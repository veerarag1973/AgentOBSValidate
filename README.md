# agentobs-validate

**Reference validation CLI for the [AgentOBS](https://github.com/veerarag1973/AgentOBSValidate) event standard.**

[![CI](https://github.com/veerarag1973/AgentOBSValidate/actions/workflows/tests.yml/badge.svg)](https://github.com/veerarag1973/AgentOBSValidate/actions)

---

## Overview

`agentobs-validate` validates **JSON or JSONL event streams** against the AgentOBS schema.  
If an event stream passes validation, it is considered **AgentOBS compliant**.

---

## Installation

```bash
pip install agentobs-validate
```

For development:

```bash
git clone https://github.com/veerarag1973/AgentOBSValidate.git
cd AgentOBSValidate
pip install -e ".[dev]"
```

---

## Quick Start

```bash
# Validate a JSONL stream
agentobs-validate events.jsonl

# JSON output for CI
agentobs-validate events.jsonl --json

# Strict mode (fail on warnings)
agentobs-validate events.jsonl --strict

# Read from STDIN
cat events.jsonl | agentobs-validate
```

---

## Exit Codes

| Code | Meaning                   |
|------|---------------------------|
| 0    | All events valid          |
| 1    | Validation errors present |
| 2    | Input parse failure       |
| 3    | Internal validator error  |

---

## Specification

See [agentobsvalidatespec.md](agentobsvalidatespec.md) for the full specification.

See [implementationplan.md](implementationplan.md) for the phased implementation plan.

---

## Running Tests

```bash
pytest
```

Targets ≥95% coverage.

---

## Status

`v0.1` — Foundation scaffold (Phase 0 complete). Validation engine in progress.
