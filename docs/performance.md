# Performance Notes

`agentobs-validate` is designed to meet the 100 000 events/second throughput floor from spec §14
while consuming O(1) memory for JSONL input streams.

---

## Requirements  (spec §14)

| Requirement       | Target                         |
|-------------------|--------------------------------|
| Throughput        | ≥ 100 000 events/second        |
| Memory model      | O(1) for JSONL streaming input |
| Memory model      | O(n) for JSON array input (unavoidable) |

---

## Benchmark Results

Measured on a Windows 11 workstation with Python 3.13.9.

### Throughput test — 100 000 events

```
[throughput] Generating and validating 100,000 events …
  Result : 136,995 events/sec  (required: ≥100,000)  [PASS]
  Invalid events detected: 0 (expected 0)
```

### Memory stability test — 200 000 events

```
[memory]     Running memory-stability test with 200,000 events …
  Baseline : 19.0 KiB  (after 10 000 warm-up events)
  Peak     : 2.0 KiB
  Growth   : 0.11×  (max allowed: 2.0×)  [PASS]
```

Total: **PASS**

---

## How to reproduce

```bash
# Quick smoke test (100 k throughput + 200 k memory)
python tests/benchmarks/bench_throughput.py --n 100000 --memory-n 200000 --memory-full-n 50000

# Full-scale test (spec §14 targets: 500 k throughput + 1 M memory)
python tests/benchmarks/bench_throughput.py
```

The generator script (`tests/benchmarks/gen_events.py`) creates deterministic
JSONL fixtures. All generated events are structurally valid so the benchmark
measures parser + validator overhead only.

---

## Implementation notes

- **JSONL streaming** — `input_parser.iter_events_jsonl()` reads one line at a
  time using Python's default file iterator. The file is never buffered in full.
- **Result retention tradeoff** — `engine.validate_stream()` returns per-event
  results and therefore retains an `EventResult` list in memory (O(n) in number
  of events). The parser itself remains O(1) for JSONL input.
- **Benchmark methodology** — memory benchmark now tracks true peak via
  `tracemalloc.get_traced_memory()`. It reports:
  1. streaming-core profile (`iter_events` + `validate_event`) with pass/fail threshold,
  2. full `validate_stream` profile (informational, includes retained results).
- **Input hardening limits** — parser enforces default safety limits:
  `MAX_JSONL_LINE_BYTES=1_000_000`, `MAX_EVENT_BYTES=1_000_000`,
  `MAX_NESTING_DEPTH=10`, `MAX_STDIN_BYTES=10_000_000`.
- **No heavy dependencies** — the hot path uses only Python stdlib (`re`, `json`,
  `io`). No third-party parsing libraries are involved.

---

## Benchmark scripts

| File                                   | Purpose                              |
|----------------------------------------|--------------------------------------|
| `tests/benchmarks/gen_events.py`       | Generate large JSONL fixture         |
| `tests/benchmarks/bench_throughput.py` | Measure throughput + memory stability |
