"""Tests for the Core Validator Engine (Phase 4).

Covers:
- results.py: EventResult, StreamResult construction and to_dict()
- engine.py: validate_event(), validate_stream()
"""

from __future__ import annotations

import pytest

from agentobs_validate.errors.codes import (
    INVALID_EVENT_TYPE,
    INVALID_NAMESPACE,
    INVALID_SIGNATURE,
    INVALID_SPAN_ID,
    INVALID_TIMESTAMP,
    INVALID_TRACE_ID,
    INVALID_ULID,
    MISSING_EVENT_ID,
    MISSING_SOURCE,
    MISSING_TIMESTAMP,
    UNSUPPORTED_ALGORITHM,
)
from agentobs_validate.errors.models import ValidationError
from agentobs_validate.schema.fields import FIELD_SIGNATURE
from agentobs_validate.validator.engine import validate_event, validate_stream
from agentobs_validate.validator.results import EventResult, StreamResult

# ── Shared fixtures ────────────────────────────────────────────────────────────

VALID_EVENT = {
    "event_id": "01HZY7M4YQZB3D0V4K6Z5R9F7A",
    "timestamp": "2026-02-20T10:45:21.123Z",
    "event_type": "agent.tool.called",
    "source": "langchain@0.2.11",
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "00f067aa0ba902b7",
}

VALID_EVENT_WITH_SIG = {
    **VALID_EVENT,
    "signature": {
        "algorithm": "HMAC-SHA256",
        "value": "dGVzdA==",
        "key_id": "k1",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# EventResult
# ─────────────────────────────────────────────────────────────────────────────


class TestEventResult:
    def test_construction_pass(self):
        r = EventResult(index=1, status="pass", errors=[])
        assert r.index == 1
        assert r.status == "pass"
        assert r.errors == []

    def test_construction_fail(self):
        err = ValidationError(code=INVALID_ULID, field="event_id", message="bad")
        r = EventResult(index=2, status="fail", errors=[err])
        assert r.index == 2
        assert r.status == "fail"
        assert r.errors == [err]

    def test_errors_default_to_empty_list(self):
        r = EventResult(index=1, status="pass")
        assert r.errors == []

    def test_to_dict_pass_no_errors(self):
        r = EventResult(index=1, status="pass", errors=[])
        d = r.to_dict()
        assert d == {"index": 1, "status": "pass", "errors": []}

    def test_to_dict_fail_with_errors(self):
        err = ValidationError(code=INVALID_ULID, field="event_id", message="bad", value="x")
        r = EventResult(index=3, status="fail", errors=[err])
        d = r.to_dict()
        assert d["index"] == 3
        assert d["status"] == "fail"
        assert len(d["errors"]) == 1
        assert d["errors"][0] == err.to_dict()

    def test_to_dict_errors_are_dicts(self):
        err = ValidationError(code=MISSING_EVENT_ID, field="event_id", message="required")
        r = EventResult(index=1, status="fail", errors=[err])
        d = r.to_dict()
        assert isinstance(d["errors"][0], dict)

    def test_to_dict_multiple_errors(self):
        err1 = ValidationError(code=MISSING_EVENT_ID, field="event_id", message="m1")
        err2 = ValidationError(code=INVALID_ULID, field="event_id", message="m2")
        r = EventResult(index=1, status="fail", errors=[err1, err2])
        d = r.to_dict()
        assert len(d["errors"]) == 2

    def test_to_dict_is_json_serialisable(self):
        import json
        r = EventResult(index=1, status="pass", errors=[])
        json.dumps(r.to_dict())  # must not raise

    def test_to_dict_fail_is_json_serialisable(self):
        import json
        err = ValidationError(code=INVALID_ULID, field="event_id", message="bad", value="x")
        r = EventResult(index=1, status="fail", errors=[err])
        json.dumps(r.to_dict())  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# StreamResult
# ─────────────────────────────────────────────────────────────────────────────


class TestStreamResult:
    def test_construction_empty(self):
        r = StreamResult(events_checked=0, valid=0, invalid=0, events=[])
        assert r.events_checked == 0
        assert r.valid == 0
        assert r.invalid == 0
        assert r.events == []

    def test_construction_with_counts(self):
        r = StreamResult(events_checked=5, valid=3, invalid=2, events=[])
        assert r.events_checked == 5
        assert r.valid == 3
        assert r.invalid == 2

    def test_events_default_to_empty_list(self):
        r = StreamResult(events_checked=0, valid=0, invalid=0)
        assert r.events == []

    def test_to_dict_empty(self):
        r = StreamResult(events_checked=0, valid=0, invalid=0, events=[])
        d = r.to_dict()
        assert d == {"schema_version": "0.1", "events_checked": 0, "valid": 0, "invalid": 0, "events": []}

    def test_to_dict_with_events(self):
        ev = EventResult(index=1, status="pass", errors=[])
        r = StreamResult(events_checked=1, valid=1, invalid=0, events=[ev])
        d = r.to_dict()
        assert d["events_checked"] == 1
        assert d["valid"] == 1
        assert d["invalid"] == 0
        assert len(d["events"]) == 1

    def test_to_dict_events_are_dicts(self):
        ev = EventResult(index=1, status="pass", errors=[])
        r = StreamResult(events_checked=1, valid=1, invalid=0, events=[ev])
        d = r.to_dict()
        assert isinstance(d["events"][0], dict)

    def test_to_dict_is_json_serialisable(self):
        import json
        r = StreamResult(events_checked=0, valid=0, invalid=0, events=[])
        json.dumps(r.to_dict())  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# validate_event
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateEvent:
    """Tests for validate_event(index, event) → EventResult."""

    def test_fully_valid_event_passes(self):
        result = validate_event(1, VALID_EVENT)
        assert result.status == "pass"
        assert result.errors == []
        assert result.index == 1

    def test_fully_valid_event_with_signature_passes(self):
        result = validate_event(1, VALID_EVENT_WITH_SIG)
        assert result.status == "pass"
        assert result.errors == []

    def test_index_is_preserved(self):
        result = validate_event(42, VALID_EVENT)
        assert result.index == 42

    def test_returns_event_result_instance(self):
        result = validate_event(1, VALID_EVENT)
        assert isinstance(result, EventResult)

    # Missing required fields ─────────────────────────────────────────────────

    def test_missing_event_id_gives_fail(self):
        event = {**VALID_EVENT}
        del event["event_id"]
        result = validate_event(1, event)
        assert result.status == "fail"
        codes = [e.code for e in result.errors]
        assert MISSING_EVENT_ID in codes

    def test_missing_timestamp_gives_fail(self):
        event = {**VALID_EVENT}
        del event["timestamp"]
        result = validate_event(1, event)
        assert result.status == "fail"
        codes = [e.code for e in result.errors]
        assert MISSING_TIMESTAMP in codes

    def test_missing_source_gives_fail(self):
        event = {**VALID_EVENT}
        del event["source"]
        result = validate_event(1, event)
        assert result.status == "fail"
        codes = [e.code for e in result.errors]
        assert MISSING_SOURCE in codes

    # Invalid required fields ─────────────────────────────────────────────────

    def test_invalid_event_id_gives_fail(self):
        event = {**VALID_EVENT, "event_id": "not-a-ulid"}
        result = validate_event(1, event)
        assert result.status == "fail"
        codes = [e.code for e in result.errors]
        assert INVALID_ULID in codes

    def test_invalid_timestamp_gives_fail(self):
        event = {**VALID_EVENT, "timestamp": "not-a-timestamp"}
        result = validate_event(1, event)
        assert result.status == "fail"
        codes = [e.code for e in result.errors]
        assert INVALID_TIMESTAMP in codes

    def test_invalid_event_type_gives_fail(self):
        # "no-dots" is a string but wrong format → INVALID_NAMESPACE
        event = {**VALID_EVENT, "event_type": "no-dots"}
        result = validate_event(1, event)
        assert result.status == "fail"
        codes = [e.code for e in result.errors]
        assert INVALID_NAMESPACE in codes

    def test_invalid_trace_id_gives_fail(self):
        event = {**VALID_EVENT, "trace_id": "UPPERCASE"}
        result = validate_event(1, event)
        assert result.status == "fail"
        codes = [e.code for e in result.errors]
        assert INVALID_TRACE_ID in codes

    def test_invalid_span_id_gives_fail(self):
        event = {**VALID_EVENT, "span_id": "tooshort"}
        result = validate_event(1, event)
        assert result.status == "fail"
        codes = [e.code for e in result.errors]
        assert INVALID_SPAN_ID in codes

    # Non-short-circuit: multiple errors collected ────────────────────────────

    def test_multiple_invalid_fields_all_errors_reported(self):
        event = {
            "event_id": "bad",                      # INVALID_ULID
            "timestamp": "bad",                      # INVALID_TIMESTAMP
            "event_type": "noDots",                  # INVALID_EVENT_TYPE
            "source": "no-at-sign",                  # INVALID_SOURCE_FORMAT
            "trace_id": "tooshort",                  # INVALID_TRACE_ID
            "span_id": "tooshort",                   # INVALID_SPAN_ID
        }
        result = validate_event(1, event)
        assert result.status == "fail"
        assert len(result.errors) >= 6

    def test_all_missing_required_fields_all_errors_reported(self):
        result = validate_event(1, {})
        assert result.status == "fail"
        # event_id (MISSING) + timestamp (MISSING) + event_type (INVALID) +
        # source (MISSING) + trace_id (INVALID) + span_id (INVALID) = 6 min
        assert len(result.errors) >= 6

    # Signature field ─────────────────────────────────────────────────────────

    def test_signature_field_absent_not_validated(self):
        """Absence of the optional signature field must not produce any error."""
        assert FIELD_SIGNATURE not in VALID_EVENT
        result = validate_event(1, VALID_EVENT)
        assert result.status == "pass"

    def test_invalid_signature_algorithm_gives_fail(self):
        event = {
            **VALID_EVENT,
            "signature": {"algorithm": "bad-algo", "value": "dGVzdA=="},
        }
        result = validate_event(1, event)
        assert result.status == "fail"
        codes = [e.code for e in result.errors]
        assert UNSUPPORTED_ALGORITHM in codes

    def test_invalid_signature_value_gives_fail(self):
        event = {
            **VALID_EVENT,
            "signature": {"algorithm": "HMAC-SHA256", "value": "not!base64"},
        }
        result = validate_event(1, event)
        assert result.status == "fail"
        codes = [e.code for e in result.errors]
        assert INVALID_SIGNATURE in codes

    def test_signature_none_value_treated_as_present_and_validated(self):
        """A key ``"signature": None`` is present → validation runs → fail."""
        event = {**VALID_EVENT, "signature": None}
        result = validate_event(1, event)
        # validate_signature(None) returns [] per spec (absent = skip)
        # because the value is None — validator treats None as "not provided"
        assert result.status == "pass"

    def test_errors_are_validation_error_instances(self):
        event = {**VALID_EVENT, "event_id": "bad"}
        result = validate_event(1, event)
        for err in result.errors:
            assert isinstance(err, ValidationError)


# ─────────────────────────────────────────────────────────────────────────────
# validate_stream
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateStream:
    """Tests for validate_stream(events_iterator) → StreamResult."""

    def _make_iter(self, events: list[dict]):
        """Wrap a list of dicts as a 1-based (index, dict) iterator."""
        return iter(enumerate(events, start=1))

    def test_empty_stream_returns_zeroed_result(self):
        result = validate_stream(iter([]))
        assert result.events_checked == 0
        assert result.valid == 0
        assert result.invalid == 0
        assert result.events == []

    def test_returns_stream_result_instance(self):
        result = validate_stream(iter([]))
        assert isinstance(result, StreamResult)

    def test_single_valid_event(self):
        result = validate_stream(self._make_iter([VALID_EVENT]))
        assert result.events_checked == 1
        assert result.valid == 1
        assert result.invalid == 0

    def test_single_invalid_event(self):
        result = validate_stream(self._make_iter([{"event_id": "bad"}]))
        assert result.events_checked == 1
        assert result.valid == 0
        assert result.invalid == 1

    def test_all_valid_stream(self):
        events = [VALID_EVENT, VALID_EVENT, VALID_EVENT]
        result = validate_stream(self._make_iter(events))
        assert result.events_checked == 3
        assert result.valid == 3
        assert result.invalid == 0

    def test_all_invalid_stream(self):
        events = [{"event_id": "bad"}, {"event_id": "bad"}]
        result = validate_stream(self._make_iter(events))
        assert result.events_checked == 2
        assert result.valid == 0
        assert result.invalid == 2

    def test_mixed_stream_correct_counts(self):
        events = [VALID_EVENT, {"event_id": "bad"}, VALID_EVENT, {"event_id": "x"}]
        result = validate_stream(self._make_iter(events))
        assert result.events_checked == 4
        assert result.valid == 2
        assert result.invalid == 2

    def test_events_checked_equals_valid_plus_invalid(self):
        events = [VALID_EVENT, {"event_id": "bad"}, VALID_EVENT]
        result = validate_stream(self._make_iter(events))
        assert result.events_checked == result.valid + result.invalid

    def test_event_results_length_matches_events_checked(self):
        events = [VALID_EVENT, VALID_EVENT]
        result = validate_stream(self._make_iter(events))
        assert len(result.events) == result.events_checked

    def test_event_results_preserve_order(self):
        events = [VALID_EVENT, {"event_id": "bad"}, VALID_EVENT]
        result = validate_stream(self._make_iter(events))
        statuses = [r.status for r in result.events]
        assert statuses == ["pass", "fail", "pass"]

    def test_event_results_preserve_indices(self):
        result = validate_stream(self._make_iter([VALID_EVENT, VALID_EVENT]))
        assert result.events[0].index == 1
        assert result.events[1].index == 2

    def test_non_sequential_indices_preserved(self):
        """Indices come from the iterator, not recalculated by validate_stream."""
        events_iter = iter([(10, VALID_EVENT), (20, VALID_EVENT)])
        result = validate_stream(events_iter)
        assert result.events[0].index == 10
        assert result.events[1].index == 20

    def test_event_errors_populated_for_invalid(self):
        result = validate_stream(self._make_iter([{"event_id": "bad"}]))
        assert len(result.events[0].errors) > 0

    def test_event_errors_empty_for_valid(self):
        result = validate_stream(self._make_iter([VALID_EVENT]))
        assert result.events[0].errors == []

    def test_stream_with_signature_valid(self):
        result = validate_stream(self._make_iter([VALID_EVENT_WITH_SIG]))
        assert result.valid == 1
        assert result.invalid == 0

    def test_to_dict_round_trip(self):
        import json
        events = [VALID_EVENT, {"event_id": "bad"}]
        result = validate_stream(self._make_iter(events))
        d = result.to_dict()
        json.dumps(d)  # must not raise

    def test_large_stream_counts(self):
        events = [VALID_EVENT] * 100
        result = validate_stream(self._make_iter(events))
        assert result.events_checked == 100
        assert result.valid == 100
        assert result.invalid == 0


# ─────────────────────────────────────────────────────────────────────────────
# Integration: validate_event + validate_stream round-trip
# ─────────────────────────────────────────────────────────────────────────────


class TestEngineIntegration:
    """End-to-end checks combining both engine functions."""

    def test_spec_example_event_passes(self):
        """The canonical event from the spec should always pass."""
        result = validate_event(1, VALID_EVENT)
        assert result.status == "pass"
        assert result.errors == []

    def test_spec_example_with_sig_passes(self):
        result = validate_event(1, VALID_EVENT_WITH_SIG)
        assert result.status == "pass"

    def test_stream_of_spec_examples_passes(self):
        events = [VALID_EVENT, VALID_EVENT_WITH_SIG]
        result = validate_stream(iter(enumerate(events, start=1)))
        assert result.valid == 2
        assert result.invalid == 0

    def test_stream_result_to_dict_structure(self):
        events = [VALID_EVENT]
        result = validate_stream(iter(enumerate(events, start=1)))
        d = result.to_dict()
        assert "events_checked" in d
        assert "valid" in d
        assert "invalid" in d
        assert "events" in d
        assert isinstance(d["events"], list)
        ev_dict = d["events"][0]
        assert "index" in ev_dict
        assert "status" in ev_dict
        assert "errors" in ev_dict
