"""Tests for errors.codes and errors.models.

Coverage targets:
- Every error code constant has the correct string value
- ALL_ERROR_CODES contains every code and nothing extra
- ValidationError dataclass construction, immutability, and to_dict()
- Frozen/hashable properties
- to_dict() produces spec §12-compliant structure
- Edge cases: None value, complex value types
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from agentobs_validate.errors.codes import (
    ALL_ERROR_CODES,
    INVALID_EVENT_TYPE,
    INVALID_NAMESPACE,
    INVALID_SIGNATURE,
    INVALID_SOURCE_FORMAT,
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


# ── Error code string values ──────────────────────────────────────────────────


class TestErrorCodeValues:
    """Each constant must match the exact string in spec §8."""

    def test_missing_event_id(self) -> None:
        assert MISSING_EVENT_ID == "MISSING_EVENT_ID"

    def test_invalid_ulid(self) -> None:
        assert INVALID_ULID == "INVALID_ULID"

    def test_missing_timestamp(self) -> None:
        assert MISSING_TIMESTAMP == "MISSING_TIMESTAMP"

    def test_invalid_timestamp(self) -> None:
        assert INVALID_TIMESTAMP == "INVALID_TIMESTAMP"

    def test_invalid_event_type(self) -> None:
        assert INVALID_EVENT_TYPE == "INVALID_EVENT_TYPE"

    def test_invalid_namespace(self) -> None:
        assert INVALID_NAMESPACE == "INVALID_NAMESPACE"

    def test_missing_source(self) -> None:
        assert MISSING_SOURCE == "MISSING_SOURCE"

    def test_invalid_source_format(self) -> None:
        assert INVALID_SOURCE_FORMAT == "INVALID_SOURCE_FORMAT"

    def test_invalid_trace_id(self) -> None:
        assert INVALID_TRACE_ID == "INVALID_TRACE_ID"

    def test_invalid_span_id(self) -> None:
        assert INVALID_SPAN_ID == "INVALID_SPAN_ID"

    def test_invalid_signature(self) -> None:
        assert INVALID_SIGNATURE == "INVALID_SIGNATURE"

    def test_unsupported_algorithm(self) -> None:
        assert UNSUPPORTED_ALGORITHM == "UNSUPPORTED_ALGORITHM"


class TestAllErrorCodesCatalog:
    """ALL_ERROR_CODES must contain every spec code and nothing undocumented."""

    EXPECTED_CODES = {
        "MISSING_EVENT_ID",
        "INVALID_ULID",
        "MISSING_TIMESTAMP",
        "INVALID_TIMESTAMP",
        "INVALID_EVENT_TYPE",
        "INVALID_NAMESPACE",
        "MISSING_SOURCE",
        "INVALID_SOURCE_FORMAT",
        "INVALID_TRACE_ID",
        "INVALID_SPAN_ID",
        "INVALID_SIGNATURE",
        "UNSUPPORTED_ALGORITHM",
    }

    def test_all_codes_count(self) -> None:
        assert len(ALL_ERROR_CODES) == 12

    def test_all_codes_is_frozenset(self) -> None:
        assert isinstance(ALL_ERROR_CODES, frozenset)

    def test_all_codes_matches_expected(self) -> None:
        assert ALL_ERROR_CODES == self.EXPECTED_CODES

    @pytest.mark.parametrize("code", list(EXPECTED_CODES))
    def test_each_code_in_all_codes(self, code: str) -> None:
        assert code in ALL_ERROR_CODES

    def test_no_lowercase_codes(self) -> None:
        for code in ALL_ERROR_CODES:
            assert code == code.upper(), f"Code not uppercase: {code!r}"

    def test_no_duplicate_codes(self) -> None:
        # frozenset guarantees uniqueness, but verify count matches the list
        all_as_list = [
            MISSING_EVENT_ID, INVALID_ULID, MISSING_TIMESTAMP,
            INVALID_TIMESTAMP, INVALID_EVENT_TYPE, INVALID_NAMESPACE,
            MISSING_SOURCE, INVALID_SOURCE_FORMAT, INVALID_TRACE_ID,
            INVALID_SPAN_ID, INVALID_SIGNATURE, UNSUPPORTED_ALGORITHM,
        ]
        assert len(all_as_list) == len(set(all_as_list))


# ── ValidationError dataclass ─────────────────────────────────────────────────


class TestValidationErrorConstruction:
    """ValidationError must be constructable with required and optional args."""

    def test_basic_construction(self) -> None:
        err = ValidationError(
            code=INVALID_ULID,
            field="event_id",
            message="event_id must be a valid ULID",
            value="bad-value",
        )
        assert err.code == INVALID_ULID
        assert err.field == "event_id"
        assert err.message == "event_id must be a valid ULID"
        assert err.value == "bad-value"

    def test_value_defaults_to_none(self) -> None:
        err = ValidationError(
            code=MISSING_EVENT_ID,
            field="event_id",
            message="event_id is required",
        )
        assert err.value is None

    def test_value_can_be_none_explicitly(self) -> None:
        err = ValidationError(
            code=MISSING_EVENT_ID,
            field="event_id",
            message="event_id is required",
            value=None,
        )
        assert err.value is None

    def test_value_can_be_integer(self) -> None:
        err = ValidationError(code=INVALID_ULID, field="event_id",
                              message="msg", value=42)
        assert err.value == 42

    def test_value_can_be_dict(self) -> None:
        err = ValidationError(code=INVALID_SIGNATURE, field="signature",
                              message="msg", value={"algorithm": "MD5"})
        assert isinstance(err.value, dict)


class TestValidationErrorImmutability:
    """ValidationError must be frozen — no mutation allowed."""

    def test_code_cannot_be_reassigned(self) -> None:
        err = ValidationError(code=INVALID_ULID, field="event_id",
                              message="msg", value="x")
        with pytest.raises(FrozenInstanceError):
            err.code = "OTHER_CODE"  # type: ignore[misc]

    def test_field_cannot_be_reassigned(self) -> None:
        err = ValidationError(code=INVALID_ULID, field="event_id",
                              message="msg", value="x")
        with pytest.raises(FrozenInstanceError):
            err.field = "other_field"  # type: ignore[misc]

    def test_message_cannot_be_reassigned(self) -> None:
        err = ValidationError(code=INVALID_ULID, field="event_id",
                              message="msg", value="x")
        with pytest.raises(FrozenInstanceError):
            err.message = "new message"  # type: ignore[misc]


class TestValidationErrorEquality:
    """Two ValidationErrors with same code+field+message must be equal."""

    def test_equal_instances(self) -> None:
        a = ValidationError(code=INVALID_ULID, field="event_id",
                            message="msg", value="x")
        b = ValidationError(code=INVALID_ULID, field="event_id",
                            message="msg", value="y")  # value excluded from compare
        assert a == b

    def test_different_code_not_equal(self) -> None:
        a = ValidationError(code=INVALID_ULID, field="event_id", message="msg")
        b = ValidationError(code=MISSING_EVENT_ID, field="event_id", message="msg")
        assert a != b

    def test_different_field_not_equal(self) -> None:
        a = ValidationError(code=INVALID_ULID, field="event_id", message="msg")
        b = ValidationError(code=INVALID_ULID, field="trace_id", message="msg")
        assert a != b

    def test_hashable_in_set(self) -> None:
        a = ValidationError(code=INVALID_ULID, field="event_id", message="msg")
        b = ValidationError(code=INVALID_ULID, field="event_id", message="msg")
        s = {a, b}
        assert len(s) == 1

    def test_usable_as_dict_key(self) -> None:
        err = ValidationError(code=INVALID_ULID, field="event_id", message="msg")
        d = {err: "found"}
        assert d[err] == "found"


class TestValidationErrorToDict:
    """to_dict() must produce a spec §12-compliant JSON-serialisable dict."""

    def test_to_dict_returns_dict(self) -> None:
        err = ValidationError(code=INVALID_ULID, field="event_id",
                              message="msg", value="bad")
        assert isinstance(err.to_dict(), dict)

    def test_to_dict_has_all_keys(self) -> None:
        err = ValidationError(code=INVALID_ULID, field="event_id",
                              message="msg", value="bad")
        d = err.to_dict()
        assert set(d.keys()) == {"code", "field", "message", "value"}

    def test_to_dict_code(self) -> None:
        err = ValidationError(code=INVALID_ULID, field="event_id",
                              message="msg", value="bad")
        assert err.to_dict()["code"] == INVALID_ULID

    def test_to_dict_field(self) -> None:
        err = ValidationError(code=INVALID_ULID, field="event_id",
                              message="msg", value="bad")
        assert err.to_dict()["field"] == "event_id"

    def test_to_dict_message(self) -> None:
        err = ValidationError(code=INVALID_ULID, field="event_id",
                              message="must be a valid ULID", value="bad")
        assert err.to_dict()["message"] == "must be a valid ULID"

    def test_to_dict_value(self) -> None:
        err = ValidationError(code=INVALID_ULID, field="event_id",
                              message="msg", value="bad-id")
        assert err.to_dict()["value"] == "bad-id"

    def test_to_dict_value_none(self) -> None:
        err = ValidationError(code=MISSING_EVENT_ID, field="event_id",
                              message="msg", value=None)
        assert err.to_dict()["value"] is None

    def test_to_dict_matches_spec_example(self) -> None:
        """Verify the exact structure from spec §12."""
        err = ValidationError(
            code="INVALID_EVENT_TYPE",
            field="event_type",
            message="event_type must match domain.category.action",
            value="agenttoolcalled",
        )
        d = err.to_dict()
        assert d == {
            "code": "INVALID_EVENT_TYPE",
            "field": "event_type",
            "message": "event_type must match domain.category.action",
            "value": "agenttoolcalled",
        }

    def test_to_dict_is_json_serialisable(self) -> None:
        import json

        err = ValidationError(code=INVALID_ULID, field="event_id",
                              message="must be ULID", value="bad")
        # Should not raise
        json.dumps(err.to_dict())

    def test_to_dict_does_not_mutate_instance(self) -> None:
        err = ValidationError(code=INVALID_ULID, field="event_id",
                              message="msg", value="bad")
        d = err.to_dict()
        d["code"] = "TAMPERED"
        # Original must be untouched
        assert err.code == INVALID_ULID
