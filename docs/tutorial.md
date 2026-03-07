# Tutorial: Validating AgentOBS Events

This tutorial walks through common validation tasks, first using the **CLI**
and then using the **Python SDK** for programmatic integration.

---

## Prerequisites

Install the package:

```bash
pip install agentobs-validate
```

Verify the installation:

```bash
agentobs-validate --version
# agentobs-validate, version 0.1.0
```

---

## Part 1 — CLI Tutorial

### 1.1 Validating a JSONL file

Create a file `events.jsonl` with one JSON object per line:

```jsonl
{"event_id":"01HZQSN7PQVR2K4M0BXJD3GSTA","timestamp":"2026-03-06T10:00:00.000Z","event_type":"agent.plan.created","source":"spanforge@1.0.0","trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b7"}
{"event_id":"01HZQSN7PQVR2K4M0BXJD3GSTB","timestamp":"2026-03-06T10:00:01.000Z","event_type":"agent.tool.called","source":"langchain@0.2.11","trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b8"}
```

Run validation:

```bash
agentobs-validate events.jsonl
```

Expected output:

```
✔ Event 1  valid
✔ Event 2  valid

Summary
------
schema_version: 0.1
events_checked: 2
valid: 2
invalid: 0
```

Exit code is `0` — all events are valid.

---

### 1.2 Catching invalid events

Create `bad-events.jsonl` with deliberate errors:

```jsonl
{"timestamp":"2026-03-06T10:00:00.000Z","event_type":"agent.plan.created","source":"spanforge@1.0.0","trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b7"}
{"event_id":"not-a-ulid","timestamp":"2026-03-06T10:00:01.000Z","event_type":"agent.plan.created","source":"spanforge@1.0.0","trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b7"}
```

```bash
agentobs-validate bad-events.jsonl
```

Expected output:

```
✖ Event 1  MISSING_EVENT_ID
✖ Event 2  INVALID_ULID

Summary
------
schema_version: 0.1
events_checked: 2
valid: 0
invalid: 2
```

Exit code is `1` — validation errors were found.

---

### 1.3 Validating a JSON array file

The validator also accepts a JSON array (`.json` file):

```bash
agentobs-validate events.json
```

Format is auto-detected from the file extension. If the extension is ambiguous,
the validator peeks at the first character (`[` → JSON array, `{` → JSONL).

---

### 1.4 Reading from STDIN

Pipe events directly into the validator:

```bash
cat events.jsonl | agentobs-validate
```

Or equivalently:

```bash
agentobs-validate -
```

Useful in pipelines where events are generated on-the-fly:

```bash
my-agent emit-events | agentobs-validate
```

---

### 1.5 Machine-readable JSON output (`--json`)

Use `--json` for structured output suitable for CI systems or downstream scripts:

```bash
agentobs-validate events.jsonl --json
```

Output:

```json
{
  "summary": {
    "schema_version": "0.1",
    "events_checked": 2,
    "valid": 2,
    "invalid": 0
  },
  "events": [
    {"index": 1, "status": "pass"},
    {"index": 2, "status": "pass"}
  ]
}
```

For failing events, the `errors` array is included:

```json
{
  "summary": {"schema_version": "0.1", "events_checked": 1, "valid": 0, "invalid": 1},
  "events": [
    {
      "index": 1,
      "status": "fail",
      "errors": [
        {
          "code": "MISSING_EVENT_ID",
          "field": "event_id",
          "message": "event_id is required",
          "value": null
        }
      ]
    }
  ]
}
```

---

### 1.6 Saving a validation report

```bash
agentobs-validate events.jsonl --json > report.json
echo "Exit code: $?"
```

Process the report in a follow-up script:

```bash
python - <<'EOF'
import json, sys
r = json.load(open("report.json"))
s = r["summary"]
print(f"Checked {s['events_checked']} events — {s['valid']} valid, {s['invalid']} invalid")
for evt in r["events"]:
    if evt["status"] == "fail":
        codes = ", ".join(e["code"] for e in evt["errors"])
        print(f"  Event {evt['index']}: {codes}")
EOF
```

---

### 1.7 OpenTelemetry compatibility mode (`--otel`)

If your agent emits events using OTel/W3C Trace Context camelCase field names,
use `--otel` to accept them automatically:

```jsonl
{"eventId":"01HZQSN7PQVR2K4M0BXJD3GSTA","timestamp":"2026-03-06T10:00:00.000Z","eventType":"agent.plan.created","source":"spanforge@1.0.0","traceId":"4bf92f3577b34da6a3ce929d0e0e4736","spanId":"00f067aa0ba902b7"}
```

```bash
agentobs-validate otel-events.jsonl --otel
```

The following aliases are mapped to their AgentOBS snake_case equivalents:

| OTel camelCase | AgentOBS snake_case |
|----------------|---------------------|
| `eventId`      | `event_id`          |
| `eventType`    | `event_type`        |
| `traceId`      | `trace_id`          |
| `spanId`       | `span_id`           |

> **Note:** Aliases are only renamed when the canonical snake_case name is absent.
> Events that already use snake_case pass through unchanged.

---

### 1.8 Pinning a schema version (`--schema-version`)

```bash
agentobs-validate events.jsonl --schema-version 0.1
```

The `schema_version` appears in all output.
Supplying an unsupported version exits with code `2`:

```bash
agentobs-validate events.jsonl --schema-version 9.9
# Error: Schema version '9.9' is not supported. Supported versions: 0.1
# Exit code: 2
```

Currently supported versions: **0.1**

---

### 1.9 Cryptographic signature verification (`--key-file`)

When events carry an HMAC-SHA256 `signature` block, you can verify the digest
against a known key:

```bash
agentobs-validate events.jsonl --key-file signing.key
```

The key file contains the raw signing key (trailing whitespace is stripped):

```bash
echo -n "my-secret-key" > signing.key
agentobs-validate events.jsonl --key-file signing.key
```

Without `--key-file`, only structural validation is performed (algorithm name
and base64 format are checked, but the HMAC digest is **not** verified).

**Generating a test event with a valid signature (Python):**

```python
import base64, hashlib, hmac, json

key = b"my-secret-key"
event = {
    "event_id": "01HZQSN7PQVR2K4M0BXJD3GSTA",
    "timestamp": "2026-03-06T10:00:00.000Z",
    "event_type": "agent.plan.created",
    "source": "spanforge@1.0.0",
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "00f067aa0ba902b7",
}
# Canonical message: event without signature, sorted keys, no whitespace
canonical = json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
digest = base64.b64encode(hmac.digest(key, canonical, hashlib.sha256)).decode()
event["signature"] = {"algorithm": "HMAC-SHA256", "value": digest}
print(json.dumps(event))
```

---

### 1.10 Exporting the JSON Schema (`--export-schema`)

Print the full AgentOBS event envelope as a JSON Schema (Draft 2020-12) document:

```bash
agentobs-validate --export-schema
```

Save to a file:

```bash
agentobs-validate --export-schema > agentobs-event-schema.json
```

Combine with `--schema-version` to export a specific version schema:

```bash
agentobs-validate --export-schema --schema-version 0.1 > schema-0.1.json
```

The exported schema can be used with:
- JSON Schema validators (`jsonschema`, `ajv`)
- OpenAPI spec generators
- IDE JSON validation (VS Code, JetBrains)
- Code generation tooling

---

### 1.11 Exit code summary

Use exit codes to gate CI pipelines:

```bash
agentobs-validate events.jsonl
case $? in
  0) echo "All events valid — deploy allowed" ;;
  1) echo "Validation errors — deploy blocked" ;;
  2) echo "Parse failure — check your event format" ;;
  3) echo "Unexpected error" ;;
esac
```

| Code | Meaning |
|------|---------|
| `0`  | All events valid |
| `1`  | One or more validation errors |
| `2`  | Input parse failure or invalid configuration |
| `3`  | Internal error |

---

## Part 2 — Python SDK Tutorial

### 2.1 Validate a single event dict

```python
from agentobs_validate.validator.engine import validate_event

event = {
    "event_id": "01HZQSN7PQVR2K4M0BXJD3GSTA",
    "timestamp": "2026-03-06T10:00:00.000Z",
    "event_type": "agent.plan.created",
    "source": "spanforge@1.0.0",
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "00f067aa0ba902b7",
}

result = validate_event(1, event)

if result.status == "pass":
    print("Event is valid")
else:
    for error in result.errors:
        print(f"  [{error.code}] {error.field}: {error.message}")
```

---

### 2.2 Validate a list of events

```python
from agentobs_validate.validator.engine import validate_stream

events = [
    {"event_id": "01HZQSN7PQVR2K4M0BXJD3GSTA", ...},
    {"event_id": "01HZQSN7PQVR2K4M0BXJD3GSTB", ...},
]

# validate_stream expects an iterator of (index, dict) pairs
result = validate_stream(iter(enumerate(events, start=1)))

print(f"Valid:   {result.valid}")
print(f"Invalid: {result.invalid}")
for evt in result.events:
    if evt.status == "fail":
        codes = [e.code for e in evt.errors]
        print(f"  Event {evt.index} failed: {codes}")
```

---

### 2.3 Validate a JSONL file

```python
from agentobs_validate.validator.engine import validate_stream
from agentobs_validate.validator.input_parser import iter_events, ParseError

try:
    result = validate_stream(iter_events("events.jsonl"))
except ParseError as exc:
    print(f"Parse error: {exc}")
    raise SystemExit(2)

print(f"Checked {result.events_checked} events")
print(f"Valid:   {result.valid}")
print(f"Invalid: {result.invalid}")
```

---

### 2.4 Get structured output

```python
import json
from agentobs_validate.validator.formatters import format_human, format_json

# Human-readable (same as default CLI output)
print(format_human(result))

# Machine-readable JSON string
report = json.loads(format_json(result))
print(report["summary"])

# Or use to_dict() directly
d = result.to_dict()
# d["schema_version"], d["events_checked"], d["valid"], d["invalid"], d["events"]
```

---

### 2.5 Inspect individual errors

```python
from agentobs_validate.errors.codes import MISSING_EVENT_ID, INVALID_ULID

for evt in result.events:
    if evt.status == "fail":
        for error in evt.errors:
            print(f"  code={error.code!r}")
            print(f"  field={error.field!r}")
            print(f"  message={error.message!r}")
            print(f"  value={error.value!r}")

            # React to specific codes
            if error.code == MISSING_EVENT_ID:
                print("  → Add an event_id to this event")
            elif error.code == INVALID_ULID:
                print("  → event_id must be a 26-char Crockford Base32 ULID")
```

---

### 2.6 OTel compatibility mode

```python
from agentobs_validate.validator.engine import validate_event
from agentobs_validate.validator.context import ValidationContext

# Event emitted by an OTel-native SDK
otel_event = {
    "eventId": "01HZQSN7PQVR2K4M0BXJD3GSTA",
    "timestamp": "2026-03-06T10:00:00.000Z",
    "eventType": "agent.plan.created",
    "source": "spanforge@1.0.0",
    "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
    "spanId": "00f067aa0ba902b7",
}

ctx = ValidationContext(otel_mode=True)
result = validate_event(1, otel_event, ctx)
print(result.status)  # "pass"
```

---

### 2.7 HMAC signature verification

```python
import base64, hashlib, hmac, json
from agentobs_validate.validator.engine import validate_event
from agentobs_validate.validator.context import ValidationContext

key = b"my-secret-key"

# Build a signed event
event = {
    "event_id": "01HZQSN7PQVR2K4M0BXJD3GSTA",
    "timestamp": "2026-03-06T10:00:00.000Z",
    "event_type": "agent.plan.created",
    "source": "spanforge@1.0.0",
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "00f067aa0ba902b7",
}
canonical = json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
digest = base64.b64encode(hmac.digest(key, canonical, hashlib.sha256)).decode()
event["signature"] = {"algorithm": "HMAC-SHA256", "value": digest}

# Validate with the key — HMAC digest is cryptographically verified
ctx = ValidationContext(key_bytes=key)
result = validate_event(1, event, ctx)
print(result.status)  # "pass"

# Wrong key produces SIGNATURE_MISMATCH
ctx_wrong = ValidationContext(key_bytes=b"wrong-key")
result_wrong = validate_event(1, event, ctx_wrong)
print(result_wrong.status)         # "fail"
print(result_wrong.errors[0].code)  # "SIGNATURE_MISMATCH"
```

---

### 2.8 Validate a JSONL file with a key and OTel mode

```python
from agentobs_validate.validator.engine import validate_stream
from agentobs_validate.validator.input_parser import iter_events
from agentobs_validate.validator.context import ValidationContext

ctx = ValidationContext(
    otel_mode=True,
    schema_version="0.1",
    key_bytes=open("signing.key", "rb").read().rstrip(b"\r\n "),
)

result = validate_stream(iter_events("events.jsonl"), ctx)
print(f"schema_version: {result.schema_version}")
print(f"valid={result.valid}, invalid={result.invalid}")
```

---

### 2.9 Export the JSON Schema

```python
from agentobs_validate.schema.json_schema import build_json_schema, export_schema

# As a Python dict
schema = build_json_schema("0.1")
print(schema["$schema"])   # "https://json-schema.org/draft/2020-12/schema"
print(schema["required"])  # ["event_id", "timestamp", ...]

# As a formatted JSON string
print(export_schema("0.1"))

# Write to disk
with open("agentobs-schema.json", "w") as f:
    f.write(export_schema("0.1"))
```

---

### 2.10 Check a specific error code

```python
from agentobs_validate.errors.codes import ALL_ERROR_CODES, SIGNATURE_MISMATCH

# Enumerate all known codes
for code in sorted(ALL_ERROR_CODES):
    print(code)

# Check if any event has a signature mismatch
has_mismatch = any(
    e.code == SIGNATURE_MISMATCH
    for evt in result.events
    for e in evt.errors
)
```

---

### 2.11 Integration example — validate events before publishing

```python
"""
Validate every event before writing it to a log store.
Reject invalid events so the log remains clean.
"""
import json
from agentobs_validate.validator.engine import validate_event
from agentobs_validate.validator.context import ValidationContext

ctx = ValidationContext()

def publish(events: list[dict]) -> None:
    valid_events = []
    for i, event in enumerate(events, start=1):
        result = validate_event(i, event, ctx)
        if result.status == "pass":
            valid_events.append(event)
        else:
            codes = [e.code for e in result.errors]
            print(f"Dropped event {i} — errors: {codes}")
    # write valid_events to your log store
    print(f"Published {len(valid_events)} / {len(events)} events")

publish([
    {
        "event_id": "01HZQSN7PQVR2K4M0BXJD3GSTA",
        "timestamp": "2026-03-06T10:00:00.000Z",
        "event_type": "agent.plan.created",
        "source": "spanforge@1.0.0",
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "span_id": "00f067aa0ba902b7",
    },
    {
        "event_id": "bad-id",  # will be dropped
        "timestamp": "2026-03-06T10:00:01.000Z",
        "event_type": "agent.tool.called",
        "source": "spanforge@1.0.0",
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "span_id": "00f067aa0ba902b8",
    },
])
```

---

## Part 3 — What's validated

Every event is checked against all of the following rules in a single pass.
All errors are collected before result is returned (**non-short-circuit**).

| Field        | Rule                                                              |
|--------------|-------------------------------------------------------------------|
| `event_id`   | Required. Must be a 26-char Crockford Base32 ULID                |
| `timestamp`  | Required. Must be RFC3339/ISO8601 (e.g. `2026-02-20T10:45:21Z`) |
| `event_type` | Required. Must match `domain.category.action` pattern           |
| `source`     | Required. Must match `name@MAJOR.MINOR.PATCH` pattern           |
| `trace_id`   | Required. Must be exactly 32 lowercase hex chars                 |
| `span_id`    | Required. Must be exactly 16 lowercase hex chars                 |
| `signature`  | Optional. When present: `algorithm` must be `HMAC-SHA256`, `value` must be valid base64. When `--key-file` provided: HMAC digest is cryptographically verified. |

See [errors.md](errors.md) for the complete error code reference.
