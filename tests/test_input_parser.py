"""Tests for validator.input_parser.

Coverage targets (100%):
- ParseError construction and attributes
- detect_format: extension-based routing, file sniffing, error cases
- iter_events_jsonl: valid, blank lines, malformed, non-object, O(1) streaming
- iter_events_json: valid, empty array, invalid JSON, wrong top-level type,
  non-object item
- iter_events: file JSONL, file JSON, no-extension sniff, STDIN JSONL,
  STDIN JSON, STDIN empty, non-existent file, error propagation
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from agentobs_validate.validator.input_parser import (
    ParseError,
    detect_format,
    iter_events,
    iter_events_json,
    iter_events_jsonl,
)

# ── Shared fixtures / helpers ─────────────────────────────────────────────────

# Spec §17 example values used throughout
_EV1: dict[str, Any] = {
    "event_id": "01HZY7M4YQZB3D0V4K6Z5R9F7A",
    "timestamp": "2026-02-20T10:45:21.123Z",
    "event_type": "agent.tool.called",
    "source": "langchain@0.2.11",
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "00f067aa0ba902b7",
}

_EV2: dict[str, Any] = {
    "event_id": "01HZY7M4YQZB3D0V4K6Z5R9F7B",
    "timestamp": "2026-02-20T10:45:22.000Z",
    "event_type": "agent.llm.request",
    "source": "langchain@0.2.11",
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "00f067aa0ba902b8",
}


def _jsonl(*events: dict[str, Any]) -> str:
    """Serialise dicts as a JSONL string."""
    return "\n".join(json.dumps(e) for e in events) + "\n"


def _json_array(*events: dict[str, Any]) -> str:
    """Serialise dicts as a JSON array string."""
    return json.dumps(list(events), indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# ParseError
# ─────────────────────────────────────────────────────────────────────────────


class TestParseError:
    def test_is_exception_subclass(self) -> None:
        assert issubclass(ParseError, Exception)

    def test_message_stored(self) -> None:
        err = ParseError("bad input")
        assert str(err) == "bad input"

    def test_line_number_defaults_to_none(self) -> None:
        err = ParseError("bad input")
        assert err.line_number is None

    def test_line_number_can_be_set(self) -> None:
        err = ParseError("bad input", line_number=42)
        assert err.line_number == 42

    def test_raiseable(self) -> None:
        with pytest.raises(ParseError, match="bad input"):
            raise ParseError("bad input")


# ─────────────────────────────────────────────────────────────────────────────
# detect_format
# ─────────────────────────────────────────────────────────────────────────────


class TestDetectFormat:
    """Tests for detect_format() — all file-based."""

    # ── Extension routing ─────────────────────────────────────────────────────

    def test_jsonl_extension_lowercase(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        p.write_text(_jsonl(_EV1))
        assert detect_format(str(p)) == "jsonl"

    def test_jsonl_extension_uppercase(self, tmp_path: Path) -> None:
        p = tmp_path / "events.JSONL"
        p.write_text(_jsonl(_EV1))
        assert detect_format(str(p)) == "jsonl"

    def test_json_extension_lowercase(self, tmp_path: Path) -> None:
        p = tmp_path / "events.json"
        p.write_text(_json_array(_EV1))
        assert detect_format(str(p)) == "json"

    def test_json_extension_uppercase(self, tmp_path: Path) -> None:
        p = tmp_path / "events.JSON"
        p.write_text(_json_array(_EV1))
        assert detect_format(str(p)) == "json"

    def test_jsonl_extension_never_reads_file(self, tmp_path: Path) -> None:
        """Extension-detected .jsonl must not attempt to open the file."""
        p = tmp_path / "empty.jsonl"
        # File does not exist — extension check must short-circuit before open
        assert detect_format(str(p)) == "jsonl"

    def test_json_extension_never_reads_file(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.json"
        assert detect_format(str(p)) == "json"

    # ── Content sniffing — no extension ──────────────────────────────────────

    def test_sniff_json_array(self, tmp_path: Path) -> None:
        p = tmp_path / "events"
        p.write_text(_json_array(_EV1))
        assert detect_format(str(p)) == "json"

    def test_sniff_jsonl(self, tmp_path: Path) -> None:
        p = tmp_path / "events"
        p.write_text(_jsonl(_EV1))
        assert detect_format(str(p)) == "jsonl"

    def test_sniff_json_with_leading_whitespace(self, tmp_path: Path) -> None:
        p = tmp_path / "events"
        p.write_text("  \n\t[" + _json_array(_EV1)[1:])
        assert detect_format(str(p)) == "json"

    def test_sniff_jsonl_with_leading_whitespace(self, tmp_path: Path) -> None:
        p = tmp_path / "events"
        p.write_text("  \n" + _jsonl(_EV1))
        assert detect_format(str(p)) == "jsonl"

    # ── Error paths ───────────────────────────────────────────────────────────

    def test_empty_file_raises_parse_error(self, tmp_path: Path) -> None:
        p = tmp_path / "empty"
        p.write_text("")
        with pytest.raises(ParseError, match="empty or contains only whitespace"):
            detect_format(str(p))

    def test_whitespace_only_file_raises_parse_error(self, tmp_path: Path) -> None:
        p = tmp_path / "ws"
        p.write_text("   \n\t\r\n  ")
        with pytest.raises(ParseError, match="empty or contains only whitespace"):
            detect_format(str(p))

    def test_unexpected_leading_char_raises_parse_error(self, tmp_path: Path) -> None:
        p = tmp_path / "badfile"
        p.write_text("# this is a comment\n{}")
        with pytest.raises(ParseError, match="unexpected leading character"):
            detect_format(str(p))

    def test_nonexistent_file_no_extension_raises_parse_error(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "missing_file"
        with pytest.raises(ParseError, match="Cannot open file"):
            detect_format(str(p))


# ─────────────────────────────────────────────────────────────────────────────
# iter_events_jsonl
# ─────────────────────────────────────────────────────────────────────────────


class TestIterEventsJsonl:
    """Tests for iter_events_jsonl() — uses StringIO for O(1) isolation."""

    def test_single_event(self) -> None:
        stream = io.StringIO(_jsonl(_EV1))
        results = list(iter_events_jsonl(stream))
        assert results == [(1, _EV1)]

    def test_two_events_correct_line_numbers(self) -> None:
        stream = io.StringIO(_jsonl(_EV1, _EV2))
        results = list(iter_events_jsonl(stream))
        assert results == [(1, _EV1), (2, _EV2)]

    def test_empty_stream_yields_nothing(self) -> None:
        results = list(iter_events_jsonl(io.StringIO("")))
        assert results == []

    def test_blank_lines_skipped(self) -> None:
        content = "\n" + json.dumps(_EV1) + "\n\n" + json.dumps(_EV2) + "\n"
        results = list(iter_events_jsonl(io.StringIO(content)))
        assert len(results) == 2
        assert results[0][1] == _EV1
        assert results[1][1] == _EV2

    def test_blank_lines_do_not_shift_line_numbers(self) -> None:
        """Line numbers should reflect the real position in the stream."""
        content = "\n" + json.dumps(_EV1) + "\n"  # EV1 is on line 2
        results = list(iter_events_jsonl(io.StringIO(content)))
        assert results[0][0] == 2

    def test_whitespace_only_lines_skipped(self) -> None:
        content = "   \n" + json.dumps(_EV1) + "\n\t\n"
        results = list(iter_events_jsonl(io.StringIO(content)))
        assert len(results) == 1

    def test_malformed_json_raises_parse_error(self) -> None:
        stream = io.StringIO("not-json\n")
        with pytest.raises(ParseError) as exc_info:
            list(iter_events_jsonl(stream))
        assert exc_info.value.line_number == 1
        assert "line 1" in str(exc_info.value)

    def test_malformed_json_mid_stream_carries_line_number(self) -> None:
        content = json.dumps(_EV1) + "\nnot-json\n" + json.dumps(_EV2) + "\n"
        stream = io.StringIO(content)
        with pytest.raises(ParseError) as exc_info:
            list(iter_events_jsonl(stream))
        assert exc_info.value.line_number == 2

    def test_non_object_array_raises_parse_error(self) -> None:
        stream = io.StringIO("[1, 2, 3]\n")
        with pytest.raises(ParseError) as exc_info:
            list(iter_events_jsonl(stream))
        assert exc_info.value.line_number == 1
        assert "list" in str(exc_info.value)

    def test_non_object_string_raises_parse_error(self) -> None:
        stream = io.StringIO('"hello"\n')
        with pytest.raises(ParseError) as exc_info:
            list(iter_events_jsonl(stream))
        assert "str" in str(exc_info.value)

    def test_non_object_integer_raises_parse_error(self) -> None:
        stream = io.StringIO("42\n")
        with pytest.raises(ParseError) as exc_info:
            list(iter_events_jsonl(stream))
        assert exc_info.value.line_number == 1

    def test_trailing_newline_does_not_add_event(self) -> None:
        stream = io.StringIO(json.dumps(_EV1) + "\n\n\n")
        results = list(iter_events_jsonl(stream))
        assert len(results) == 1

    def test_return_values_are_dicts(self) -> None:
        stream = io.StringIO(_jsonl(_EV1))
        _, event = next(iter(iter_events_jsonl(stream)))
        assert isinstance(event, dict)

    def test_streaming_yields_one_at_a_time(self) -> None:
        """Verify the iterator is lazy — yields one event, then the next."""
        stream = io.StringIO(_jsonl(_EV1, _EV2))
        gen = iter_events_jsonl(stream)
        first = next(gen)
        assert first == (1, _EV1)
        second = next(gen)
        assert second == (2, _EV2)
        with pytest.raises(StopIteration):
            next(gen)


# ─────────────────────────────────────────────────────────────────────────────
# iter_events_json
# ─────────────────────────────────────────────────────────────────────────────


class TestIterEventsJson:
    """Tests for iter_events_json() — uses StringIO."""

    def test_single_event(self) -> None:
        stream = io.StringIO(_json_array(_EV1))
        results = list(iter_events_json(stream))
        assert results == [(1, _EV1)]

    def test_two_events_correct_indices(self) -> None:
        stream = io.StringIO(_json_array(_EV1, _EV2))
        results = list(iter_events_json(stream))
        assert results == [(1, _EV1), (2, _EV2)]

    def test_empty_array_yields_nothing(self) -> None:
        results = list(iter_events_json(io.StringIO("[]")))
        assert results == []

    def test_index_starts_at_one(self) -> None:
        stream = io.StringIO(_json_array(_EV1, _EV2))
        positions = [pos for pos, _ in iter_events_json(stream)]
        assert positions == [1, 2]

    def test_invalid_json_raises_parse_error(self) -> None:
        with pytest.raises(ParseError, match="Invalid JSON"):
            list(iter_events_json(io.StringIO("not json")))

    def test_top_level_object_raises_parse_error(self) -> None:
        with pytest.raises(ParseError, match="Expected a JSON array"):
            list(iter_events_json(io.StringIO(json.dumps(_EV1))))

    def test_top_level_string_raises_parse_error(self) -> None:
        with pytest.raises(ParseError, match="Expected a JSON array"):
            list(iter_events_json(io.StringIO('"hello"')))

    def test_top_level_number_raises_parse_error(self) -> None:
        with pytest.raises(ParseError, match="Expected a JSON array"):
            list(iter_events_json(io.StringIO("42")))

    def test_non_object_item_raises_parse_error(self) -> None:
        mixed = json.dumps([_EV1, "not-an-object", _EV2])
        with pytest.raises(ParseError) as exc_info:
            list(iter_events_json(io.StringIO(mixed)))
        assert "index 2" in str(exc_info.value)
        assert exc_info.value.line_number == 2

    def test_non_object_item_at_index_one_raises_parse_error(self) -> None:
        bad = json.dumps([42, _EV1])
        with pytest.raises(ParseError) as exc_info:
            list(iter_events_json(io.StringIO(bad)))
        assert exc_info.value.line_number == 1

    def test_returns_dicts(self) -> None:
        stream = io.StringIO(_json_array(_EV1))
        _, event = next(iter(iter_events_json(stream)))
        assert isinstance(event, dict)

    def test_event_content_preserved(self) -> None:
        stream = io.StringIO(_json_array(_EV1))
        _, event = next(iter(iter_events_json(stream)))
        assert event == _EV1


# ─────────────────────────────────────────────────────────────────────────────
# iter_events — file paths
# ─────────────────────────────────────────────────────────────────────────────


class TestIterEventsFiles:
    """Tests for iter_events() with real file paths (uses tmp_path)."""

    def test_jsonl_file_by_extension(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        p.write_text(_jsonl(_EV1, _EV2))
        results = list(iter_events(str(p)))
        assert results == [(1, _EV1), (2, _EV2)]

    def test_json_file_by_extension(self, tmp_path: Path) -> None:
        p = tmp_path / "events.json"
        p.write_text(_json_array(_EV1, _EV2))
        results = list(iter_events(str(p)))
        assert results == [(1, _EV1), (2, _EV2)]

    def test_no_extension_jsonl_detected(self, tmp_path: Path) -> None:
        p = tmp_path / "events"
        p.write_text(_jsonl(_EV1))
        results = list(iter_events(str(p)))
        assert results == [(1, _EV1)]

    def test_no_extension_json_detected(self, tmp_path: Path) -> None:
        p = tmp_path / "events"
        p.write_text(_json_array(_EV1))
        results = list(iter_events(str(p)))
        assert results == [(1, _EV1)]

    def test_empty_jsonl_yields_nothing(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.jsonl"
        p.write_text("")
        results = list(iter_events(str(p)))
        assert results == []

    def test_empty_json_array_yields_nothing(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.json"
        p.write_text("[]")
        results = list(iter_events(str(p)))
        assert results == []

    def test_nonexistent_jsonl_raises_parse_error(self, tmp_path: Path) -> None:
        p = tmp_path / "missing.jsonl"
        with pytest.raises(ParseError, match="Cannot open file"):
            list(iter_events(str(p)))

    def test_nonexistent_json_raises_parse_error(self, tmp_path: Path) -> None:
        p = tmp_path / "missing.json"
        with pytest.raises(ParseError, match="Cannot open file"):
            list(iter_events(str(p)))

    def test_nonexistent_no_extension_raises_parse_error(
        self, tmp_path: Path
    ) -> None:
        """No-extension non-existent file: detect_format raises first."""
        p = tmp_path / "missing"
        with pytest.raises(ParseError):
            list(iter_events(str(p)))

    def test_malformed_line_in_jsonl_file_raises_parse_error(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "bad.jsonl"
        p.write_text(json.dumps(_EV1) + "\nnot-json\n")
        with pytest.raises(ParseError) as exc_info:
            list(iter_events(str(p)))
        assert exc_info.value.line_number == 2

    def test_invalid_json_array_file_raises_parse_error(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "bad.json"
        p.write_text("[invalid json]")
        with pytest.raises(ParseError, match="Invalid JSON"):
            list(iter_events(str(p)))

    def test_positions_are_line_numbers_for_jsonl(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        p.write_text("\n" + json.dumps(_EV1) + "\n" + json.dumps(_EV2) + "\n")
        positions = [pos for pos, _ in iter_events(str(p))]
        # EV1 is on line 2, EV2 is on line 3
        assert positions == [2, 3]

    def test_positions_are_one_based_indices_for_json(self, tmp_path: Path) -> None:
        p = tmp_path / "events.json"
        p.write_text(_json_array(_EV1, _EV2))
        positions = [pos for pos, _ in iter_events(str(p))]
        assert positions == [1, 2]

    def test_parse_error_propagates_from_jsonl(self, tmp_path: Path) -> None:
        """ParseError from iter_events_jsonl must propagate unchanged."""
        p = tmp_path / "bad.jsonl"
        p.write_text("[1,2,3]\n")
        with pytest.raises(ParseError) as exc_info:
            list(iter_events(str(p)))
        assert exc_info.value.line_number == 1

    def test_returns_iterator(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        p.write_text(_jsonl(_EV1))
        result = iter_events(str(p))
        import collections.abc
        assert isinstance(result, collections.abc.Iterator)


# ─────────────────────────────────────────────────────────────────────────────
# iter_events — STDIN
# ─────────────────────────────────────────────────────────────────────────────


class TestIterEventsStdin:
    """Tests for iter_events(None) — monkeypatches sys.stdin."""

    def test_stdin_jsonl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(_jsonl(_EV1, _EV2)))
        results = list(iter_events(None))
        assert results == [(1, _EV1), (2, _EV2)]

    def test_stdin_json_array(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(_json_array(_EV1, _EV2)))
        results = list(iter_events(None))
        assert results == [(1, _EV1), (2, _EV2)]

    def test_stdin_empty_raises_parse_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))
        with pytest.raises(ParseError, match="empty or contains only whitespace"):
            list(iter_events(None))

    def test_stdin_whitespace_only_raises_parse_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO("  \n\t\n"))
        with pytest.raises(ParseError, match="empty or contains only whitespace"):
            list(iter_events(None))

    def test_stdin_malformed_jsonl_raises_parse_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Start with '{' so format detection succeeds (→ jsonl), then the
        # line itself is invalid JSON, raising ParseError with line_number=1.
        monkeypatch.setattr(sys, "stdin", io.StringIO("{bad json}\n"))
        with pytest.raises(ParseError) as exc_info:
            list(iter_events(None))
        assert exc_info.value.line_number == 1

    def test_stdin_invalid_json_array_raises_parse_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO("[bad json]"))
        with pytest.raises(ParseError, match="Invalid JSON"):
            list(iter_events(None))

    def test_stdin_single_jsonl_event(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_EV1) + "\n"))
        results = list(iter_events(None))
        assert len(results) == 1
        assert results[0] == (1, _EV1)

    def test_stdin_empty_json_array(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO("[]"))
        results = list(iter_events(None))
        assert results == []

    def test_stdin_unexpected_leading_char_raises_parse_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO("# comment\n{}"))
        with pytest.raises(ParseError, match="unexpected leading character"):
            list(iter_events(None))
