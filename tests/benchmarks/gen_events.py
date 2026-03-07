"""Generate a large JSONL fixture of valid AgentOBS events for benchmarking.

Usage
-----
    python tests/benchmarks/gen_events.py [N] [output_path]

    N            Number of events to generate (default 500_000)
    output_path  Destination file path  (default: /tmp/bench_events.jsonl)

The generated file contains only structurally valid events, so the validator
should produce zero errors and measure only parsing + validation overhead.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time

# ---------------------------------------------------------------------------
# Deterministic event templates (spec §17 sample values)
# ---------------------------------------------------------------------------
_EVENT_TYPES = [
    "agent.plan.created",
    "agent.tool.called",
    "agent.tool.returned",
    "agent.llm.requested",
    "agent.llm.responded",
    "agent.memory.read",
    "agent.memory.written",
    "agent.plan.completed",
]

_SOURCES = [
    "spanforge@1.0.0",
    "langchain@0.2.11",
    "autogen@0.4.0",
    "crewai@0.30.0",
    "openai-agents@1.0.0",
]

# Fixed trace / span anchors — rotated so the file is non-trivial
_TRACE_IDS = [
    "4bf92f3577b34da6a3ce929d0e0e4736",
    "a3ce929d0e0e47364bf92f3577b34da6",
    "ce929d0e0e47364bf92f3577b34da6a3",
]

# ULID character set (Crockford base32, uppercase, spec §8.1)
_ULID_CHARS = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _make_ulid(index: int) -> str:
    """Return a deterministic 26-char ULID-shaped string for *index*.

    This is NOT a real time-based ULID — it is designed only to satisfy the
    ``^[0-9A-HJKMNP-TV-Z]{26}$`` regex from spec §8.1.
    """
    # Encode index in base 32 using ULID_CHARS, left-padded to 26 chars
    chars = []
    n = index
    while n:
        chars.append(_ULID_CHARS[n % 32])
        n //= 32
    chars.reverse()
    return "".join(chars).zfill(26).replace("0", "0")[:26]


def _make_span_id(index: int) -> str:
    """Return a deterministic 16-char lowercase hex span_id."""
    return format(index % (16 ** 16), "016x")


def _make_timestamp(index: int) -> str:
    """Return a deterministic ISO-8601 / RFC-3339 UTC timestamp."""
    # Step 100 ms per event — wraps within the same minute for simplicity
    ms = (index * 100) % 60000
    sec = ms // 1000
    frac = ms % 1000
    return f"2026-02-20T10:{(index // 600) % 60:02d}:{sec:02d}.{frac:03d}Z"


def generate_events(n: int, path: str) -> None:
    """Write *n* valid AgentOBS events to *path* in JSONL format."""
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(n):
            event = {
                "event_id": _make_ulid(i + 1),
                "timestamp": _make_timestamp(i),
                "event_type": _EVENT_TYPES[i % len(_EVENT_TYPES)],
                "source": _SOURCES[i % len(_SOURCES)],
                "trace_id": _TRACE_IDS[i % len(_TRACE_IDS)],
                "span_id": _make_span_id(i),
            }
            fh.write(json.dumps(event, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate large JSONL fixture for AgentOBS benchmarks."
    )
    parser.add_argument(
        "n",
        nargs="?",
        type=int,
        default=500_000,
        help="Number of events to generate (default: 500 000)",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=os.path.join(tempfile.gettempdir(), "bench_events.jsonl"),
        help="Output file path",
    )
    args = parser.parse_args()

    print(f"Generating {args.n:,} events → {args.output} ...", flush=True)
    t0 = time.perf_counter()
    generate_events(args.n, args.output)
    elapsed = time.perf_counter() - t0
    size_mb = os.path.getsize(args.output) / 1024 / 1024
    print(
        f"Done in {elapsed:.2f}s  |  {args.n / elapsed:,.0f} events/s  |  {size_mb:.1f} MB",
        flush=True,
    )


if __name__ == "__main__":
    main()
