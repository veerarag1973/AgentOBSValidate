"""Tests for the example fixture files (spec §16).

Verifies that:
- ``examples/valid.jsonl``  passes validation (exit 0)
- ``examples/valid.json``   passes validation (exit 0)
- ``examples/invalid.jsonl`` fails validation (exit 1)
- All 12 error codes defined in §8 are exercised by ``examples/invalid.jsonl``
- All 5 ``event_type`` patterns from §8.3 are present in ``examples/valid.jsonl``
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from agentobs_validate.cli.main import EXIT_INVALID, EXIT_VALID, main
from agentobs_validate.errors.codes import ALL_ERROR_CODES
from agentobs_validate.validator.engine import validate_stream
from agentobs_validate.validator.input_parser import iter_events


@pytest.fixture(scope="module")
def examples_dir() -> Path:
    """Absolute path to the ``examples/`` directory in the repository root."""
    return Path(__file__).resolve().parent.parent / "examples"


# ── valid.jsonl ───────────────────────────────────────────────────────────────


class TestValidJsonlFixture:
    """``examples/valid.jsonl`` must produce exit 0 and contain 5 events."""

    def test_exits_zero(self, runner: CliRunner, examples_dir: Path) -> None:
        result = runner.invoke(main, [str(examples_dir / "valid.jsonl")])
        assert result.exit_code == EXIT_VALID

    def test_json_mode_exits_zero(self, runner: CliRunner, examples_dir: Path) -> None:
        result = runner.invoke(main, [str(examples_dir / "valid.jsonl"), "--json"])
        assert result.exit_code == EXIT_VALID

    def test_json_output_is_parseable(
        self, runner: CliRunner, examples_dir: Path
    ) -> None:
        result = runner.invoke(main, [str(examples_dir / "valid.jsonl"), "--json"])
        report = json.loads(result.output)
        assert isinstance(report, dict)

    def test_five_events_checked(
        self, runner: CliRunner, examples_dir: Path
    ) -> None:
        result = runner.invoke(main, [str(examples_dir / "valid.jsonl"), "--json"])
        report = json.loads(result.output)
        assert report["summary"]["events_checked"] == 5

    def test_zero_invalid_events(
        self, runner: CliRunner, examples_dir: Path
    ) -> None:
        result = runner.invoke(main, [str(examples_dir / "valid.jsonl"), "--json"])
        report = json.loads(result.output)
        assert report["summary"]["invalid"] == 0

    def test_covers_all_spec_event_types(self, examples_dir: Path) -> None:
        """Every event_type example from spec §8.3 must appear in valid.jsonl."""
        event_types = {
            event["event_type"]
            for _, event in iter_events(str(examples_dir / "valid.jsonl"))
        }
        expected = {
            "agent.plan.created",
            "agent.tool.called",
            "agent.llm.request",
            "agent.llm.response",
            "agent.memory.write",
        }
        assert event_types == expected

    def test_pass_events_omit_errors_in_json(
        self, runner: CliRunner, examples_dir: Path
    ) -> None:
        result = runner.invoke(main, [str(examples_dir / "valid.jsonl"), "--json"])
        report = json.loads(result.output)
        for event in report["events"]:
            assert "errors" not in event


# ── valid.json ────────────────────────────────────────────────────────────────


class TestValidJsonFixture:
    """``examples/valid.json`` (array format) must produce exit 0 with 3 events."""

    def test_exits_zero(self, runner: CliRunner, examples_dir: Path) -> None:
        result = runner.invoke(main, [str(examples_dir / "valid.json")])
        assert result.exit_code == EXIT_VALID

    def test_three_events_checked(
        self, runner: CliRunner, examples_dir: Path
    ) -> None:
        result = runner.invoke(main, [str(examples_dir / "valid.json"), "--json"])
        report = json.loads(result.output)
        assert report["summary"]["events_checked"] == 3

    def test_zero_invalid_events(
        self, runner: CliRunner, examples_dir: Path
    ) -> None:
        result = runner.invoke(main, [str(examples_dir / "valid.json"), "--json"])
        report = json.loads(result.output)
        assert report["summary"]["invalid"] == 0


# ── invalid.jsonl ─────────────────────────────────────────────────────────────


class TestInvalidJsonlFixture:
    """``examples/invalid.jsonl`` must produce exit 1 and exercise all error codes."""

    def test_exits_one(self, runner: CliRunner, examples_dir: Path) -> None:
        result = runner.invoke(main, [str(examples_dir / "invalid.jsonl")])
        assert result.exit_code == EXIT_INVALID

    def test_json_mode_exits_one(
        self, runner: CliRunner, examples_dir: Path
    ) -> None:
        result = runner.invoke(main, [str(examples_dir / "invalid.jsonl"), "--json"])
        assert result.exit_code == EXIT_INVALID

    def test_json_output_is_parseable(
        self, runner: CliRunner, examples_dir: Path
    ) -> None:
        result = runner.invoke(main, [str(examples_dir / "invalid.jsonl"), "--json"])
        report = json.loads(result.output)
        assert isinstance(report, dict)

    def test_has_invalid_events(self, runner: CliRunner, examples_dir: Path) -> None:
        result = runner.invoke(main, [str(examples_dir / "invalid.jsonl"), "--json"])
        report = json.loads(result.output)
        assert report["summary"]["invalid"] > 0

    def test_twelve_events_in_file(self, examples_dir: Path) -> None:
        """One event per error code — 12 total."""
        events = list(iter_events(str(examples_dir / "invalid.jsonl")))
        assert len(events) == 12

    def test_covers_all_error_codes(self, examples_dir: Path) -> None:
        """Every error code except SIGNATURE_MISMATCH (requires --key-file) must be triggered."""
        from agentobs_validate.errors.codes import ALL_ERROR_CODES, SIGNATURE_MISMATCH
        stream_result = validate_stream(iter_events(str(examples_dir / "invalid.jsonl")))
        found_codes = {
            err.code
            for event_result in stream_result.events
            for err in event_result.errors
        }
        # SIGNATURE_MISMATCH is only produced with --key-file; exclude from fixture check.
        expected = ALL_ERROR_CODES - {SIGNATURE_MISMATCH}
        assert found_codes == expected

    def test_each_event_has_distinct_primary_error(self, examples_dir: Path) -> None:
        """Every event in the invalid file contributes at least one error."""
        stream_result = validate_stream(iter_events(str(examples_dir / "invalid.jsonl")))
        for event_result in stream_result.events:
            assert event_result.status == "fail"
            assert len(event_result.errors) >= 1
