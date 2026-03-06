"""Phase 0 scaffold tests.

Covers:
- Version flag (--version)
- Help flags (--help, -h)
- Help content correctness
- Flag acceptance (--json, --strict)
- Stub exit code contract (exit 3 until engine is wired)
- Package and sub-package importability
- __version__ format and consistency
"""

from __future__ import annotations

import importlib

import pytest
from click.testing import CliRunner

from agentobs_validate import __version__
from agentobs_validate.cli.main import (
    EXIT_INTERNAL_ERROR,
    EXIT_INVALID,
    EXIT_PARSE_FAILURE,
    EXIT_VALID,
    main,
)


# ── Exit code constants ───────────────────────────────────────────────────────


class TestExitCodeConstants:
    """Exit code constants must match spec §5 exactly."""

    def test_exit_valid_is_zero(self) -> None:
        assert EXIT_VALID == 0

    def test_exit_invalid_is_one(self) -> None:
        assert EXIT_INVALID == 1

    def test_exit_parse_failure_is_two(self) -> None:
        assert EXIT_PARSE_FAILURE == 2

    def test_exit_internal_error_is_three(self) -> None:
        assert EXIT_INTERNAL_ERROR == 3

    def test_all_codes_are_distinct(self) -> None:
        codes = {EXIT_VALID, EXIT_INVALID, EXIT_PARSE_FAILURE, EXIT_INTERNAL_ERROR}
        assert len(codes) == 4


# ── --version ────────────────────────────────────────────────────────────────


class TestVersionFlag:
    """--version must exit 0 and print the current version string."""

    def test_version_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0

    def test_version_contains_semver(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert __version__ in result.output

    def test_version_contains_program_name(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert "agentobs-validate" in result.output

    def test_version_matches_package_init(self, runner: CliRunner) -> None:
        import agentobs_validate

        result = runner.invoke(main, ["--version"])
        assert agentobs_validate.__version__ in result.output


# ── --help / -h ──────────────────────────────────────────────────────────────


class TestHelpFlag:
    """Help flags must exit 0 and surface key spec elements in the help text."""

    def test_long_help_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0

    def test_short_help_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["-h"])
        assert result.exit_code == 0

    def test_long_and_short_help_match(self, runner: CliRunner) -> None:
        long_result = runner.invoke(main, ["--help"])
        short_result = runner.invoke(main, ["-h"])
        assert long_result.output == short_result.output

    def test_help_documents_file_argument(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert "FILE" in result.output

    def test_help_documents_json_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert "--json" in result.output

    def test_help_documents_strict_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert "--strict" in result.output

    def test_help_documents_stdin_usage(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert "STDIN" in result.output

    def test_help_documents_exit_codes(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert "Exit codes" in result.output

    def test_help_documents_version_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert "--version" in result.output


# ── Flag acceptance ───────────────────────────────────────────────────────────


class TestFlagAcceptance:
    """All CLI flags from spec §4 must be accepted without click usage errors."""

    def test_json_flag_accepted(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["events.jsonl", "--json"])
        # Flag is accepted by click; non-existent file → ParseError → exit 2.
        assert result.exit_code == EXIT_PARSE_FAILURE

    def test_strict_flag_accepted(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["events.jsonl", "--strict"])
        assert result.exit_code == EXIT_PARSE_FAILURE

    def test_json_and_strict_combined(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["events.jsonl", "--json", "--strict"])
        assert result.exit_code == EXIT_PARSE_FAILURE

    def test_flags_before_file(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--json", "--strict", "events.jsonl"])
        assert result.exit_code == EXIT_PARSE_FAILURE

    def test_unknown_flag_is_rejected(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--undefined-flag"])
        assert result.exit_code != 0

    def test_unknown_flag_is_not_exit_3(self, runner: CliRunner) -> None:
        # Unknown flags should trigger click UsageError (exit 2), not internal error.
        result = runner.invoke(main, ["--undefined-flag"])
        assert result.exit_code != EXIT_INTERNAL_ERROR


# ── Package imports ───────────────────────────────────────────────────────────


class TestPackageImports:
    """All declared packages must be importable without errors."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "agentobs_validate",
            "agentobs_validate.cli",
            "agentobs_validate.cli.main",
            "agentobs_validate.validator",
            "agentobs_validate.schema",
            "agentobs_validate.errors",
        ],
    )
    def test_module_importable(self, module_path: str) -> None:
        mod = importlib.import_module(module_path)
        assert mod is not None

    def test_main_function_is_callable(self) -> None:
        from agentobs_validate.cli.main import main as cli_main

        assert callable(cli_main)


# ── __version__ contract ──────────────────────────────────────────────────────


class TestVersionContract:
    """__version__ must be a valid semver string in MAJOR.MINOR.PATCH format."""

    def test_version_is_string(self) -> None:
        assert isinstance(__version__, str)

    def test_version_is_three_parts(self) -> None:
        parts = __version__.split(".")
        assert len(parts) == 3, f"Expected 3 parts, got {parts}"

    def test_version_parts_are_numeric(self) -> None:
        parts = __version__.split(".")
        for part in parts:
            assert part.isdigit(), f"Non-numeric version part: {part!r}"

    def test_version_major_is_zero(self) -> None:
        major = int(__version__.split(".")[0])
        assert major == 0, "Phase 0 — major version must be 0"

    def test_version_exported_from_package(self) -> None:
        import agentobs_validate

        assert hasattr(agentobs_validate, "__version__")
        assert agentobs_validate.__version__ == __version__

    def test_version_in_all_list(self) -> None:
        import agentobs_validate

        assert "__version__" in agentobs_validate.__all__
