# Roadmap

All planned v0.1 features are now fully implemented.  This document
records what was built and notes areas for future development.

---

## `--export-schema`  (spec §18.1)

**Status:** ✅ Implemented in v0.1.0

Exports the full AgentOBS event envelope as a JSON Schema (Draft 2020-12) document.

```bash
agentobs-validate --export-schema > agentobs-schema.json
agentobs-validate --export-schema --schema-version 0.1
```

The schema covers all required and optional fields with types, regex patterns, and
descriptions.  It can be used with `jsonschema`, `ajv`, OpenAPI generators, and
IDE JSON validators.  Python SDK: `build_json_schema()` / `export_schema()`.

---

## `--otel`  (spec §18.2)

**Status:** ✅ Implemented in v0.1.0

Enables OpenTelemetry / W3C Trace Context compatibility: accepts camelCase
field-name aliases in addition to AgentOBS snake_case names.

```bash
agentobs-validate events.jsonl --otel
```

Alias mapping:

| OTel camelCase | AgentOBS snake_case |
|----------------|---------------------|
| `eventId`      | `event_id`          |
| `eventType`    | `event_type`        |
| `traceId`      | `trace_id`          |
| `spanId`       | `span_id`           |

Aliases are only renamed when the canonical name is absent — fully snake_case events
pass through unchanged.  Python SDK: `ValidationContext(otel_mode=True)`.

---

## `--schema-version VERSION`  (spec §18.3)

**Status:** ✅ Implemented in v0.1.0

Pins validation against a specific schema version.  The version appears in all
output (human and JSON).  Supplying an unsupported version exits with code 2.

```bash
agentobs-validate events.jsonl --schema-version 0.1
```

Currently supported versions: **0.1**

Python SDK: `ValidationContext(schema_version="0.1")`.

---

## `--key-file FILE`  (spec §18.4)

**Status:** ✅ Implemented in v0.1.0

Loads a raw HMAC-SHA256 signing key and cryptographically verifies the digest of
every event that carries a `signature` block.  Events whose digest does not match
are rejected with `SIGNATURE_MISMATCH`.

```bash
agentobs-validate events.jsonl --key-file signing.key
```

Canonical message: event dict without the `signature` key, serialised with
`json.dumps(sort_keys=True, separators=(',', ':'))` and encoded as UTF-8.

Python SDK: `ValidationContext(key_bytes=b"...")`.

---

## Future work

- Multi-version schema registry (v0.2+)
- Plugin system for custom field validators
- `--output-file` flag to write reports to disk without shell redirection
- GitHub Action packaging (`uses: veerarag1973/AgentOBSValidate@v0.1`)

These will be tracked in the GitHub issue tracker at
<https://github.com/veerarag1973/AgentOBSValidate>.
