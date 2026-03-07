"""Integration tests for the CLI entry point.

Covers spec §4 (CLI Interface), §5 (Exit Codes), §10 (Human Output),
and §11 (JSON Output).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from agentobs_validate.cli.main import (
    EXIT_INTERNAL_ERROR,
    EXIT_INVALID,
    EXIT_PARSE_FAILURE,
    EXIT_VALID,
    main,
)

# ── Test event data ───────────────────────────────────────────────────────────

_VALID_EVENT: dict[str, str] = {
    "event_id": "01HZQSN7PQVR2K4M0BXJD3GSTW",
    "timestamp": "2024-01-01T00:00:00Z",
    "event_type": "agent.task.start",
    "source": "my-agent@1.0.0",
    "trace_id": "0123456789abcdef0123456789abcdef",
    "span_id": "0123456789abcdef",
}

# Valid JSONL line (single event)
VALID_JSONL: str = json.dumps(_VALID_EVENT) + "\n"

# Valid JSON array (single event)
VALID_JSON_ARRAY: str = json.dumps([_VALID_EVENT]) + "\n"

# Structurally valid JSON but schema-invalid (bad id, missing fields)
INVALID_JSONL: str = '{"event_id": "bad-id", "timestamp": "not-a-date"}\n'


# ── Helpers ───────────────────────────────────────────────────────────────────


def _write(tmp_path: Path, name: str, content: str) -> str:
    """Write *content* to *name* inside *tmp_path* and return the absolute path."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


# ── Valid input — human output (default) ─────────────────────────────────────


class TestValidInput:
    """Valid events exit 0; human output contains ✔ and a Summary line."""

    def test_valid_jsonl_file_exits_zero(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path])
        assert result.exit_code == EXIT_VALID

    def test_valid_jsonl_human_output_shows_tick(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path])
        assert "✔" in result.output

    def test_valid_jsonl_human_output_has_summary(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path])
        assert "Summary" in result.output

    def test_valid_json_array_file_exits_zero(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.json", VALID_JSON_ARRAY)
        result = runner.invoke(main, [path])
        assert result.exit_code == EXIT_VALID

    def test_multiple_valid_events_exits_zero(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL + VALID_JSONL)
        result = runner.invoke(main, [path])
        assert result.exit_code == EXIT_VALID


# ── Invalid input — human output ─────────────────────────────────────────────


class TestInvalidInput:
    """Schema-invalid events give exit 1; human output contains ✖."""

    def test_invalid_event_exits_one(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", INVALID_JSONL)
        result = runner.invoke(main, [path])
        assert result.exit_code == EXIT_INVALID

    def test_invalid_event_human_output_shows_cross(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", INVALID_JSONL)
        result = runner.invoke(main, [path])
        assert "✖" in result.output

    def test_mix_valid_and_invalid_exits_one(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL + INVALID_JSONL)
        result = runner.invoke(main, [path])
        assert result.exit_code == EXIT_INVALID


# ── Parse failures (exit 2) ───────────────────────────────────────────────────


class TestParseFailures:
    """Malformed input or missing file triggers exit 2 with an error message."""

    def test_nonexistent_file_exits_parse_failure(
        self, runner: CliRunner
    ) -> None:
        result = runner.invoke(main, ["/no/such/file.jsonl"])
        assert result.exit_code == EXIT_PARSE_FAILURE

    def test_nonexistent_file_emits_parse_error_message(
        self, runner: CliRunner
    ) -> None:
        result = runner.invoke(main, ["/no/such/file.jsonl"])
        assert "Parse error" in result.output

    def test_malformed_jsonl_exits_parse_failure(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", "{bad json\n")
        result = runner.invoke(main, [path])
        assert result.exit_code == EXIT_PARSE_FAILURE

    def test_malformed_json_array_exits_parse_failure(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.json", "[not valid json")
        result = runner.invoke(main, [path])
        assert result.exit_code == EXIT_PARSE_FAILURE


# ── Unexpected exceptions (exit 3) ───────────────────────────────────────────


class TestUnexpectedException:
    """Unexpected exceptions give exit 3 with an internal-error message."""

    def test_unexpected_exception_exits_internal_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        with patch(
            "agentobs_validate.cli.main.validate_stream",
            side_effect=RuntimeError("unexpected boom"),
        ):
            result = runner.invoke(main, [path])
        assert result.exit_code == EXIT_INTERNAL_ERROR

    def test_unexpected_exception_emits_internal_error_message(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        with patch(
            "agentobs_validate.cli.main.validate_stream",
            side_effect=RuntimeError("unexpected boom"),
        ):
            result = runner.invoke(main, [path])
        assert "Internal error" in result.output


# ── JSON output (--json flag) ─────────────────────────────────────────────────


class TestJsonOutput:
    """--json flag emits machine-readable JSON per spec §11."""

    def test_json_flag_produces_valid_json(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path, "--json"])
        parsed = json.loads(result.output)
        assert isinstance(parsed, dict)

    def test_json_flag_exits_zero_on_valid(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path, "--json"])
        assert result.exit_code == EXIT_VALID

    def test_json_flag_exits_one_on_invalid(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", INVALID_JSONL)
        result = runner.invoke(main, [path, "--json"])
        assert result.exit_code == EXIT_INVALID

    def test_json_output_has_valid_count(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path, "--json"])
        parsed = json.loads(result.output)
        assert "valid" in parsed["summary"]

    def test_json_output_invalid_event_has_errors_key(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", INVALID_JSONL)
        result = runner.invoke(main, [path, "--json"])
        parsed = json.loads(result.output)
        assert any("errors" in evt for evt in parsed["events"])

    def test_json_output_valid_event_omits_errors_key(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path, "--json"])
        parsed = json.loads(result.output)
        for evt in parsed["events"]:
            assert "errors" not in evt


# ── --strict flag ─────────────────────────────────────────────────────────────


class TestStrictFlag:
    """--strict is accepted; exit behaviour matches normal mode (spec §4, reserved)."""

    def test_strict_valid_input_exits_zero(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path, "--strict"])
        assert result.exit_code == EXIT_VALID

    def test_strict_invalid_input_exits_one(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", INVALID_JSONL)
        result = runner.invoke(main, [path, "--strict"])
        assert result.exit_code == EXIT_INVALID


# ── STDIN input ───────────────────────────────────────────────────────────────


class TestStdinInput:
    """Omitting FILE or passing '-' reads from STDIN."""

    def test_no_file_arg_reads_stdin_valid(self, runner: CliRunner) -> None:
        result = runner.invoke(main, [], input=VALID_JSONL)
        assert result.exit_code == EXIT_VALID

    def test_no_file_arg_reads_stdin_invalid(self, runner: CliRunner) -> None:
        result = runner.invoke(main, [], input=INVALID_JSONL)
        assert result.exit_code == EXIT_INVALID

    def test_stdin_malformed_exits_parse_failure(self, runner: CliRunner) -> None:
        result = runner.invoke(main, [], input="{bad json\n")
        assert result.exit_code == EXIT_PARSE_FAILURE

    def test_dash_arg_reads_stdin_valid(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["-"], input=VALID_JSONL)
        assert result.exit_code == EXIT_VALID

    def test_dash_arg_reads_stdin_invalid(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["-"], input=INVALID_JSONL)
        assert result.exit_code == EXIT_INVALID


# ── Roadmap features (now fully implemented) ─────────────────────────────────

_OTEL_VALID_EVENT = {
    "eventId": "01HZQSN7PQVR2K4M0BXJD3GSTW",
    "timestamp": "2024-01-01T00:00:00Z",
    "eventType": "agent.task.start",
    "source": "my-agent@1.0.0",
    "traceId": "0123456789abcdef0123456789abcdef",
    "spanId": "0123456789abcdef",
}


class TestExportSchema:
    """--export-schema prints a JSON Schema document and exits 0."""

    def test_export_schema_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--export-schema"])
        assert result.exit_code == EXIT_VALID

    def test_export_schema_output_is_valid_json(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--export-schema"])
        doc = json.loads(result.output)
        assert isinstance(doc, dict)

    def test_export_schema_has_dollar_schema(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--export-schema"])
        doc = json.loads(result.output)
        assert "$schema" in doc

    def test_export_schema_has_required_fields(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--export-schema"])
        doc = json.loads(result.output)
        assert "event_id" in doc["required"]
        assert "trace_id" in doc["required"]

    def test_export_schema_with_version(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--export-schema", "--schema-version", "0.1"])
        assert result.exit_code == EXIT_VALID

    def test_export_schema_unsupported_version(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--export-schema", "--schema-version", "9.9"])
        assert result.exit_code == EXIT_PARSE_FAILURE


class TestOtelMode:
    """--otel accepts camelCase field-name aliases from OTel/W3C Trace Context."""

    def test_otel_camelcase_event_passes(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--otel"], input=json.dumps(_OTEL_VALID_EVENT) + "\n")
        assert result.exit_code == EXIT_VALID

    def test_otel_mode_exit_zero_on_valid(self, runner: CliRunner, tmp_path: Path) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path, "--otel"])
        assert result.exit_code == EXIT_VALID

    def test_otel_mode_exit_one_on_invalid(self, runner: CliRunner, tmp_path: Path) -> None:
        path = _write(tmp_path, "events.jsonl", INVALID_JSONL)
        result = runner.invoke(main, [path, "--otel"])
        assert result.exit_code == EXIT_INVALID

    def test_otel_mode_json_output(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--otel", "--json"], input=json.dumps(_OTEL_VALID_EVENT) + "\n")
        assert result.exit_code == EXIT_VALID
        doc = json.loads(result.output)
        assert doc["summary"]["valid"] == 1


class TestSchemaVersion:
    """--schema-version validates against a specific schema version."""

    def test_supported_version_exits_zero(self, runner: CliRunner, tmp_path: Path) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path, "--schema-version", "0.1"])
        assert result.exit_code == EXIT_VALID

    def test_unsupported_version_exits_parse_failure(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path, "--schema-version", "0.2"])
        assert result.exit_code == EXIT_PARSE_FAILURE

    def test_unsupported_version_message(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path, "--schema-version", "0.2"])
        assert "not supported" in result.output

    def test_schema_version_in_json_summary(self, runner: CliRunner, tmp_path: Path) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path, "--json", "--schema-version", "0.1"])
        doc = json.loads(result.output)
        assert doc["summary"]["schema_version"] == "0.1"

    def test_schema_version_in_human_summary(self, runner: CliRunner, tmp_path: Path) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path, "--schema-version", "0.1"])
        assert "schema_version: 0.1" in result.output


class TestKeyFile:
    """--key-file enables HMAC-SHA256 cryptographic signature verification."""

    @staticmethod
    def _make_signed_event(key_bytes: bytes) -> str:
        import base64
        import hashlib
        import hmac
        import json
        event = {
            "event_id": "01HZQSN7PQVR2K4M0BXJD3GSTW",
            "timestamp": "2024-01-01T00:00:00Z",
            "event_type": "agent.task.start",
            "source": "my-agent@1.0.0",
            "trace_id": "0123456789abcdef0123456789abcdef",
            "span_id": "0123456789abcdef",
        }
        canonical = json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hmac.digest(key_bytes, canonical, hashlib.sha256)
        sig_value = base64.b64encode(digest).decode()
        event["signature"] = {"algorithm": "HMAC-SHA256", "value": sig_value}
        return json.dumps(event) + "\n"

    def test_missing_key_file_exits_parse_failure(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path, "--key-file", "/no/such/key.bin"])
        assert result.exit_code == EXIT_PARSE_FAILURE

    def test_missing_key_file_message(self, runner: CliRunner, tmp_path: Path) -> None:
        path = _write(tmp_path, "events.jsonl", VALID_JSONL)
        result = runner.invoke(main, [path, "--key-file", "/no/such/key.bin"])
        assert "Cannot read key file" in result.output

    def test_valid_signature_passes(self, runner: CliRunner, tmp_path: Path) -> None:
        key = b"my-secret-key"
        key_path = _write(tmp_path, "signing.key", key.decode())
        event_line = self._make_signed_event(key)
        events_path = _write(tmp_path, "events.jsonl", event_line)
        result = runner.invoke(main, [events_path, "--key-file", key_path])
        assert result.exit_code == EXIT_VALID

    def test_wrong_key_fails_signature(self, runner: CliRunner, tmp_path: Path) -> None:
        key = b"my-secret-key"
        wrong_key_path = _write(tmp_path, "wrong.key", "wrong-key")
        event_line = self._make_signed_event(key)
        events_path = _write(tmp_path, "events.jsonl", event_line)
        result = runner.invoke(main, [events_path, "--key-file", wrong_key_path])
        assert result.exit_code == EXIT_INVALID

    def test_without_key_file_signature_not_verified(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        # Structural-only check: any valid base64 passes without a key file
        key = b"my-secret-key"
        event_line = self._make_signed_event(key)
        events_path = _write(tmp_path, "events.jsonl", event_line)
        result = runner.invoke(main, [events_path])
        assert result.exit_code == EXIT_VALID

