"""CLI entry point for agentobs-validate.

Maps to spec §4 (CLI Interface) and §5 (Exit Codes).
"""

from __future__ import annotations

import sys

import click

from agentobs_validate import __version__
from agentobs_validate.validator.engine import validate_stream
from agentobs_validate.validator.formatters import format_human, format_json
from agentobs_validate.validator.input_parser import ParseError, iter_events

# Exit codes per spec §5
EXIT_VALID = 0
EXIT_INVALID = 1
EXIT_PARSE_FAILURE = 2
EXIT_INTERNAL_ERROR = 3


@click.command(
    name="agentobs-validate",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.argument(
    "file",
    required=False,
    default=None,
    metavar="FILE",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Emit results as JSON (machine-readable, for CI).",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Treat warnings as errors (fail on any non-compliant event).",
)
@click.version_option(
    version=__version__,
    prog_name="agentobs-validate",
)
def main(file: str | None, output_json: bool, strict: bool) -> None:
    """Validate AgentOBS event streams against the AgentOBS schema.

    FILE is the path to a .json or .jsonl event file.
    Omit FILE (or pass -) to read from STDIN.

    \b
    Exit codes:
      0 — all events valid
      1 — validation errors present
      2 — input parse failure
      3 — internal validator error
    """
    source = None if (file is None or file == "-") else file
    try:
        result = validate_stream(iter_events(source))
    except ParseError as exc:
        click.echo(f"Parse error: {exc}", err=True)
        sys.exit(EXIT_PARSE_FAILURE)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Internal error: {exc}", err=True)
        sys.exit(EXIT_INTERNAL_ERROR)
    if output_json:
        click.echo(format_json(result))
    else:
        click.echo(format_human(result))
    sys.exit(EXIT_VALID if result.invalid == 0 else EXIT_INVALID)
