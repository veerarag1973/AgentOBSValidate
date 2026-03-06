# `agentobs-validate` — Implementation Plan

**Based on:** agentobsvalidatespec.md v0.1
**Language:** Python (reference implementation per spec §15)
**Target:** Production-ready CLI, CI-safe, O(1) streaming memory

---

## Phase Overview

| Phase | Name                          | Scope                                              | Exit Criteria                                              |
| ----- | ----------------------------- | -------------------------------------------------- | ---------------------------------------------------------- |
| 1     | Repository Scaffold           | Directory layout, packaging, tooling               | `agentobs-validate --help` runs from source                |
| 2     | Schema & Error Catalog        | Field specs, regex constants, error codes          | All error codes from spec are defined and importable       |
| 3     | Field Validators              | Per-field validation logic for all 7 fields        | Unit tests pass for every rule in §8                       |
| 4     | Input Parsing & Streaming     | JSON array, JSONL, STDIN; O(1) memory for JSONL    | 100k-event JSONL parsed with flat memory profile           |
| 5     | Core Validator Engine         | Orchestrates per-event validation pipeline (§9)    | All events in a stream produce a structured result         |
| 6     | Output Formatters             | Human-readable (§10) and JSON (§11) output         | Both modes produce spec-compliant output                   |
| 7     | CLI Interface & Exit Codes    | Argument parsing, flags, exit codes (§4, §5)       | All CLI invocation forms from §4 work correctly            |
| 8     | Signature Validation          | Optional HMAC-SHA256 + base64 check (§8.7)         | Valid and invalid signatures handled correctly             |
| 9     | Example Fixtures              | `valid.jsonl`, `invalid.jsonl` example files (§16) | Examples demonstrable in README                            |
| 10    | Performance Validation        | Benchmark at 100k events/sec, O(1) memory (§14)    | Benchmark script passes on reference hardware              |
| 11    | CI Integration Artifacts      | GitHub Actions workflow, exit code contract (§13)  | Workflow runs and fails correctly on invalid input         |
| 12    | Documentation                 | `docs/spec.md` mirror, README, usage guide         | All CLI flags and error codes documented                   |
| 13    | Roadmap Foundations (Optional)| Stubs for JSON Schema export, OTel mode (§18)      | Flags exist but return `not yet implemented` with exit 3   |

---

## Phase 1 — Repository Scaffold

**Goal:** Establish the full directory layout from spec §16, packaging entry point, and developer tooling.

### Tasks

- [ ] Create directory tree:
  ```
  agentobs-validate/
    cmd/agentobs-validate/
    pkg/validator/
    pkg/schema/
    pkg/errors/
    examples/
    docs/
    tests/
  ```
- [ ] Create `pyproject.toml` (or `setup.py`) declaring:
  - Package name: `agentobs-validate`
  - Entry point: `agentobs-validate = cmd.agentobs_validate.main:main`
  - Python `>=3.9`
  - Dependencies: `python-ulid` or `ulid-py`, `click` (CLI), `pytest` (dev)
- [ ] Create `__init__.py` files for all packages under `pkg/`
- [ ] Add `.gitignore`, `LICENSE`, and stub `README.md`
- [ ] Verify `agentobs-validate --help` prints without error

### Deliverables
- `pyproject.toml`
- `cmd/agentobs_validate/main.py` (stub)
- Package `__init__.py` files

---

## Phase 2 — Schema & Error Catalog

**Goal:** Codify every field spec, regex, and error code from §7, §8, and §12 into importable constants.

### Tasks

- [ ] Create `pkg/schema/fields.py` — define field name constants and per-field metadata:
  ```python
  REQUIRED_FIELDS = ["event_id", "timestamp", "event_type", "source", "trace_id", "span_id"]
  OPTIONAL_FIELDS = ["signature"]
  ```
- [ ] Create `pkg/schema/patterns.py` — compile all regex patterns from spec:
  ```python
  ULID_RE        = re.compile(r'^[0-9A-HJKMNP-TV-Z]{26}$')
  TIMESTAMP_RE   = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$')
  EVENT_TYPE_RE  = re.compile(r'^[a-z0-9]+\.[a-z0-9]+\.[a-z0-9_]+$')
  SOURCE_RE      = re.compile(r'^[a-zA-Z0-9\-_]+@[0-9]+\.[0-9]+\.[0-9]+$')
  TRACE_ID_RE    = re.compile(r'^[0-9a-f]{16,32}$')
  SPAN_ID_RE     = re.compile(r'^[0-9a-f]{16}$')
  BASE64_RE      = re.compile(r'^[A-Za-z0-9+/]+=*$')
  ```
- [ ] Create `pkg/errors/codes.py` — enumerate all error codes from §8 and §12:
  ```python
  MISSING_EVENT_ID        = "MISSING_EVENT_ID"
  INVALID_ULID            = "INVALID_ULID"
  MISSING_TIMESTAMP       = "MISSING_TIMESTAMP"
  INVALID_TIMESTAMP       = "INVALID_TIMESTAMP"
  INVALID_EVENT_TYPE      = "INVALID_EVENT_TYPE"
  INVALID_NAMESPACE       = "INVALID_NAMESPACE"
  MISSING_SOURCE          = "MISSING_SOURCE"
  INVALID_SOURCE_FORMAT   = "INVALID_SOURCE_FORMAT"
  INVALID_TRACE_ID        = "INVALID_TRACE_ID"
  INVALID_SPAN_ID         = "INVALID_SPAN_ID"
  INVALID_SIGNATURE       = "INVALID_SIGNATURE"
  UNSUPPORTED_ALGORITHM   = "UNSUPPORTED_ALGORITHM"
  ```
- [ ] Create `pkg/errors/models.py` — define `ValidationError` dataclass matching §12:
  ```python
  @dataclass
  class ValidationError:
      code: str
      field: str
      message: str
      value: Any
  ```

### Deliverables
- `pkg/schema/fields.py`
- `pkg/schema/patterns.py`
- `pkg/errors/codes.py`
- `pkg/errors/models.py`

---

## Phase 3 — Field Validators

**Goal:** Implement one validator function per field, each returning a list of `ValidationError` objects.

### Tasks

- [ ] Create `pkg/validator/field_validators.py` with functions:

  | Function                   | Spec Section | Checks                                      |
  | -------------------------- | ------------ | ------------------------------------------- |
  | `validate_event_id(v)`     | §8.1         | present, matches ULID regex                 |
  | `validate_timestamp(v)`    | §8.2         | present, matches RFC3339 pattern            |
  | `validate_event_type(v)`   | §8.3         | present, matches `domain.category.action`   |
  | `validate_source(v)`       | §8.4         | present, matches `name@semver`              |
  | `validate_trace_id(v)`     | §8.5         | present, 16–32 hex chars                    |
  | `validate_span_id(v)`      | §8.6         | present, exactly 16 hex chars               |
  | `validate_signature(v)`    | §8.7         | optional; if present: algorithm + base64    |

- [ ] Each function returns `list[ValidationError]` (empty = valid)
- [ ] Write unit tests in `tests/test_field_validators.py`:
  - Happy path for every field using the example values from spec §17
  - Each specific error code triggered by a crafted invalid input
  - Missing field → correct MISSING_* code
  - Boundary cases (e.g. 15-char trace_id, 33-char trace_id)

### Deliverables
- `pkg/validator/field_validators.py`
- `tests/test_field_validators.py`

---

## Phase 4 — Input Parsing & Streaming

**Goal:** Parse both JSON array files and JSONL files. Support STDIN. Guarantee O(1) memory for JSONL (streaming iterator, never load full file).

### Tasks

- [ ] Create `pkg/validator/input_parser.py` with:
  - `detect_format(path: str | None) -> Literal["json", "jsonl"]`
    - If path ends in `.jsonl` → jsonl
    - Otherwise peek first byte: `[` → json array, `{` → jsonl
  - `iter_events_jsonl(stream) -> Iterator[tuple[int, dict]]`
    - Read one line at a time, parse with `json.loads`
    - Yield `(line_number, event_dict)` pairs
    - Raise `ParseError` on malformed line with line number
  - `iter_events_json(stream) -> Iterator[tuple[int, dict]]`
    - Load full JSON array (acceptable for non-streaming array format)
    - Yield `(index, event_dict)` pairs
    - Raise `ParseError` on invalid JSON
  - `iter_events(source: str | None) -> Iterator[tuple[int, dict]]`
    - Unified entry point routing to STDIN or file, detecting format
- [ ] STDIN support: when `source` is `None`, read from `sys.stdin`
- [ ] `ParseError` maps to exit code 2 (spec §5)
- [ ] Write tests in `tests/test_input_parser.py`:
  - Valid JSON array
  - Valid JSONL multi-line
  - JSONL with one malformed line mid-stream
  - Empty file
  - Non-JSON garbage input

### Deliverables
- `pkg/validator/input_parser.py`
- `tests/test_input_parser.py`

---

## Phase 5 — Core Validator Engine

**Goal:** Implement the per-event validation pipeline described in spec §9, producing a structured result per event.

### Tasks

- [ ] Create `pkg/validator/engine.py`:
  - `validate_event(index: int, event: dict) -> EventResult`
    - Runs all field validators in pipeline order:
      1. `validate_event_id`
      2. `validate_timestamp`
      3. `validate_event_type`
      4. `validate_source`
      5. `validate_trace_id`
      6. `validate_span_id`
      7. `validate_signature` (only if key present)
    - Collects all errors (non-short-circuit — report all errors per event)
    - Returns `EventResult(index, status, errors)`
  - `validate_stream(events: Iterator) -> StreamResult`
    - Iterates events, calls `validate_event` per event
    - Accumulates `summary` counters: `events_checked`, `valid`, `invalid`
    - Returns `StreamResult(summary, events)`
- [ ] Define result dataclasses in `pkg/validator/results.py`:
  ```python
  @dataclass
  class EventResult:
      index: int
      status: Literal["pass", "fail"]
      errors: list[ValidationError]

  @dataclass
  class StreamResult:
      events_checked: int
      valid: int
      invalid: int
      events: list[EventResult]
  ```
- [ ] Write tests in `tests/test_engine.py`:
  - All-valid stream → `StreamResult.invalid == 0`
  - Mixed stream → correct counts
  - Event with multiple errors → all errors reported
  - Empty stream → `events_checked == 0`

### Deliverables
- `pkg/validator/engine.py`
- `pkg/validator/results.py`
- `tests/test_engine.py`

---

## Phase 6 — Output Formatters

**Goal:** Implement both output modes from spec §10 and §11.

### Tasks

- [ ] Create `pkg/validator/formatters.py`:
  - `format_human(result: StreamResult) -> str`
    - Per-event: `✔ Event N  valid` or `✖ Event N  ERROR_CODE [ERROR_CODE2 ...]`
    - Summary block:
      ```
      Summary
      ------
      events_checked: N
      valid: N
      invalid: N
      ```
  - `format_json(result: StreamResult) -> str`
    - Emit spec §11 JSON structure exactly
    - Events with status `pass` omit `errors` key
    - Events with status `fail` include full error objects per §12
    - Use `json.dumps` with `indent=2`
- [ ] Write tests in `tests/test_formatters.py`:
  - Human output snapshot test for mixed result
  - JSON output validates against expected §11 structure
  - JSON output is parseable by `json.loads`
  - `pass` events have no `errors` key in JSON output

### Deliverables
- `pkg/validator/formatters.py`
- `tests/test_formatters.py`

---

## Phase 7 — CLI Interface & Exit Codes

**Goal:** Wire everything together into the `agentobs-validate` CLI exactly as specified in §4 and §5.

### Tasks

- [ ] Implement `cmd/agentobs_validate/main.py` using `click`:
  ```
  agentobs-validate [FILE] [--json] [--strict]
  ```
  - `FILE` is optional positional argument (defaults to STDIN)
  - `--json` flag enables JSON output mode
  - `--strict` flag: treat any `ValidationError` that would be a warning as a failure (also fails on any invalid event)
  - `--version` flag: prints `agentobs-validate 0.1`
  - `--help` auto-generated by click

- [ ] Exit code contract (spec §5):
  | Condition                                      | Exit Code |
  | ---------------------------------------------- | --------- |
  | All events valid                               | 0         |
  | One or more validation errors                  | 1         |
  | Input parse failure (malformed JSON/JSONL)     | 2         |
  | Internal/unexpected exception                  | 3         |

- [ ] `--strict` mode: exit 1 if any event fails, same as normal; reserved for future warning-level rules

- [ ] Wrap entire run in try/except to catch unexpected errors → exit 3 with human message

- [ ] Write integration tests in `tests/test_cli.py` using `click.testing.CliRunner`:
  - `agentobs-validate valid.jsonl` → exit 0
  - `agentobs-validate invalid.jsonl` → exit 1
  - `agentobs-validate broken.json` (parse failure) → exit 2
  - `agentobs-validate valid.jsonl --json` → exit 0, stdout is valid JSON
  - `agentobs-validate valid.jsonl --strict` → exit 0 on valid input
  - STDIN pipe: pass bytes to CliRunner input

### Deliverables
- `cmd/agentobs_validate/main.py`
- `tests/test_cli.py`

---

## Phase 8 — Signature Validation

**Goal:** Implement the optional `signature` field validation from spec §8.7.

### Tasks

- [ ] In `pkg/validator/field_validators.py`, implement full `validate_signature(v)`:
  - If `signature` key is absent → skip (valid)
  - If present, validate sub-fields:
    - `algorithm` must equal `"HMAC-SHA256"` exactly → `UNSUPPORTED_ALGORITHM` otherwise
    - `value` must be non-empty valid base64 → `INVALID_SIGNATURE` otherwise
    - `key_id` must be a non-empty string (informational, no error code specified)
  - Return list of applicable `ValidationError` objects
- [ ] Note: actual HMAC cryptographic verification is a roadmap item (§18 "signature verification keys") — Phase 8 validates structure only
- [ ] Extend unit tests in `tests/test_field_validators.py`:
  - Valid signature block → no errors
  - Wrong algorithm value → `UNSUPPORTED_ALGORITHM`
  - Invalid base64 value → `INVALID_SIGNATURE`
  - Missing `value` key → `INVALID_SIGNATURE`
  - Missing `algorithm` key → `UNSUPPORTED_ALGORITHM`

### Deliverables
- Updated `pkg/validator/field_validators.py`
- Updated `tests/test_field_validators.py`

---

## Phase 9 — Example Fixtures

**Goal:** Provide the `examples/valid.jsonl` and `examples/invalid.jsonl` files from spec §16, usable in tests and the README.

### Tasks

- [ ] Create `examples/valid.jsonl` — 5+ events, all passing, covering all `event_type` examples from §8.3:
  ```jsonl
  {"event_id":"01HZY7M4YQZB3D0V4K6Z5R9F7A","timestamp":"2026-02-20T10:45:21.123Z","event_type":"agent.plan.created","source":"spanforge@1.0.0","trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b7"}
  {"event_id":"01HZY7M4YQZB3D0V4K6Z5R9F7B","timestamp":"2026-02-20T10:45:22.000Z","event_type":"agent.tool.called","source":"langchain@0.2.11","trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b8"}
  ...
  ```
- [ ] Create `examples/invalid.jsonl` — one event per error code, covering all codes from §8:
  - Missing `event_id` → `MISSING_EVENT_ID`
  - Malformed ULID → `INVALID_ULID`
  - Missing `timestamp` → `MISSING_TIMESTAMP`
  - Bad timestamp format → `INVALID_TIMESTAMP`
  - Bad `event_type` format → `INVALID_EVENT_TYPE`
  - Bad `source` format → `INVALID_SOURCE_FORMAT`
  - Bad `trace_id` → `INVALID_TRACE_ID`
  - Bad `span_id` → `INVALID_SPAN_ID`
- [ ] Create `examples/valid.json` — JSON array format with 3 events (demonstrates §3.1 support)
- [ ] Add fixture-based test in `tests/test_examples.py` that runs the CLI against both example files and asserts exit codes 0 and 1 respectively

### Deliverables
- `examples/valid.jsonl`
- `examples/invalid.jsonl`
- `examples/valid.json`
- `tests/test_examples.py`

---

## Phase 10 — Performance Validation

**Goal:** Demonstrate the 100k events/sec throughput and O(1) memory requirements from spec §14.

### Tasks

- [ ] Create `tests/benchmarks/gen_events.py` — generates a large JSONL fixture:
  - Generates N events (default 500k) to a temp file
  - Uses only valid events matching §17
- [ ] Create `tests/benchmarks/bench_throughput.py`:
  - Runs `validate_stream` against a 500k-event JSONL file
  - Measures wall clock time → asserts `events/sec >= 100_000`
  - Uses `tracemalloc` to measure peak memory allocation with a 1M-event stream → asserts peak stays flat (does not grow linearly with N)
- [ ] Profile and optimize `input_parser.py` if needed:
  - Confirm JSONL reader uses `readline()` / line iteration, never `readlines()` or `read()`
  - Confirm `StreamResult` accumulates only summary counters, not raw event dicts, in streaming mode
- [ ] Document benchmark results in `docs/performance.md`

### Deliverables
- `tests/benchmarks/gen_events.py`
- `tests/benchmarks/bench_throughput.py`
- `docs/performance.md`

---

## Phase 11 — CI Integration Artifacts

**Goal:** Provide ready-to-use GitHub Actions workflow and document the CI contract from spec §13.

### Tasks

- [ ] Create `.github/workflows/validate.yml`:
  ```yaml
  name: AgentOBS Validate
  on: [push, pull_request]
  jobs:
    validate:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: "3.11"
        - run: pip install .
        - name: Validate AgentOBS events
          run: agentobs-validate examples/valid.jsonl
        - name: Validate with JSON output
          run: agentobs-validate examples/valid.jsonl --json
  ```
- [ ] Create `.github/workflows/tests.yml`:
  - Runs `pytest tests/` on push
  - Matrix: Python 3.9, 3.10, 3.11, 3.12
- [ ] Document exit code contract in `docs/ci.md`:
  - Table of exit codes mirroring spec §5
  - Example for GitHub Actions, GitLab CI, and CircleCI
  - Note on `--json` flag for CI log parsing

### Deliverables
- `.github/workflows/validate.yml`
- `.github/workflows/tests.yml`
- `docs/ci.md`

---

## Phase 12 — Documentation

**Goal:** Full documentation suite covering the spec, usage, and error reference.

### Tasks

- [ ] `README.md` — top-level project README:
  - Installation: `pip install agentobs-validate`
  - Quick start (all CLI forms from §4)
  - Exit codes table (§5)
  - Link to docs/
- [ ] `docs/spec.md` — mirror of the specification (already exists as `agentobsvalidatespec.md`, symlinked or copied)
- [ ] `docs/errors.md` — full error code reference:
  - One table row per error code
  - Field, error code, description, example bad value, how to fix
- [ ] `docs/ci.md` — CI integration guide (from Phase 11)
- [ ] `docs/performance.md` — benchmark results (from Phase 10)
- [ ] Inline docstrings in all public functions in `pkg/`

### Deliverables
- `README.md` (updated)
- `docs/spec.md`
- `docs/errors.md`
- `docs/ci.md`
- `docs/performance.md`

---

## Phase 13 — Roadmap Foundations (Optional)

**Goal:** Stub the four roadmap features from spec §18 so they are discoverable in `--help` and return a clear not-yet-implemented message. This ensures the CLI surface is designed correctly before full implementation.

### Tasks

- [ ] `--export-schema` flag → prints `JSON Schema export: not yet implemented` → exit 3
- [ ] `--otel` flag → prints `OpenTelemetry compatibility mode: not yet implemented` → exit 3
- [ ] `--schema-version` flag → prints `Schema version negotiation: not yet implemented` → exit 3
- [ ] `--key-file` flag → prints `Signature key verification: not yet implemented` → exit 3
- [ ] Add note in help text: `(roadmap feature — see docs/roadmap.md)`
- [ ] Create `docs/roadmap.md` describing each future feature with its spec §18 source

### Deliverables
- Updated `cmd/agentobs_validate/main.py` (stub flags)
- `docs/roadmap.md`

---

## Dependency Summary

| Package              | Purpose                             | Phase Used  |
| -------------------- | ----------------------------------- | ----------- |
| `click`              | CLI argument parsing                | 7           |
| `python-ulid`        | ULID format validation (optional)   | 3           |
| `pytest`             | Unit and integration testing        | 3–9         |
| `pytest-benchmark`   | Throughput benchmarking             | 10          |

All validation logic uses Python stdlib (`re`, `json`, `base64`, `sys`, `io`) — no heavy runtime dependencies.

---

## Test Coverage Targets

| Phase | Test File                        | Coverage Target |
| ----- | -------------------------------- | --------------- |
| 3     | `test_field_validators.py`       | 100%            |
| 4     | `test_input_parser.py`           | 100%            |
| 5     | `test_engine.py`                 | 100%            |
| 6     | `test_formatters.py`             | 100%            |
| 7     | `test_cli.py`                    | 95%+            |
| 9     | `test_examples.py`               | fixture-driven  |

---

## Completion Criteria

The implementation is **complete and spec-compliant** when:

1. `agentobs-validate examples/valid.jsonl` exits 0
2. `agentobs-validate examples/invalid.jsonl` exits 1
3. `agentobs-validate examples/valid.jsonl --json` exits 0 and stdout is valid JSON matching §11
4. `cat examples/valid.jsonl | agentobs-validate` exits 0
5. All `pytest tests/` pass
6. Benchmark confirms ≥ 100k events/sec on JSONL streaming
7. Memory profile confirms O(1) growth for JSONL mode
8. All 12 error codes from §8 are triggerable and testable
