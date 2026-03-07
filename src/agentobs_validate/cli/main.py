"""CLI entry point for agentobs-validate.

Maps to spec §4 (CLI Interface) and §5 (Exit Codes).
"""

from __future__ import annotations

import sys

import click

from agentobs_validate import __version__
from agentobs_validate.schema.json_schema import (
    SUPPORTED_VERSIONS as SUPPORTED_SCHEMA_VERSIONS,
    export_schema as do_export_schema,
)
from agentobs_validate.validator.context import ValidationContext
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
@click.option(
    "--export-schema",
    "export_schema",
    is_flag=True,
    default=False,
    help="Export JSON Schema (Draft 2020-12) for the AgentOBS event envelope and exit.",
)
@click.option(
    "--otel",
    is_flag=True,
    default=False,
    help=(
        "OpenTelemetry compatibility mode: accept camelCase field-name aliases "
        "(traceId, spanId, eventId, eventType) in addition to AgentOBS snake_case names."
    ),
)
@click.option(
    "--schema-version",
    "schema_version",
    default=None,
    metavar="VERSION",
    help=f"Validate against a specific schema version (supported: {', '.join(sorted(SUPPORTED_SCHEMA_VERSIONS))}).",
)
@click.option(
    "--key-file",
    "key_file",
    default=None,
    metavar="FILE",
    help=(
        "Path to a file containing the HMAC-SHA256 signing key. "
        "When provided, events with a signature block are cryptographically verified."
    ),
)
@click.version_option(
    version=__version__,
    prog_name="agentobs-validate",
)
def main(
    file: str | None,
    output_json: bool,
    strict: bool,
    export_schema: bool,
    otel: bool,
    schema_version: str | None,
    key_file: str | None,
) -> None:
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
    # ── Schema version validation ────────────────────────────────────────────
    ver = schema_version or "0.1"
    if ver not in SUPPORTED_SCHEMA_VERSIONS:
        supported = ", ".join(sorted(SUPPORTED_SCHEMA_VERSIONS))
        click.echo(
            f"Schema version {ver!r} is not supported. Supported versions: {supported}",
            err=True,
        )
        sys.exit(EXIT_PARSE_FAILURE)

    # ── --export-schema: print JSON Schema and exit ──────────────────────────
    if export_schema:
        click.echo(do_export_schema(ver))
        sys.exit(EXIT_VALID)

    # ── --key-file: load HMAC key bytes ──────────────────────────────────────
    key_bytes: bytes | None = None
    if key_file is not None:
        try:
            with open(key_file, "rb") as fh:
                key_bytes = fh.read().rstrip(b"\r\n ")
        except OSError as exc:
            click.echo(f"Cannot read key file: {exc}", err=True)
            sys.exit(EXIT_PARSE_FAILURE)

    ctx = ValidationContext(otel_mode=otel, schema_version=ver, key_bytes=key_bytes)

    source = None if (file is None or file == "-") else file
    try:
        result = validate_stream(iter_events(source), ctx)
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
