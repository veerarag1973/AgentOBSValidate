# CI Integration Guide

`agentobs-validate` is designed as a **drop-in CI gate** — its exit code contract maps directly to `pass`/`fail` in every major CI system.

---

## Exit Code Contract  (spec §5)

| Exit Code | Condition                                     |
|-----------|-----------------------------------------------|
| `0`       | All events valid — **CI step passes**         |
| `1`       | One or more validation errors — **CI step fails** |
| `2`       | Input or configuration error (bad JSON/JSONL, unreadable file, unsupported schema version) |
| `3`       | Internal / unexpected validator error         |

---

## GitHub Actions

```yaml
- name: Validate AgentOBS events
  run: agentobs-validate events.jsonl

# For machine-parseable output in CI logs:
- name: Validate (JSON output)
  run: agentobs-validate events.jsonl --json | tee validation-report.json
```

Full workflow template: [`.github/workflows/validate.yml`](../.github/workflows/validate.yml)

---

## GitLab CI

```yaml
validate-events:
  image: python:3.11-slim
  script:
    - pip install agentobs-validate
    - agentobs-validate events.jsonl
  artifacts:
    when: on_failure
    paths:
      - validation-report.json
```

---

## CircleCI

```yaml
jobs:
  validate:
    docker:
      - image: cimg/python:3.11
    steps:
      - checkout
      - run:
          name: Install validator
          command: pip install agentobs-validate
      - run:
          name: Validate events
          command: agentobs-validate events.jsonl
```

---

## Parsing JSON output in CI scripts

Use `--json` to get a structured report suitable for downstream processing:

```bash
agentobs-validate events.jsonl --json > report.json
python - <<'EOF'
import json, sys
r = json.load(open("report.json"))
print(f"Checked: {r['summary']['events_checked']}")
print(f"Invalid: {r['summary']['invalid']}")
for e in r['events']:
    if e['status'] == 'fail':
        print(f"  Event {e['index']}: {[err['code'] for err in e['errors']]}")
EOF
```

---

## `--strict` mode

`--strict` is reserved for future warning-level rules.  
Currently it behaves identically to normal mode — exit `0` on all-valid, exit `1` on any failure.

```bash
agentobs-validate events.jsonl --strict
```

---

## Pinning the version

For reproducible CI, pin the package version in your `requirements.txt`:

```
agentobs-validate==0.1.0
```

Or with pip extras for development:

```bash
pip install "agentobs-validate[dev]==0.1.0"
```

---

See [docs/errors.md](errors.md) for the full error code reference.
