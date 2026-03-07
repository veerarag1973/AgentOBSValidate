# SDK Reference — Programmatic Usage

`agentobs-validate` ships as a fully importable Python library in addition to its CLI.
Core validation capabilities are available as a Python API. CLI-only flags such as
`--strict` are command-interface behaviors, not separate SDK methods.

---

## Installation

```bash
pip install agentobs-validate
```

---

## Package layout

```
agentobs_validate/
├── cli/main.py              # Click entry point (CLI only)
├── errors/
│   ├── codes.py             # Error code string constants + ALL_ERROR_CODES
│   └── models.py            # ValidationError dataclass
├── schema/
│   ├── fields.py            # Field name constants + REQUIRED_FIELDS
│   ├── patterns.py          # Pre-compiled regex patterns
│   └── json_schema.py       # JSON Schema export (build_json_schema / export_schema)
└── validator/
    ├── context.py           # ValidationContext dataclass
    ├── engine.py            # validate_event() / validate_stream()
    ├── field_validators.py  # Per-field validator functions
    ├── formatters.py        # format_human() / format_json()
    ├── input_parser.py      # iter_events() / ParseError
    └── results.py           # EventResult / StreamResult dataclasses
```

---

## Core concepts

### `ValidationError`

The atomic unit of a failed validation.

```python
from agentobs_validate.errors.models import ValidationError

# Fields:
# .code     — machine-readable error code (str)
# .field    — the event field that failed (str)
# .message  — human-readable description (str)
# .value    — the raw value that was rejected (Any | None)
```

### `EventResult`

The outcome of validating a single event.

```python
from agentobs_validate.validator.results import EventResult

# Fields:
# .index   — 1-based position in the input stream (int)
# .status  — "pass" or "fail" (Literal["pass", "fail"])
# .errors  — list of ValidationError (empty when status == "pass")
```

### `StreamResult`

The aggregated outcome of validating a stream of events.

```python
from agentobs_validate.validator.results import StreamResult

# Fields:
# .events_checked  — total events processed (int)
# .valid           — events with status "pass" (int)
# .invalid         — events with status "fail" (int)
# .events          — list of EventResult, preserving input order
# .schema_version  — the schema version validated against (str, default "0.1")
```

### `ValidationContext`

Per-run configuration: OTel mode, schema version, HMAC key.

```python
from agentobs_validate.validator.context import ValidationContext

ctx = ValidationContext(
    otel_mode=False,       # accept camelCase OTel aliases
    schema_version="0.1",  # must be a supported version
    key_bytes=None,        # raw HMAC-SHA256 key bytes (or None = structural only)
)
```

---

## API Reference

### `validate_event(index, event, ctx=None) → EventResult`

Validate a single event dict.

```python
from agentobs_validate.validator.engine import validate_event

result = validate_event(1, event_dict)
# result.status   → "pass" or "fail"
# result.errors   → list[ValidationError]
# result.index    → 1
```

- `index` — 1-based position used in output (pass `1` when validating standalone events).
- `event` — a plain Python `dict` decoded from JSON.
- `ctx` — optional `ValidationContext`; defaults to `ValidationContext()` when `None`.

All field validators run regardless of earlier failures (**non-short-circuit**).

---

### `validate_stream(events, ctx=None) → StreamResult`

Validate every event in an iterator.

```python
from agentobs_validate.validator.engine import validate_stream

result = validate_stream(iter([(1, event1), (2, event2)]))
# result.events_checked  → 2
# result.valid           → ...
# result.invalid         → ...
# result.events          → [EventResult, ...]
```

- `events` — an iterator yielding `(position: int, event_dict: dict)` pairs.
  Use `iter_events()` (see below) to produce this from a file or stdin.
- `ctx` — optional `ValidationContext`.

---

### `iter_events(source) → Iterator[(int, dict)]`

Open a file (or stdin) and yield `(position, event_dict)` pairs.

```python
from agentobs_validate.validator.input_parser import iter_events, ParseError

try:
    for position, event in iter_events("events.jsonl"):
        ...
except ParseError as exc:
    print(f"Parse error at line {exc.line_number}: {exc}")
```

- `source` — path to a `.json` or `.jsonl` file, or `None` to read from `sys.stdin`.
- Format is auto-detected: `.json` extension → JSON array; `.jsonl` extension → JSONL;
  ambiguous → file is peeked to detect `[` (JSON) or `{` (JSONL).
- Raises `ParseError` (maps to CLI exit code 2) on malformed input.

---

### `format_human(result) → str`

Return the human-readable report string (spec §10).

```python
from agentobs_validate.validator.formatters import format_human

print(format_human(result))
```

Output example:

```
✔ Event 1  valid
✖ Event 2  INVALID_ULID MISSING_TIMESTAMP

Summary
------
schema_version: 0.1
events_checked: 2
valid: 1
invalid: 1
```

---

### `format_json(result) → str`

Return the machine-readable JSON report string (spec §11).

```python
from agentobs_validate.validator.formatters import format_json
import json

report = json.loads(format_json(result))
print(report["summary"]["valid"])
```

---

### `build_json_schema(schema_version="0.1") → dict`

Return the JSON Schema (Draft 2020-12) as a Python dict.

```python
from agentobs_validate.schema.json_schema import build_json_schema

schema = build_json_schema("0.1")
# schema["$schema"]    → "https://json-schema.org/draft/2020-12/schema"
# schema["required"]   → ["event_id", "timestamp", ...]
```

Raises `ValueError` if `schema_version` is not in `SUPPORTED_VERSIONS`.

---

### `export_schema(schema_version="0.1") → str`

Return the JSON Schema as a formatted JSON string (``indent=2``).

```python
from agentobs_validate.schema.json_schema import export_schema

print(export_schema("0.1"))
```

---

## Error codes

All error code constants live in `agentobs_validate.errors.codes`.

```python
from agentobs_validate.errors.codes import (
    MISSING_EVENT_ID,    # "MISSING_EVENT_ID"
    INVALID_ULID,        # "INVALID_ULID"
    MISSING_TIMESTAMP,   # "MISSING_TIMESTAMP"
    INVALID_TIMESTAMP,   # "INVALID_TIMESTAMP"
    INVALID_EVENT_TYPE,  # "INVALID_EVENT_TYPE"
    INVALID_NAMESPACE,   # "INVALID_NAMESPACE"
    MISSING_SOURCE,      # "MISSING_SOURCE"
    INVALID_SOURCE_FORMAT, # "INVALID_SOURCE_FORMAT"
    INVALID_TRACE_ID,    # "INVALID_TRACE_ID"
    INVALID_SPAN_ID,     # "INVALID_SPAN_ID"
    INVALID_SIGNATURE,   # "INVALID_SIGNATURE"
    UNSUPPORTED_ALGORITHM, # "UNSUPPORTED_ALGORITHM"
    SIGNATURE_MISMATCH,  # "SIGNATURE_MISMATCH"
    ALL_ERROR_CODES,     # frozenset of all 13 codes
)
```

See [errors.md](errors.md) for the full reference including field, trigger, and fix for each code.

---

## Serialisation

Both result types expose a `to_dict()` method that returns a JSON-serialisable `dict`.

```python
import json

event_dict = result.to_dict()
stream_dict = stream_result.to_dict()

json.dumps(stream_dict, indent=2)  # always safe — no non-serialisable values
```

`StreamResult.to_dict()` structure:

```json
{
  "schema_version": "0.1",
  "events_checked": 5,
  "valid": 4,
  "invalid": 1,
  "events": [
    {"index": 1, "status": "pass", "errors": []},
    {"index": 3, "status": "fail", "errors": [
      {"code": "INVALID_ULID", "field": "event_id",
       "message": "event_id must be a valid ULID ...", "value": "bad-id"}
    ]}
  ]
}
```

---

## Thread safety

`validate_event` and `validate_stream` are pure functions with no global mutable state.
`ValidationContext` is a dataclass with no interior mutation after construction.
Both are safe to call from multiple threads simultaneously.

---

## Supported schema versions

```python
from agentobs_validate.schema.json_schema import SUPPORTED_VERSIONS
# frozenset({"0.1"})
```
