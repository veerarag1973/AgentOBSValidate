# AgentOBS Tool Specification

# `agentobs-validate`

**Version:** 0.1
**Status:** FOUNDATION TOOL
**Priority:** P0
**Maintainer:** SpanForge

---

# 1. Purpose

`agentobs-validate` is the **reference validation CLI** for the **AgentOBS event standard**.

It validates **JSON or JSONL event streams** against the AgentOBS schema and enforces structural compliance.

This tool acts as the **compliance gatekeeper** for the ecosystem.

If an event stream passes validation, it is considered **AgentOBS compliant**.

---

# 2. Design Goals

1. **Deterministic validation**
2. **Fast enough for CI**
3. **Human-readable errors**
4. **Machine-readable output**
5. **Strict schema enforcement**
6. **Zero configuration required**

---

# 3. Supported Input Formats

### 3.1 JSON

Single file containing:

```
[
  {event1},
  {event2}
]
```

---

### 3.2 JSONL

Each line contains one event.

Example:

```
{event}
{event}
{event}
```

JSONL is the **recommended format for streams and logs**.

---

# 4. CLI Interface

### Basic

```
agentobs-validate events.jsonl
```

---

### JSON output (for CI)

```
agentobs-validate events.jsonl --json
```

---

### Strict mode

Fails on warnings.

```
agentobs-validate events.jsonl --strict
```

---

### Validate from STDIN

```
cat events.jsonl | agentobs-validate
```

---

# 5. Exit Codes

| Code | Meaning                   |
| ---- | ------------------------- |
| 0    | All events valid          |
| 1    | Validation errors present |
| 2    | Input parse failure       |
| 3    | Internal validator error  |

---

# 6. Event Validation Rules

Each event must satisfy **all required envelope constraints**.

---

# 7. Required Envelope Fields

Every event **must include**:

```
event_id
timestamp
event_type
source
trace_id
span_id
```

---

# 8. Field Specifications

---

# 8.1 `event_id`

**Type**

```
string
```

**Format**

ULID

Example

```
01HZY7M4YQZB3D0V4K6Z5R9F7A
```

Regex

```
^[0-9A-HJKMNP-TV-Z]{26}$
```

Validation errors

```
INVALID_ULID
MISSING_EVENT_ID
```

---

# 8.2 `timestamp`

**Type**

```
string
```

**Format**

RFC3339 / ISO8601

Example

```
2026-02-20T10:45:21.123Z
```

Errors

```
INVALID_TIMESTAMP
MISSING_TIMESTAMP
```

---

# 8.3 `event_type`

**Type**

```
string
```

**Namespace Pattern**

```
domain.category.action
```

Example

```
agent.plan.created
agent.tool.called
agent.llm.request
agent.llm.response
agent.memory.write
```

Regex

```
^[a-z0-9]+\.[a-z0-9]+\.[a-z0-9_]+$
```

Errors

```
INVALID_EVENT_TYPE
INVALID_NAMESPACE
```

---

# 8.4 `source`

Identifies the emitting component.

**Format**

```
name@semver
```

Example

```
langchain@0.2.11
autogen@0.4.1
spanforge@1.0.0
agent-runtime@0.9.2
```

Regex

```
^[a-zA-Z0-9\-_]+@[0-9]+\.[0-9]+\.[0-9]+$
```

Errors

```
INVALID_SOURCE_FORMAT
MISSING_SOURCE
```

---

# 8.5 `trace_id`

**Type**

```
string
```

**Format**

16 or 32 byte hex.

Example

```
4bf92f3577b34da6a3ce929d0e0e4736
```

Regex

```
^[0-9a-f]{16,32}$
```

Errors

```
INVALID_TRACE_ID
```

---

# 8.6 `span_id`

**Type**

```
string
```

**Format**

Hex

Example

```
00f067aa0ba902b7
```

Regex

```
^[0-9a-f]{16}$
```

Errors

```
INVALID_SPAN_ID
```

---

# 8.7 `signature` (Optional)

HMAC signature validating event integrity.

Structure

```
signature: {
  algorithm: "HMAC-SHA256",
  key_id: "spanforge-key-1",
  value: "base64..."
}
```

Validation:

```
algorithm must equal HMAC-SHA256
value must be valid base64
```

Errors

```
INVALID_SIGNATURE
UNSUPPORTED_ALGORITHM
```

---

# 9. Validation Process

For each event:

```
parse event
validate envelope fields
validate formats
validate namespace
validate optional signature
emit validation result
```

Processing is **stream-safe** for JSONL.

---

# 10. Human Output Format

Default CLI output.

Example:

```
✔ Event 1  valid
✔ Event 2  valid
✖ Event 3  INVALID_ULID
✖ Event 4  INVALID_EVENT_TYPE

Summary
------
events_checked: 4
valid: 2
invalid: 2
```

---

# 11. JSON Output Format

Enabled via `--json`.

Example:

```
{
  "summary": {
    "events_checked": 4,
    "valid": 2,
    "invalid": 2
  },
  "events": [
    {
      "index": 1,
      "status": "pass"
    },
    {
      "index": 2,
      "status": "pass"
    },
    {
      "index": 3,
      "status": "fail",
      "errors": [
        {
          "code": "INVALID_ULID",
          "field": "event_id"
        }
      ]
    }
  ]
}
```

---

# 12. Error Object Schema

```
{
  "code": "INVALID_EVENT_TYPE",
  "field": "event_type",
  "message": "event_type must match domain.category.action",
  "value": "agenttoolcalled"
}
```

Fields

| Field   | Description                |
| ------- | -------------------------- |
| code    | machine readable error     |
| field   | offending field            |
| message | human readable explanation |
| value   | original invalid value     |

---

# 13. CI Integration

Typical CI usage:

```
agentobs-validate events.jsonl --json
```

CI rule:

```
if exit_code != 0
  fail build
```

Example GitHub Actions step:

```
- name: Validate AgentOBS events
  run: agentobs-validate events.jsonl
```

---

# 14. Performance Requirements

Validator must handle:

```
100k events/sec
```

for JSONL streams.

Memory usage must remain:

```
O(1)
```

for streaming mode.

---

# 15. Implementation Reference

Recommended languages:

* Go
* Rust
* Python (reference implementation)

Primary libraries:

```
ULID parser
JSON streaming parser
regex validator
```

---

# 16. Repository Structure

```
agentobs-validate/

cmd/
   agentobs-validate/

pkg/
   validator/
   schema/
   errors/

examples/
   valid.jsonl
   invalid.jsonl

docs/
   spec.md
```

---

# 17. Example Valid Event

```
{
  "event_id": "01HZY7M4YQZB3D0V4K6Z5R9F7A",
  "timestamp": "2026-02-20T10:45:21.123Z",
  "event_type": "agent.tool.called",
  "source": "langchain@0.2.11",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7"
}
```

---

# 18. Roadmap

Future features:

```
JSON Schema export
OpenTelemetry compatibility mode
schema version negotiation
signature verification keys
streaming validation server
```

---

# 19. Ecosystem Role

`agentobs-validate` is expected to become:

```
the official compliance validator
for AgentOBS event producers
```

All AgentOBS SDKs should pass this validator in CI.
