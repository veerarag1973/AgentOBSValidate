"""Tests for the Output Formatters (Phase 5).

Covers:
- formatters.py: format_human() and format_json()
- Spec §10 (human), §11 (JSON), §12 (error objects)
"""

from __future__ import annotations

import json

import pytest

from agentobs_validate.errors.codes import (
    INVALID_NAMESPACE,
    INVALID_SIGNATURE,
    INVALID_ULID,
    MISSING_EVENT_ID,
    MISSING_TIMESTAMP,
)
from agentobs_validate.errors.models import ValidationError
from agentobs_validate.validator.formatters import format_human, format_json
from agentobs_validate.validator.results import EventResult, StreamResult

# ── Reusable fixtures ──────────────────────────────────────────────────────────

ERR_ULID = ValidationError(
    code=INVALID_ULID, field="event_id", message="bad ulid", value="bad"
)
ERR_MISSING = ValidationError(
    code=MISSING_EVENT_ID, field="event_id", message="required", value=None
)
ERR_TIMESTAMP = ValidationError(
    code=MISSING_TIMESTAMP, field="timestamp", message="required", value=None
)
ERR_SIG = ValidationError(
    code=INVALID_SIGNATURE, field="signature", message="bad sig", value="x"
)
ERR_NS = ValidationError(
    code=INVALID_NAMESPACE, field="event_type", message="bad ns", value="noDots"
)

PASS_1 = EventResult(index=1, status="pass", errors=[])
PASS_2 = EventResult(index=2, status="pass", errors=[])
FAIL_3 = EventResult(index=3, status="fail", errors=[ERR_ULID])
FAIL_4 = EventResult(index=4, status="fail", errors=[ERR_MISSING, ERR_TIMESTAMP])

EMPTY_STREAM = StreamResult(events_checked=0, valid=0, invalid=0, events=[])
ALL_PASS = StreamResult(events_checked=2, valid=2, invalid=0, events=[PASS_1, PASS_2])
ALL_FAIL = StreamResult(events_checked=2, valid=0, invalid=2, events=[FAIL_3, FAIL_4])
MIXED = StreamResult(events_checked=4, valid=2, invalid=2, events=[PASS_1, PASS_2, FAIL_3, FAIL_4])


# ─────────────────────────────────────────────────────────────────────────────
# format_human
# ─────────────────────────────────────────────────────────────────────────────


class TestFormatHuman:
    """Tests for format_human(result) → str."""

    # ── Return type and structure ─────────────────────────────────────────────

    def test_returns_string(self):
        assert isinstance(format_human(EMPTY_STREAM), str)

    def test_empty_stream_has_summary(self):
        output = format_human(EMPTY_STREAM)
        assert "Summary" in output
        assert "------" in output

    def test_empty_stream_counts(self):
        output = format_human(EMPTY_STREAM)
        assert "events_checked: 0" in output
        assert "valid: 0" in output
        assert "invalid: 0" in output

    # ── Pass event lines ──────────────────────────────────────────────────────

    def test_pass_event_line_format(self):
        output = format_human(ALL_PASS)
        assert "✔ Event 1  valid" in output

    def test_pass_event_uses_tick_symbol(self):
        output = format_human(ALL_PASS)
        assert "✔" in output

    def test_pass_event_two_spaces_before_valid(self):
        output = format_human(ALL_PASS)
        # Must be two spaces between index and "valid"
        assert "✔ Event 1  valid" in output
        assert "✔ Event 2  valid" in output

    def test_pass_event_index_preserved(self):
        ev = EventResult(index=99, status="pass", errors=[])
        r = StreamResult(events_checked=1, valid=1, invalid=0, events=[ev])
        assert "✔ Event 99  valid" in format_human(r)

    # ── Fail event lines ──────────────────────────────────────────────────────

    def test_fail_event_uses_cross_symbol(self):
        output = format_human(ALL_FAIL)
        assert "✖" in output

    def test_fail_event_line_format_single_code(self):
        output = format_human(ALL_FAIL)
        assert f"✖ Event 3  {INVALID_ULID}" in output

    def test_fail_event_line_two_spaces_before_codes(self):
        output = format_human(ALL_FAIL)
        assert "✖ Event 3  " in output

    def test_fail_event_multiple_codes_space_separated(self):
        output = format_human(ALL_FAIL)
        # FAIL_4 has two errors: MISSING_EVENT_ID and MISSING_TIMESTAMP
        assert f"✖ Event 4  {MISSING_EVENT_ID} {MISSING_TIMESTAMP}" in output

    def test_fail_event_index_preserved(self):
        ev = EventResult(index=77, status="fail", errors=[ERR_ULID])
        r = StreamResult(events_checked=1, valid=0, invalid=1, events=[ev])
        assert "✖ Event 77  " in format_human(r)

    def test_fail_event_no_valid_label(self):
        output = format_human(ALL_FAIL)
        # Fail lines must not include "valid"
        lines = output.splitlines()
        event_lines = [l for l in lines if l.startswith("✖")]
        for line in event_lines:
            assert "valid" not in line

    # ── Mixed output ──────────────────────────────────────────────────────────

    def test_mixed_stream_has_both_symbols(self):
        output = format_human(MIXED)
        assert "✔" in output
        assert "✖" in output

    def test_mixed_stream_event_order(self):
        output = format_human(MIXED)
        pos_pass1 = output.index("✔ Event 1")
        pos_pass2 = output.index("✔ Event 2")
        pos_fail3 = output.index("✖ Event 3")
        pos_fail4 = output.index("✖ Event 4")
        assert pos_pass1 < pos_pass2 < pos_fail3 < pos_fail4

    # ── Summary block ─────────────────────────────────────────────────────────

    def test_summary_header_present(self):
        output = format_human(MIXED)
        assert "Summary" in output

    def test_summary_separator_present(self):
        output = format_human(MIXED)
        assert "------" in output

    def test_summary_events_checked(self):
        output = format_human(MIXED)
        assert "events_checked: 4" in output

    def test_summary_valid_count(self):
        output = format_human(MIXED)
        assert "valid: 2" in output

    def test_summary_invalid_count(self):
        output = format_human(MIXED)
        assert "invalid: 2" in output

    def test_blank_line_before_summary(self):
        output = format_human(MIXED)
        lines = output.splitlines()
        summary_idx = lines.index("Summary")
        # Line before Summary must be blank
        assert lines[summary_idx - 1] == ""

    def test_summary_comes_after_events(self):
        output = format_human(MIXED)
        last_event_pos = max(output.rfind("✔"), output.rfind("✖"))
        summary_pos = output.index("Summary")
        assert summary_pos > last_event_pos

    def test_all_pass_summary_correct(self):
        output = format_human(ALL_PASS)
        assert "events_checked: 2" in output
        assert "valid: 2" in output
        assert "invalid: 0" in output

    def test_all_fail_summary_correct(self):
        output = format_human(ALL_FAIL)
        assert "events_checked: 2" in output
        assert "valid: 0" in output
        assert "invalid: 2" in output

    # ── Snapshot: spec §10 example ────────────────────────────────────────────

    def test_spec_example_snapshot(self):
        """Exact match against the spec §10 example layout."""
        err_ulid = ValidationError(
            code=INVALID_ULID, field="event_id", message="m1", value="x"
        )
        err_ns = ValidationError(
            code=INVALID_NAMESPACE, field="event_type", message="m2", value="y"
        )
        result = StreamResult(
            events_checked=4,
            valid=2,
            invalid=2,
            events=[
                EventResult(index=1, status="pass", errors=[]),
                EventResult(index=2, status="pass", errors=[]),
                EventResult(index=3, status="fail", errors=[err_ulid]),
                EventResult(index=4, status="fail", errors=[err_ns]),
            ],
        )
        output = format_human(result)
        assert "✔ Event 1  valid" in output
        assert "✔ Event 2  valid" in output
        assert f"✖ Event 3  {INVALID_ULID}" in output
        assert f"✖ Event 4  {INVALID_NAMESPACE}" in output
        assert "Summary" in output
        assert "------" in output
        assert "events_checked: 4" in output
        assert "valid: 2" in output
        assert "invalid: 2" in output


# ─────────────────────────────────────────────────────────────────────────────
# format_json
# ─────────────────────────────────────────────────────────────────────────────


class TestFormatJson:
    """Tests for format_json(result) → str."""

    # ── Return type and parsability ───────────────────────────────────────────

    def test_returns_string(self):
        assert isinstance(format_json(EMPTY_STREAM), str)

    def test_output_is_valid_json(self):
        json.loads(format_json(MIXED))  # must not raise

    def test_empty_stream_is_valid_json(self):
        json.loads(format_json(EMPTY_STREAM))

    # ── Top-level structure ───────────────────────────────────────────────────

    def test_top_level_keys(self):
        data = json.loads(format_json(MIXED))
        assert set(data.keys()) == {"summary", "events"}

    def test_summary_key_present(self):
        data = json.loads(format_json(EMPTY_STREAM))
        assert "summary" in data

    def test_events_key_present(self):
        data = json.loads(format_json(EMPTY_STREAM))
        assert "events" in data

    def test_events_is_list(self):
        data = json.loads(format_json(MIXED))
        assert isinstance(data["events"], list)

    # ── Summary sub-object ────────────────────────────────────────────────────

    def test_summary_has_events_checked(self):
        data = json.loads(format_json(MIXED))
        assert data["summary"]["events_checked"] == 4

    def test_summary_has_valid(self):
        data = json.loads(format_json(MIXED))
        assert data["summary"]["valid"] == 2

    def test_summary_has_invalid(self):
        data = json.loads(format_json(MIXED))
        assert data["summary"]["invalid"] == 2

    def test_summary_empty_stream(self):
        data = json.loads(format_json(EMPTY_STREAM))
        assert data["summary"]["events_checked"] == 0
        assert data["summary"]["valid"] == 0
        assert data["summary"]["invalid"] == 0
        assert data["summary"]["schema_version"] == "0.1"

    def test_summary_all_pass(self):
        data = json.loads(format_json(ALL_PASS))
        assert data["summary"]["valid"] == 2
        assert data["summary"]["invalid"] == 0

    def test_summary_all_fail(self):
        data = json.loads(format_json(ALL_FAIL))
        assert data["summary"]["valid"] == 0
        assert data["summary"]["invalid"] == 2

    # ── Event entries ─────────────────────────────────────────────────────────

    def test_events_count_matches(self):
        data = json.loads(format_json(MIXED))
        assert len(data["events"]) == 4

    def test_empty_stream_events_is_empty_list(self):
        data = json.loads(format_json(EMPTY_STREAM))
        assert data["events"] == []

    def test_event_has_index(self):
        data = json.loads(format_json(ALL_PASS))
        assert data["events"][0]["index"] == 1

    def test_event_has_status(self):
        data = json.loads(format_json(ALL_PASS))
        assert data["events"][0]["status"] == "pass"

    def test_event_index_values(self):
        data = json.loads(format_json(MIXED))
        indices = [e["index"] for e in data["events"]]
        assert indices == [1, 2, 3, 4]

    # ── Pass events omit errors key (spec §11) ────────────────────────────────

    def test_pass_event_has_no_errors_key(self):
        data = json.loads(format_json(ALL_PASS))
        for event in data["events"]:
            assert "errors" not in event

    def test_pass_event_in_mixed_stream_has_no_errors_key(self):
        data = json.loads(format_json(MIXED))
        pass_events = [e for e in data["events"] if e["status"] == "pass"]
        for event in pass_events:
            assert "errors" not in event

    def test_pass_event_only_has_index_and_status(self):
        data = json.loads(format_json(ALL_PASS))
        ev = data["events"][0]
        assert set(ev.keys()) == {"index", "status"}

    # ── Fail events include errors key (spec §11) ─────────────────────────────

    def test_fail_event_has_errors_key(self):
        data = json.loads(format_json(ALL_FAIL))
        fail_events = [e for e in data["events"] if e["status"] == "fail"]
        for event in fail_events:
            assert "errors" in event

    def test_fail_event_errors_is_list(self):
        data = json.loads(format_json(ALL_FAIL))
        assert isinstance(data["events"][0]["errors"], list)

    def test_fail_event_errors_count(self):
        data = json.loads(format_json(ALL_FAIL))
        # FAIL_3 has 1 error, FAIL_4 has 2
        assert len(data["events"][0]["errors"]) == 1
        assert len(data["events"][1]["errors"]) == 2

    # ── Error objects per spec §12 ────────────────────────────────────────────

    def test_error_has_code(self):
        data = json.loads(format_json(ALL_FAIL))
        err = data["events"][0]["errors"][0]
        assert "code" in err
        assert err["code"] == INVALID_ULID

    def test_error_has_field(self):
        data = json.loads(format_json(ALL_FAIL))
        err = data["events"][0]["errors"][0]
        assert "field" in err
        assert err["field"] == "event_id"

    def test_error_has_message(self):
        data = json.loads(format_json(ALL_FAIL))
        err = data["events"][0]["errors"][0]
        assert "message" in err

    def test_error_has_value(self):
        data = json.loads(format_json(ALL_FAIL))
        err = data["events"][0]["errors"][0]
        assert "value" in err

    def test_error_value_none_serialised(self):
        ev = EventResult(index=1, status="fail", errors=[ERR_MISSING])
        r = StreamResult(events_checked=1, valid=0, invalid=1, events=[ev])
        data = json.loads(format_json(r))
        err = data["events"][0]["errors"][0]
        assert err["value"] is None

    def test_error_value_string_preserved(self):
        data = json.loads(format_json(ALL_FAIL))
        err = data["events"][0]["errors"][0]
        assert err["value"] == "bad"

    # ── Indentation ───────────────────────────────────────────────────────────

    def test_output_is_indented(self):
        output = format_json(MIXED)
        # indent=2 means lines start with spaces
        assert "  " in output

    def test_output_has_newlines(self):
        output = format_json(MIXED)
        assert "\n" in output

    # ── Spec §11 snapshot ─────────────────────────────────────────────────────

    def test_json_spec_snapshot(self):
        """Validate against the exact structure shown in spec §11."""
        err = ValidationError(
            code=INVALID_ULID, field="event_id", message="ulid msg", value=None
        )
        result = StreamResult(
            events_checked=3,
            valid=2,
            invalid=1,
            events=[
                EventResult(index=1, status="pass", errors=[]),
                EventResult(index=2, status="pass", errors=[]),
                EventResult(index=3, status="fail", errors=[err]),
            ],
        )
        data = json.loads(format_json(result))
        assert data["summary"]["events_checked"] == 3
        assert data["summary"]["valid"] == 2
        assert data["summary"]["invalid"] == 1
        assert data["events"][0] == {"index": 1, "status": "pass"}
        assert data["events"][1] == {"index": 2, "status": "pass"}
        assert data["events"][2]["index"] == 3
        assert data["events"][2]["status"] == "fail"
        assert len(data["events"][2]["errors"]) == 1
        assert data["events"][2]["errors"][0]["code"] == INVALID_ULID
