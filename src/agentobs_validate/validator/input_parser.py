"""Input parsing and streaming for the AgentOBS event validator.

Spec reference: §3 (input formats), §4 (STDIN), §5 (exit code 2 = parse failure).

Memory model
------------
- JSONL files : O(1) — lines are yielded one at a time, never buffered in full.
- JSON arrays : O(n) — unavoidable; the full array must be loaded into memory.
- STDIN       : always buffered in full (stdin is not seekable so format
                detection requires a one-time read before iteration begins).

Format detection order
----------------------
1. ``.jsonl`` file extension → jsonl
2. ``.json``  file extension → json
3. Otherwise: open the file and peek at the first non-whitespace character.
   ``[`` → json array, ``{`` → jsonl.
4. STDIN (``source is None``): buffer stdin then sniff the buffer.
"""

from __future__ import annotations

import io
import json
import sys
from typing import IO, Any, Iterator, Literal


# Input hardening limits for untrusted streams.
MAX_EVENT_BYTES = 1_000_000
MAX_JSONL_LINE_BYTES = 1_000_000
MAX_STDIN_BYTES = 10_000_000
MAX_NESTING_DEPTH = 10


class ParseError(Exception):
    """Raised when input cannot be parsed into event dicts.

    Maps to exit code 2 (spec §5).

    Attributes
    ----------
    line_number:
        1-based line number where the error occurred, or ``None`` when the
        error does not relate to a specific line (e.g. top-level JSON failure).
    """

    def __init__(self, message: str, line_number: int | None = None) -> None:
        self.line_number = line_number
        super().__init__(message)


def _max_nesting_depth(value: Any) -> int:
    """Return maximum nesting depth for JSON-compatible containers.

    Scalars have depth 0. Dict/list add one level plus their deepest child.
    """
    if isinstance(value, dict):
        if not value:
            return 1
        return 1 + max(_max_nesting_depth(v) for v in value.values())
    if isinstance(value, list):
        if not value:
            return 1
        return 1 + max(_max_nesting_depth(v) for v in value)
    return 0


def _validate_event_limits(event: dict[str, Any], *, line_number: int | None = None) -> None:
    """Enforce event-level safety limits on size and nesting depth."""
    size_bytes = len(json.dumps(event, separators=(",", ":")).encode("utf-8"))
    if size_bytes > MAX_EVENT_BYTES:
        where = f" on line {line_number}" if line_number is not None else ""
        raise ParseError(
            f"Event{where} exceeds maximum size of {MAX_EVENT_BYTES} bytes",
            line_number=line_number,
        )

    depth = _max_nesting_depth(event)
    if depth > MAX_NESTING_DEPTH:
        where = f" on line {line_number}" if line_number is not None else ""
        raise ParseError(
            f"Event{where} exceeds maximum nesting depth of {MAX_NESTING_DEPTH}",
            line_number=line_number,
        )


# ── Format detection ──────────────────────────────────────────────────────────


def detect_format(path: str) -> Literal["json", "jsonl"]:
    """Return ``"json"`` or ``"jsonl"`` for the file at *path*.

    Resolution order:
    1. ``.jsonl`` extension (case-insensitive) → ``"jsonl"``
    2. ``.json``  extension (case-insensitive) → ``"json"``
    3. Otherwise open the file and sniff the first non-whitespace character.

    Raises
    ------
    ParseError
        If the format cannot be determined (empty file, unexpected leading
        character, or the file cannot be opened).
    """
    lower = path.lower()
    if lower.endswith(".jsonl"):
        return "jsonl"
    if lower.endswith(".json"):
        return "json"
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return _sniff_stream(fh)
    except OSError as exc:
        raise ParseError(f"Cannot open file for format detection: {exc}") from exc


def _sniff_stream(stream: IO[str]) -> Literal["json", "jsonl"]:
    """Peek at *stream* and return its format.

    Reads up to 1 024 characters searching for the first non-whitespace byte.
    ``[`` → ``"json"``, ``{`` → ``"jsonl"``.

    Raises :class:`ParseError` if the format cannot be identified.
    """
    for char in stream.read(1024):
        if char == "[":
            return "json"
        if char == "{":
            return "jsonl"
        if char not in " \t\r\n":
            raise ParseError(
                f"Cannot determine input format: unexpected leading character {char!r}"
            )
    raise ParseError(
        "Cannot determine input format: input is empty or contains only whitespace"
    )


# ── Format-specific iterators ─────────────────────────────────────────────────


def iter_events_jsonl(stream: IO[str]) -> Iterator[tuple[int, dict[str, Any]]]:
    """Yield ``(line_number, event_dict)`` pairs from a JSONL *stream*.

    Lines are processed one at a time — O(1) memory regardless of stream size.
    Blank and whitespace-only lines are silently skipped.

    Raises :class:`ParseError` on:
    - A line whose JSON is malformed.
    - A line whose decoded value is not a JSON object (``dict``).
    """
    for line_number, raw_line in enumerate(stream, start=1):
        if len(raw_line.encode("utf-8")) > MAX_JSONL_LINE_BYTES:
            raise ParseError(
                f"Line {line_number} exceeds maximum size of {MAX_JSONL_LINE_BYTES} bytes",
                line_number=line_number,
            )
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ParseError(
                f"Invalid JSON on line {line_number}: {exc.msg}",
                line_number=line_number,
            ) from exc
        if not isinstance(event, dict):
            raise ParseError(
                f"Line {line_number}: expected a JSON object, "
                f"got {type(event).__name__}",
                line_number=line_number,
            )
        _validate_event_limits(event, line_number=line_number)
        yield line_number, event


def iter_events_json(stream: IO[str]) -> Iterator[tuple[int, dict[str, Any]]]:
    """Yield ``(index, event_dict)`` pairs from a JSON array *stream*.

    The entire array is loaded into memory (O(n)), which is unavoidable for
    well-formed JSON arrays since the format requires the full document.

    Raises :class:`ParseError` on:
    - Invalid JSON.
    - A top-level value that is not a JSON array.
    - An array element that is not a JSON object.
    """
    try:
        data = json.load(stream)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid JSON: {exc.msg}") from exc
    if not isinstance(data, list):
        raise ParseError(
            f"Expected a JSON array at the top level, got {type(data).__name__}"
        )
    for index, event in enumerate(data, start=1):
        if not isinstance(event, dict):
            raise ParseError(
                f"Event at index {index}: expected a JSON object, "
                f"got {type(event).__name__}",
                line_number=index,
            )
        _validate_event_limits(event, line_number=index)
        yield index, event


# ── Unified entry point ───────────────────────────────────────────────────────


def iter_events(source: str | None) -> Iterator[tuple[int, dict[str, Any]]]:
    """Unified entry point: open *source*, detect format, and yield events.

    Parameters
    ----------
    source:
        Path to an input file, or ``None`` to read from ``sys.stdin``.

    Yields
    ------
    (position, event_dict):
        *position* is the 1-based line number for JSONL, or the 1-based
        array index for JSON arrays.

    Raises
    ------
    ParseError
        On any parse failure.  Callers map this to exit code 2 (spec §5).
    """
    if source is None:
        # stdin is not seekable — buffer in full, then wrap in StringIO so
        # format detection and iteration both start from position 0.
        content = sys.stdin.read()
        if len(content.encode("utf-8")) > MAX_STDIN_BYTES:
            raise ParseError(
                f"STDIN exceeds maximum size of {MAX_STDIN_BYTES} bytes"
            )
        buf = io.StringIO(content)
        fmt = _sniff_stream(buf)
        buf.seek(0)
        if fmt == "jsonl":
            yield from iter_events_jsonl(buf)
        else:
            yield from iter_events_json(buf)
    else:
        fmt = detect_format(source)  # raises ParseError on failure
        try:
            with open(source, "r", encoding="utf-8") as fh:
                if fmt == "jsonl":
                    yield from iter_events_jsonl(fh)
                else:
                    yield from iter_events_json(fh)
        except OSError as exc:
            raise ParseError(f"Cannot open file: {exc}") from exc
