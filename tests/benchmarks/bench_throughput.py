"""Throughput and memory benchmark for the AgentOBS validator.

Spec reference: §14 Performance Requirements.

Goals
-----
- Throughput  ≥ 100 000 events/second on reference hardware.
- Peak memory stays O(1) relative to stream size for JSONL input.

Usage
-----
    python tests/benchmarks/bench_throughput.py [--n N] [--memory-n MN]

    --n N        Events used for throughput test (default 500 000)
    --memory-n   Events used for memory-stability test (default 1 000 000)

The script exits with code 1 if either assertion fails.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
import tracemalloc

# Make sure the installed (editable) package is importable when run directly.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "src"),
)

from agentobs_validate.validator.engine import validate_stream
from agentobs_validate.validator.input_parser import iter_events

# Import the generator so we don't need a pre-existing file.
# Import relative to this file's directory so the script works when run directly.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from gen_events import generate_events  # type: ignore[import]

# Minimum acceptable throughput (spec §14)
MIN_EVENTS_PER_SEC = 100_000

# Maximum fraction that peak memory may grow relative to the baseline snapshot
# taken after the first 10 000 events.  We allow 2× headroom.
MEMORY_GROWTH_FACTOR_MAX = 2.0


# ── Helpers ───────────────────────────────────────────────────────────────────


def _tmp_file() -> str:
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    return path


def _human_bytes(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n //= 1024  # type: ignore[assignment]
    return f"{n:.1f} TiB"


# ── Throughput test ───────────────────────────────────────────────────────────


def run_throughput(n: int) -> tuple[float, int]:
    """Validate *n* events and return ``(events_per_sec, invalid_count)``."""
    path = _tmp_file()
    try:
        generate_events(n, path)
        t0 = time.perf_counter()
        result = validate_stream(iter_events(path))
        elapsed = time.perf_counter() - t0
    finally:
        os.unlink(path)

    eps = n / elapsed
    return eps, result.invalid


# ── Memory-stability test ─────────────────────────────────────────────────────


def run_memory_stability(n: int) -> tuple[int, int]:
    """Return ``(baseline_kib, peak_kib)`` for streaming-core validation.

    Methodology
    -----------
    We start ``tracemalloc``, consume the first 10 000 events to warm up
    internal data structures, capture *baseline* current memory, then
    continue to the end while tracking true peak via ``get_traced_memory``.

    A well-behaved (O(1)) implementation will show a peak that is close to
    the baseline.  A buffering implementation will show peak ∝ n.
    """
    WARM_UP = 10_000
    path = _tmp_file()
    try:
        generate_events(n, path)

        tracemalloc.start()
        baseline_size: int | None = None

        count = 0
        for _idx, event in iter_events(path):
            # Manually call validate_event inline so we can snapshot mid-stream
            from agentobs_validate.validator.engine import validate_event

            validate_event(_idx, event)
            count += 1
            if count == WARM_UP:
                baseline_size = tracemalloc.get_traced_memory()[0]
                tracemalloc.reset_peak()

        peak_size = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    finally:
        os.unlink(path)

    return (baseline_size or 0) // 1024, peak_size // 1024


def run_memory_validate_stream(n: int) -> tuple[int, int]:
    """Return ``(baseline_kib, peak_kib)`` for full ``validate_stream`` path.

    This includes retention of per-event ``EventResult`` objects and therefore
    is expected to scale with event count.
    """
    path = _tmp_file()
    try:
        generate_events(n, path)
        tracemalloc.start()
        baseline = tracemalloc.get_traced_memory()[0]
        tracemalloc.reset_peak()
        _ = validate_stream(iter_events(path))
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    finally:
        os.unlink(path)

    return baseline // 1024, peak // 1024


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Throughput + memory benchmark for agentobs-validate."
    )
    parser.add_argument(
        "--n",
        type=int,
        default=500_000,
        help="Events for throughput test (default: 500 000)",
    )
    parser.add_argument(
        "--memory-n",
        dest="memory_n",
        type=int,
        default=1_000_000,
        help="Events for memory stability test (default: 1 000 000)",
    )
    parser.add_argument(
        "--memory-full-n",
        dest="memory_full_n",
        type=int,
        default=100_000,
        help="Events for full validate_stream memory profile (default: 100 000)",
    )
    args = parser.parse_args()

    passed = True

    # ── Throughput ────────────────────────────────────────────────────────────
    print(f"\n[throughput] Generating and validating {args.n:,} events …", flush=True)
    eps, invalid = run_throughput(args.n)
    status = "PASS" if eps >= MIN_EVENTS_PER_SEC else "FAIL"
    print(
        f"  Result : {eps:,.0f} events/sec  (required: ≥{MIN_EVENTS_PER_SEC:,})  [{status}]"
    )
    print(f"  Invalid events detected: {invalid} (expected 0)")
    if eps < MIN_EVENTS_PER_SEC:
        passed = False
    if invalid != 0:
        print("  WARNING: benchmark fixture produced invalid events — check gen_events.py")

    # ── Memory stability ──────────────────────────────────────────────────────
    print(
        f"\n[memory]     Running memory-stability test with {args.memory_n:,} events …",
        flush=True,
    )
    baseline_kib, peak_kib = run_memory_stability(args.memory_n)
    growth = (peak_kib / baseline_kib) if baseline_kib > 0 else float("inf")
    status_mem = "PASS" if growth <= MEMORY_GROWTH_FACTOR_MAX else "FAIL"
    print(f"  Baseline : {_human_bytes(baseline_kib * 1024)}")
    print(f"  Peak     : {_human_bytes(peak_kib * 1024)}")
    print(
        f"  Growth   : {growth:.2f}×  (max allowed: {MEMORY_GROWTH_FACTOR_MAX}×)  [{status_mem}]"
    )
    if growth > MEMORY_GROWTH_FACTOR_MAX:
        passed = False

    # ── Full validate_stream memory profile (informational) ──────────────────
    print(
        f"\n[memory-full] Profiling validate_stream with {args.memory_full_n:,} events …",
        flush=True,
    )
    full_base_kib, full_peak_kib = run_memory_validate_stream(args.memory_full_n)
    full_growth = (full_peak_kib / full_base_kib) if full_base_kib > 0 else float("inf")
    print(f"  Baseline : {_human_bytes(full_base_kib * 1024)}")
    print(f"  Peak     : {_human_bytes(full_peak_kib * 1024)}")
    print(
        f"  Growth   : {full_growth:.2f}×  (includes retained EventResult list; informational only)"
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + ("=" * 50))
    print(f"Overall: {'PASS' if passed else 'FAIL'}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
