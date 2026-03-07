# Error Code Reference

All validation error codes emitted by `agentobs-validate` are listed below.  
Every error object in the JSON output (§11) and human output (§10) uses one of these codes.

---

## Error Object Schema

```json
{
  "code":    "INVALID_ULID",
  "field":   "event_id",
  "message": "event_id must be a 26-character Crockford base32 ULID",
  "value":   "not-a-ulid"
}
```

| Property  | Type            | Description                                  |
|-----------|-----------------|----------------------------------------------|
| `code`    | string          | Machine-readable error identifier            |
| `field`   | string          | The event field that failed validation       |
| `message` | string          | Human-readable description of the failure   |
| `value`   | any             | The actual value that was rejected           |

---

## `event_id` Errors  (spec §8.1)

| Code               | Trigger                                    | Example bad value          | How to fix                                          |
|--------------------|--------------------------------------------|----------------------------|-----------------------------------------------------|
| `MISSING_EVENT_ID` | `event_id` key is absent from the event   | *(field omitted)*          | Add `"event_id"` to every event                     |
| `INVALID_ULID`     | Value does not match the ULID character set or is not exactly 26 characters | `"abc123"` | Generate a valid ULID (e.g. Python `ulid.new()`)   |

**Pattern:** `^[0-9A-HJKMNP-TV-Z]{26}$`

---

## `timestamp` Errors  (spec §8.2)

| Code                | Trigger                                        | Example bad value         | How to fix                                         |
|---------------------|------------------------------------------------|---------------------------|----------------------------------------------------|
| `MISSING_TIMESTAMP` | `timestamp` key is absent from the event      | *(field omitted)*         | Add `"timestamp"` to every event                   |
| `INVALID_TIMESTAMP` | Value does not conform to RFC 3339 UTC format  | `"2026-02-20 10:45:21"`   | Use ISO 8601 UTC: `"2026-02-20T10:45:21.123Z"`     |

**Pattern:** `^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$`

---

## `event_type` Errors  (spec §8.3)

| Code                 | Trigger                                                    | Example bad value     | How to fix                                                  |
|----------------------|------------------------------------------------------------|-----------------------|-------------------------------------------------------------|
| `INVALID_EVENT_TYPE` | `event_type` is absent or does not match `domain.category.action` format | `"agentPlanCreated"` | Use three dot-separated lowercase segments: `"agent.plan.created"` |
| `INVALID_NAMESPACE`  | `domain` or `category` segment contains non-lowercase-alnum characters | `"Agent.plan.created"` | Lowercase all segments; only `[a-z0-9]` and `.` separators |

**Pattern:** `^[a-z0-9]+\.[a-z0-9]+\.[a-z0-9_]+$`

---

## `source` Errors  (spec §8.4)

| Code                   | Trigger                                          | Example bad value      | How to fix                                              |
|------------------------|--------------------------------------------------|------------------------|---------------------------------------------------------|
| `MISSING_SOURCE`       | `source` key is absent from the event            | *(field omitted)*      | Add `"source"` to every event                           |
| `INVALID_SOURCE_FORMAT`| Value does not match `name@semver` format        | `"spanforge-1.0.0"`    | Use `name@MAJOR.MINOR.PATCH`: `"spanforge@1.0.0"`      |

**Pattern:** `^[a-zA-Z0-9\-_]+@[0-9]+\.[0-9]+\.[0-9]+$`

---

## `trace_id` Errors  (spec §8.5)

| Code               | Trigger                                              | Example bad value        | How to fix                                          |
|--------------------|------------------------------------------------------|--------------------------|-----------------------------------------------------|
| `INVALID_TRACE_ID` | `trace_id` is absent or not exactly 32 lowercase hex chars | `"4BF92F35"` (uppercase) | Use exactly 32 lowercase hexadecimal characters. Compatible with W3C Trace Context / OpenTelemetry. |

**Pattern:** `^[0-9a-f]{32}$`

---

## `span_id` Errors  (spec §8.6)

| Code              | Trigger                                              | Example bad value      | How to fix                                          |
|-------------------|------------------------------------------------------|------------------------|-----------------------------------------------------|
| `INVALID_SPAN_ID` | `span_id` is absent or not exactly 16 lowercase hex chars | `"00f067aa"` (8 chars) | Use exactly 16 lowercase hexadecimal characters     |

**Pattern:** `^[0-9a-f]{16}$`

---

## `signature` Errors  (spec §8.7)

The `signature` field is optional. Errors are only reported when the key is present.

| Code                   | Trigger                                                      | Example bad value          | How to fix                                              |
|------------------------|--------------------------------------------------------------|----------------------------|---------------------------------------------------------|
| `UNSUPPORTED_ALGORITHM`| `signature.algorithm` is absent or not `"HMAC-SHA256"`      | `"RS256"`                  | Set `algorithm` to `"HMAC-SHA256"`                      |
| `INVALID_SIGNATURE`    | `signature.value` is absent, empty, or not valid base64      | `"not!base64"`             | Provide a valid base64-encoded HMAC-SHA256 digest       |
| `SIGNATURE_MISMATCH`   | Structural signature is valid but the HMAC digest does not match the computed value (only raised when `--key-file` / `key_bytes` is provided) | *(valid base64 but wrong key)* | Regenerate the signature using `HMAC-SHA256(canonical_event, key)` where `canonical_event = json.dumps(event_without_signature, sort_keys=True, separators=(',', ':'))` |

---

## Exit Codes

| Code | Condition                          |
|------|------------------------------------|
| `0`  | All events valid                   |
| `1`  | One or more validation errors      |
| `2`  | Input parse failure (bad JSON/JSONL) |
| `3`  | Internal / unexpected error        |

See [docs/ci.md](ci.md) for how to use exit codes in CI pipelines.
