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
    "trace_id": "0123456789abcdef",
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
