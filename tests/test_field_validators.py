"""Tests for validator.field_validators.

Coverage targets (100%):
- Every validator returns [] on the spec §17 example event values
- Every error code is triggerable by a known bad input
- Missing field (None) → correct MISSING_* or INVALID_* code
- Non-string types → correct error code
- Boundary conditions (ULID length, trace_id 16 vs 32, span_id exactly 16)
- validate_signature: absent (skip), valid, wrong algorithm, bad base64,
  missing sub-fields, non-dict value, both errors simultaneously
"""

from __future__ import annotations

import pytest

from agentobs_validate.errors.codes import (
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
from agentobs_validate.schema.fields import (
    FIELD_EVENT_ID,
    FIELD_EVENT_TYPE,
    FIELD_SIG_ALGORITHM,
    FIELD_SIG_VALUE,
    FIELD_SIGNATURE,
    FIELD_SOURCE,
    FIELD_SPAN_ID,
    FIELD_TIMESTAMP,
    FIELD_TRACE_ID,
    SUPPORTED_SIGNATURE_ALGORITHM,
)
from agentobs_validate.validator.field_validators import (
    validate_event_id,
    validate_event_type,
    validate_signature,
    validate_source,
    validate_span_id,
    validate_timestamp,
    validate_trace_id,
)

# ── Spec §17 example values (the golden dataset) ─────────────────────────────

VALID_EVENT_ID = "01HZY7M4YQZB3D0V4K6Z5R9F7A"
VALID_TIMESTAMP = "2026-02-20T10:45:21.123Z"
VALID_EVENT_TYPE = "agent.tool.called"
VALID_SOURCE = "langchain@0.2.11"
VALID_TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
VALID_SPAN_ID = "00f067aa0ba902b7"
VALID_SIGNATURE = {
    "algorithm": "HMAC-SHA256",
    "key_id": "spanforge-key-1",
    "value": "dGVzdA==",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper: assert that a result contains exactly one error with the given code
# ─────────────────────────────────────────────────────────────────────────────


def _single_error(result: list[ValidationError], code: str, field: str) -> ValidationError:
    assert len(result) == 1, f"Expected 1 error, got {len(result)}: {result}"
    assert result[0].code == code, f"Expected code {code!r}, got {result[0].code!r}"
    assert result[0].field == field, f"Expected field {field!r}, got {result[0].field!r}"
    return result[0]


# ─────────────────────────────────────────────────────────────────────────────
# validate_event_id (spec §8.1)
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateEventId:
    """Tests for validate_event_id."""

    # ── Happy paths ───────────────────────────────────────────────────────────

    def test_valid_spec_example(self) -> None:
        assert validate_event_id(VALID_EVENT_ID) == []

    @pytest.mark.parametrize(
        "ulid",
        [
            "00000000000000000000000000",
            "7ZZZZZZZZZZZZZZZZZZZZZZZZZ",
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        ],
    )
    def test_valid_ulids(self, ulid: str) -> None:
        assert validate_event_id(ulid) == []

    # ── Missing ───────────────────────────────────────────────────────────────

    def test_none_gives_missing_event_id(self) -> None:
        err = _single_error(validate_event_id(None), MISSING_EVENT_ID, FIELD_EVENT_ID)
        assert err.value is None

    def test_missing_message_mentions_required(self) -> None:
        result = validate_event_id(None)
        assert "required" in result[0].message.lower()

    # ── Invalid format ────────────────────────────────────────────────────────

    def test_empty_string_gives_invalid_ulid(self) -> None:
        _single_error(validate_event_id(""), INVALID_ULID, FIELD_EVENT_ID)

    def test_lowercase_ulid_gives_invalid_ulid(self) -> None:
        err = _single_error(
            validate_event_id("01hzy7m4yqzb3d0v4k6z5r9f7a"), INVALID_ULID, FIELD_EVENT_ID
        )
        assert err.value == "01hzy7m4yqzb3d0v4k6z5r9f7a"

    def test_too_short_gives_invalid_ulid(self) -> None:
        _single_error(validate_event_id("01HZY7M4YQZB3D0V4K6Z5R9F7"), INVALID_ULID, FIELD_EVENT_ID)

    def test_too_long_gives_invalid_ulid(self) -> None:
        _single_error(validate_event_id("01HZY7M4YQZB3D0V4K6Z5R9F7AB"), INVALID_ULID, FIELD_EVENT_ID)

    def test_invalid_char_I_gives_invalid_ulid(self) -> None:
        _single_error(validate_event_id("01HZY7M4YQZB3D0V4K6Z5R9F7I"), INVALID_ULID, FIELD_EVENT_ID)

    def test_invalid_char_L_gives_invalid_ulid(self) -> None:
        _single_error(validate_event_id("01HZY7M4YQZB3D0V4K6Z5R9F7L"), INVALID_ULID, FIELD_EVENT_ID)

    def test_invalid_char_O_gives_invalid_ulid(self) -> None:
        _single_error(validate_event_id("01HZY7M4YQZB3D0V4K6Z5R9F7O"), INVALID_ULID, FIELD_EVENT_ID)

    def test_invalid_char_U_gives_invalid_ulid(self) -> None:
        _single_error(validate_event_id("01HZY7M4YQZB3D0V4K6Z5R9F7U"), INVALID_ULID, FIELD_EVENT_ID)

    # ── Non-string types ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("bad_type", [123, 12.5, True, [], {}])
    def test_non_string_gives_invalid_ulid(self, bad_type: object) -> None:
        err = _single_error(validate_event_id(bad_type), INVALID_ULID, FIELD_EVENT_ID)
        assert err.value == bad_type

    # ── Error value preserved ─────────────────────────────────────────────────

    def test_invalid_value_is_preserved(self) -> None:
        bad = "not-a-ulid"
        result = validate_event_id(bad)
        assert result[0].value == bad


# ─────────────────────────────────────────────────────────────────────────────
# validate_timestamp (spec §8.2)
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateTimestamp:
    """Tests for validate_timestamp."""

    # ── Happy paths ───────────────────────────────────────────────────────────

    def test_valid_spec_example(self) -> None:
        assert validate_timestamp(VALID_TIMESTAMP) == []

    @pytest.mark.parametrize(
        "ts",
        [
            "2026-02-20T10:45:21Z",
            "2026-12-31T23:59:59.999999Z",
            "2026-02-20T10:45:21+05:30",
            "2026-02-20T10:45:21-08:00",
        ],
    )
    def test_valid_timestamps(self, ts: str) -> None:
        assert validate_timestamp(ts) == []

    # ── Missing ───────────────────────────────────────────────────────────────

    def test_none_gives_missing_timestamp(self) -> None:
        err = _single_error(validate_timestamp(None), MISSING_TIMESTAMP, FIELD_TIMESTAMP)
        assert err.value is None

    def test_missing_message_mentions_required(self) -> None:
        result = validate_timestamp(None)
        assert "required" in result[0].message.lower()

    # ── Invalid format ────────────────────────────────────────────────────────

    def test_date_only_gives_invalid_timestamp(self) -> None:
        _single_error(validate_timestamp("2026-02-20"), INVALID_TIMESTAMP, FIELD_TIMESTAMP)

    def test_space_separator_gives_invalid_timestamp(self) -> None:
        _single_error(
            validate_timestamp("2026-02-20 10:45:21Z"), INVALID_TIMESTAMP, FIELD_TIMESTAMP
        )

    def test_no_tz_gives_invalid_timestamp(self) -> None:
        _single_error(
            validate_timestamp("2026-02-20T10:45:21"), INVALID_TIMESTAMP, FIELD_TIMESTAMP
        )

    def test_slash_date_gives_invalid_timestamp(self) -> None:
        _single_error(
            validate_timestamp("2026/02/20T10:45:21Z"), INVALID_TIMESTAMP, FIELD_TIMESTAMP
        )

    def test_empty_string_gives_invalid_timestamp(self) -> None:
        _single_error(validate_timestamp(""), INVALID_TIMESTAMP, FIELD_TIMESTAMP)

    def test_garbage_string_gives_invalid_timestamp(self) -> None:
        _single_error(validate_timestamp("not-a-date"), INVALID_TIMESTAMP, FIELD_TIMESTAMP)

    def test_invalid_value_is_preserved(self) -> None:
        bad = "2026-02-20"
        result = validate_timestamp(bad)
        assert result[0].value == bad

    # ── Non-string types ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("bad_type", [1234567890, True, [], {}])
    def test_non_string_gives_invalid_timestamp(self, bad_type: object) -> None:
        _single_error(validate_timestamp(bad_type), INVALID_TIMESTAMP, FIELD_TIMESTAMP)


# ─────────────────────────────────────────────────────────────────────────────
# validate_event_type (spec §8.3)
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateEventType:
    """Tests for validate_event_type.

    Distinguishes INVALID_EVENT_TYPE (missing/non-string) from
    INVALID_NAMESPACE (string but wrong format).
    """

    # ── Happy paths ───────────────────────────────────────────────────────────

    def test_valid_spec_example(self) -> None:
        assert validate_event_type(VALID_EVENT_TYPE) == []

    @pytest.mark.parametrize(
        "et",
        [
            "agent.plan.created",
            "agent.llm.request",
            "agent.llm.response",
            "agent.memory.write",
            "agent.memory.read_all",
            "a.b.c",
            "a1.b2.c3",
        ],
    )
    def test_valid_event_types(self, et: str) -> None:
        assert validate_event_type(et) == []

    # ── Missing → INVALID_EVENT_TYPE ─────────────────────────────────────────

    def test_none_gives_invalid_event_type(self) -> None:
        err = _single_error(validate_event_type(None), INVALID_EVENT_TYPE, FIELD_EVENT_TYPE)
        assert err.value is None

    def test_missing_message(self) -> None:
        result = validate_event_type(None)
        assert "required" in result[0].message.lower()

    # ── Non-string → INVALID_EVENT_TYPE ──────────────────────────────────────

    @pytest.mark.parametrize("bad_type", [123, True, [], {}])
    def test_non_string_gives_invalid_event_type(self, bad_type: object) -> None:
        _single_error(validate_event_type(bad_type), INVALID_EVENT_TYPE, FIELD_EVENT_TYPE)

    # ── Bad namespace format → INVALID_NAMESPACE ──────────────────────────────

    def test_no_dots_gives_invalid_namespace(self) -> None:
        err = _single_error(
            validate_event_type("agenttoolcalled"), INVALID_NAMESPACE, FIELD_EVENT_TYPE
        )
        assert err.value == "agenttoolcalled"  # spec §12 bad value example

    def test_two_parts_gives_invalid_namespace(self) -> None:
        _single_error(validate_event_type("agent.tool"), INVALID_NAMESPACE, FIELD_EVENT_TYPE)

    def test_four_parts_gives_invalid_namespace(self) -> None:
        _single_error(
            validate_event_type("agent.tool.called.extra"), INVALID_NAMESPACE, FIELD_EVENT_TYPE
        )

    def test_uppercase_gives_invalid_namespace(self) -> None:
        _single_error(
            validate_event_type("Agent.Tool.Called"), INVALID_NAMESPACE, FIELD_EVENT_TYPE
        )

    def test_empty_string_gives_invalid_namespace(self) -> None:
        _single_error(validate_event_type(""), INVALID_NAMESPACE, FIELD_EVENT_TYPE)

    def test_special_char_gives_invalid_namespace(self) -> None:
        _single_error(
            validate_event_type("agent.tool.called!"), INVALID_NAMESPACE, FIELD_EVENT_TYPE
        )

    def test_hyphen_in_domain_gives_invalid_namespace(self) -> None:
        _single_error(
            validate_event_type("agent-tool.called.x"), INVALID_NAMESPACE, FIELD_EVENT_TYPE
        )

    def test_invalid_namespace_value_is_preserved(self) -> None:
        bad = "agent.tool"
        result = validate_event_type(bad)
        assert result[0].value == bad


# ─────────────────────────────────────────────────────────────────────────────
# validate_source (spec §8.4)
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateSource:
    """Tests for validate_source."""

    # ── Happy paths ───────────────────────────────────────────────────────────

    def test_valid_spec_example(self) -> None:
        assert validate_source(VALID_SOURCE) == []

    @pytest.mark.parametrize(
        "src",
        [
            "autogen@0.4.1",
            "spanforge@1.0.0",
            "agent-runtime@0.9.2",
            "my_tool@10.20.300",
        ],
    )
    def test_valid_sources(self, src: str) -> None:
        assert validate_source(src) == []

    # ── Missing ───────────────────────────────────────────────────────────────

    def test_none_gives_missing_source(self) -> None:
        err = _single_error(validate_source(None), MISSING_SOURCE, FIELD_SOURCE)
        assert err.value is None

    def test_missing_message_mentions_required(self) -> None:
        result = validate_source(None)
        assert "required" in result[0].message.lower()

    # ── Invalid format ────────────────────────────────────────────────────────

    def test_no_at_sign_gives_invalid_source(self) -> None:
        _single_error(validate_source("langchain"), INVALID_SOURCE_FORMAT, FIELD_SOURCE)

    def test_no_version_gives_invalid_source(self) -> None:
        _single_error(validate_source("langchain@"), INVALID_SOURCE_FORMAT, FIELD_SOURCE)

    def test_no_name_gives_invalid_source(self) -> None:
        _single_error(validate_source("@0.2.11"), INVALID_SOURCE_FORMAT, FIELD_SOURCE)

    def test_two_part_version_gives_invalid_source(self) -> None:
        _single_error(validate_source("langchain@0.2"), INVALID_SOURCE_FORMAT, FIELD_SOURCE)

    def test_four_part_version_gives_invalid_source(self) -> None:
        _single_error(validate_source("langchain@0.2.11.5"), INVALID_SOURCE_FORMAT, FIELD_SOURCE)

    def test_non_numeric_version_gives_invalid_source(self) -> None:
        _single_error(validate_source("langchain@a.b.c"), INVALID_SOURCE_FORMAT, FIELD_SOURCE)

    def test_space_in_name_gives_invalid_source(self) -> None:
        _single_error(validate_source("lang chain@0.1.0"), INVALID_SOURCE_FORMAT, FIELD_SOURCE)

    def test_empty_string_gives_invalid_source(self) -> None:
        _single_error(validate_source(""), INVALID_SOURCE_FORMAT, FIELD_SOURCE)

    def test_invalid_value_is_preserved(self) -> None:
        bad = "langchain"
        result = validate_source(bad)
        assert result[0].value == bad

    # ── Non-string types ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("bad_type", [42, True, [], {}])
    def test_non_string_gives_invalid_source(self, bad_type: object) -> None:
        _single_error(validate_source(bad_type), INVALID_SOURCE_FORMAT, FIELD_SOURCE)


# ─────────────────────────────────────────────────────────────────────────────
# validate_trace_id (spec §8.5)
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateTraceId:
    """Tests for validate_trace_id."""

    # ── Happy paths ───────────────────────────────────────────────────────────

    def test_valid_spec_example_32_chars(self) -> None:
        assert validate_trace_id(VALID_TRACE_ID) == []

    def test_16_chars_invalid(self) -> None:
        _single_error(validate_trace_id("4bf92f3577b34da6"), INVALID_TRACE_ID, FIELD_TRACE_ID)

    def test_valid_32_chars_all_zeros(self) -> None:
        assert validate_trace_id("0" * 32) == []

    def test_16_chars_all_f_invalid(self) -> None:
        _single_error(validate_trace_id("f" * 16), INVALID_TRACE_ID, FIELD_TRACE_ID)

    # ── Missing ───────────────────────────────────────────────────────────────

    def test_none_gives_invalid_trace_id(self) -> None:
        err = _single_error(validate_trace_id(None), INVALID_TRACE_ID, FIELD_TRACE_ID)
        assert err.value is None

    # ── Invalid format ────────────────────────────────────────────────────────

    def test_15_chars_gives_invalid_trace_id(self) -> None:
        _single_error(validate_trace_id("a" * 15), INVALID_TRACE_ID, FIELD_TRACE_ID)

    def test_33_chars_gives_invalid_trace_id(self) -> None:
        _single_error(validate_trace_id("a" * 33), INVALID_TRACE_ID, FIELD_TRACE_ID)

    def test_uppercase_gives_invalid_trace_id(self) -> None:
        _single_error(
            validate_trace_id("4BF92F3577B34DA6A3CE929D0E0E4736"),
            INVALID_TRACE_ID,
            FIELD_TRACE_ID,
        )

    def test_non_hex_char_gives_invalid_trace_id(self) -> None:
        _single_error(
            validate_trace_id("4bf92f3577b34da6a3ce929d0e0e473g"),
            INVALID_TRACE_ID,
            FIELD_TRACE_ID,
        )

    def test_empty_string_gives_invalid_trace_id(self) -> None:
        _single_error(validate_trace_id(""), INVALID_TRACE_ID, FIELD_TRACE_ID)

    def test_invalid_value_is_preserved(self) -> None:
        bad = "UPPERCASE"
        result = validate_trace_id(bad)
        assert result[0].value == bad

    # ── Boundary conditions ───────────────────────────────────────────────────

    def test_boundary_exactly_16_invalid(self) -> None:
        _single_error(validate_trace_id("a" * 16), INVALID_TRACE_ID, FIELD_TRACE_ID)

    def test_boundary_exactly_32(self) -> None:
        assert validate_trace_id("a" * 32) == []

    def test_boundary_17_chars_invalid(self) -> None:
        _single_error(validate_trace_id("a" * 17), INVALID_TRACE_ID, FIELD_TRACE_ID)

    def test_boundary_31_chars_invalid(self) -> None:
        _single_error(validate_trace_id("a" * 31), INVALID_TRACE_ID, FIELD_TRACE_ID)

    # ── Non-string types ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("bad_type", [123, True, [], {}])
    def test_non_string_gives_invalid_trace_id(self, bad_type: object) -> None:
        _single_error(validate_trace_id(bad_type), INVALID_TRACE_ID, FIELD_TRACE_ID)


# ─────────────────────────────────────────────────────────────────────────────
# validate_span_id (spec §8.6)
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateSpanId:
    """Tests for validate_span_id."""

    # ── Happy paths ───────────────────────────────────────────────────────────

    def test_valid_spec_example(self) -> None:
        assert validate_span_id(VALID_SPAN_ID) == []

    def test_valid_all_zeros(self) -> None:
        assert validate_span_id("0" * 16) == []

    def test_valid_all_f(self) -> None:
        assert validate_span_id("f" * 16) == []

    def test_valid_mixed(self) -> None:
        assert validate_span_id("abcdef0123456789") == []

    # ── Missing ───────────────────────────────────────────────────────────────

    def test_none_gives_invalid_span_id(self) -> None:
        err = _single_error(validate_span_id(None), INVALID_SPAN_ID, FIELD_SPAN_ID)
        assert err.value is None

    # ── Invalid format ────────────────────────────────────────────────────────

    def test_15_chars_gives_invalid_span_id(self) -> None:
        _single_error(validate_span_id("a" * 15), INVALID_SPAN_ID, FIELD_SPAN_ID)

    def test_17_chars_gives_invalid_span_id(self) -> None:
        _single_error(validate_span_id("a" * 17), INVALID_SPAN_ID, FIELD_SPAN_ID)

    def test_uppercase_gives_invalid_span_id(self) -> None:
        _single_error(validate_span_id("00F067AA0BA902B7"), INVALID_SPAN_ID, FIELD_SPAN_ID)

    def test_non_hex_char_gives_invalid_span_id(self) -> None:
        _single_error(validate_span_id("00f067aa0ba902bz"), INVALID_SPAN_ID, FIELD_SPAN_ID)

    def test_empty_string_gives_invalid_span_id(self) -> None:
        _single_error(validate_span_id(""), INVALID_SPAN_ID, FIELD_SPAN_ID)

    def test_invalid_value_is_preserved(self) -> None:
        bad = "tooshort"
        result = validate_span_id(bad)
        assert result[0].value == bad

    # ── Boundary conditions ───────────────────────────────────────────────────

    def test_boundary_exactly_16(self) -> None:
        assert validate_span_id("a" * 16) == []

    def test_boundary_15_fails(self) -> None:
        assert validate_span_id("a" * 15) != []

    def test_boundary_17_fails(self) -> None:
        assert validate_span_id("a" * 17) != []

    # ── Non-string types ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("bad_type", [123, True, [], {}])
    def test_non_string_gives_invalid_span_id(self, bad_type: object) -> None:
        _single_error(validate_span_id(bad_type), INVALID_SPAN_ID, FIELD_SPAN_ID)


# ─────────────────────────────────────────────────────────────────────────────
# validate_signature (spec §8.7)
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateSignature:
    """Tests for validate_signature (optional field)."""

    # ── Absent — no errors ────────────────────────────────────────────────────

    def test_none_returns_empty(self) -> None:
        assert validate_signature(None) == []

    # ── Valid structure ───────────────────────────────────────────────────────

    def test_valid_full_signature(self) -> None:
        assert validate_signature(VALID_SIGNATURE) == []

    def test_valid_longer_base64_value(self) -> None:
        sig = {
            "algorithm": SUPPORTED_SIGNATURE_ALGORITHM,
            "key_id": "my-key",
            "value": "dGhpcyBpcyBhIHRlc3Q=",
        }
        assert validate_signature(sig) == []

    def test_key_id_is_not_validated(self) -> None:
        """key_id is informational only — any value is acceptable."""
        sig = {
            "algorithm": SUPPORTED_SIGNATURE_ALGORITHM,
            "key_id": 12345,  # non-string key_id — still passes
            "value": "dGVzdA==",
        }
        assert validate_signature(sig) == []

    # ── Wrong algorithm ───────────────────────────────────────────────────────

    def test_wrong_algorithm_gives_unsupported_algorithm(self) -> None:
        sig = {"algorithm": "MD5", "key_id": "k", "value": "dGVzdA=="}
        _single_error(validate_signature(sig), UNSUPPORTED_ALGORITHM, FIELD_SIG_ALGORITHM)

    def test_sha1_algorithm_gives_unsupported(self) -> None:
        sig = {"algorithm": "HMAC-SHA1", "key_id": "k", "value": "dGVzdA=="}
        _single_error(validate_signature(sig), UNSUPPORTED_ALGORITHM, FIELD_SIG_ALGORITHM)

    def test_missing_algorithm_gives_unsupported(self) -> None:
        sig = {"key_id": "k", "value": "dGVzdA=="}
        _single_error(validate_signature(sig), UNSUPPORTED_ALGORITHM, FIELD_SIG_ALGORITHM)

    def test_wrong_algorithm_value_is_preserved(self) -> None:
        bad_algo = "RSA-SHA256"
        sig = {"algorithm": bad_algo, "key_id": "k", "value": "dGVzdA=="}
        result = validate_signature(sig)
        assert result[0].value == bad_algo

    def test_none_algorithm_gives_unsupported(self) -> None:
        sig = {"algorithm": None, "key_id": "k", "value": "dGVzdA=="}
        _single_error(validate_signature(sig), UNSUPPORTED_ALGORITHM, FIELD_SIG_ALGORITHM)

    # ── Invalid base64 value ──────────────────────────────────────────────────

    def test_invalid_base64_gives_invalid_signature(self) -> None:
        sig = {"algorithm": SUPPORTED_SIGNATURE_ALGORITHM, "key_id": "k", "value": "bad!base64"}
        _single_error(validate_signature(sig), INVALID_SIGNATURE, FIELD_SIG_VALUE)

    def test_missing_value_gives_invalid_signature(self) -> None:
        sig = {"algorithm": SUPPORTED_SIGNATURE_ALGORITHM, "key_id": "k"}
        _single_error(validate_signature(sig), INVALID_SIGNATURE, FIELD_SIG_VALUE)

    def test_none_value_gives_invalid_signature(self) -> None:
        sig = {"algorithm": SUPPORTED_SIGNATURE_ALGORITHM, "key_id": "k", "value": None}
        _single_error(validate_signature(sig), INVALID_SIGNATURE, FIELD_SIG_VALUE)

    def test_empty_string_value_gives_invalid_signature(self) -> None:
        sig = {"algorithm": SUPPORTED_SIGNATURE_ALGORITHM, "key_id": "k", "value": ""}
        _single_error(validate_signature(sig), INVALID_SIGNATURE, FIELD_SIG_VALUE)

    def test_integer_value_gives_invalid_signature(self) -> None:
        sig = {"algorithm": SUPPORTED_SIGNATURE_ALGORITHM, "key_id": "k", "value": 12345}
        _single_error(validate_signature(sig), INVALID_SIGNATURE, FIELD_SIG_VALUE)

    # ── Both errors simultaneously ────────────────────────────────────────────

    def test_wrong_algo_and_bad_value_gives_two_errors(self) -> None:
        sig = {"algorithm": "MD5", "key_id": "k", "value": "!!!"}
        result = validate_signature(sig)
        assert len(result) == 2
        codes = {e.code for e in result}
        assert UNSUPPORTED_ALGORITHM in codes
        assert INVALID_SIGNATURE in codes

    def test_missing_algo_and_missing_value_gives_two_errors(self) -> None:
        sig = {"key_id": "k"}
        result = validate_signature(sig)
        assert len(result) == 2
        codes = {e.code for e in result}
        assert UNSUPPORTED_ALGORITHM in codes
        assert INVALID_SIGNATURE in codes

    # ── Non-dict signature ────────────────────────────────────────────────────

    def test_non_dict_string_gives_two_errors(self) -> None:
        result = validate_signature("not-a-dict")
        assert len(result) == 2
        codes = {e.code for e in result}
        assert UNSUPPORTED_ALGORITHM in codes
        assert INVALID_SIGNATURE in codes

    def test_non_dict_int_gives_two_errors(self) -> None:
        result = validate_signature(42)
        assert len(result) == 2

    def test_non_dict_list_gives_two_errors(self) -> None:
        result = validate_signature([])
        assert len(result) == 2

    # ── Return type contract ──────────────────────────────────────────────────

    def test_always_returns_list(self) -> None:
        assert isinstance(validate_signature(None), list)
        assert isinstance(validate_signature(VALID_SIGNATURE), list)

    def test_errors_are_validation_error_instances(self) -> None:
        sig = {"algorithm": "bad", "key_id": "k", "value": "!!!"}
        result = validate_signature(sig)
        for err in result:
            assert isinstance(err, ValidationError)


# ─────────────────────────────────────────────────────────────────────────────
# Cross-cutting contracts
# ─────────────────────────────────────────────────────────────────────────────


class TestValidatorContracts:
    """Contracts that apply to every field validator."""

    ALL_VALIDATORS = [
        (validate_event_id, VALID_EVENT_ID),
        (validate_timestamp, VALID_TIMESTAMP),
        (validate_event_type, VALID_EVENT_TYPE),
        (validate_source, VALID_SOURCE),
        (validate_trace_id, VALID_TRACE_ID),
        (validate_span_id, VALID_SPAN_ID),
        (validate_signature, None),
    ]

    @pytest.mark.parametrize("fn,valid_value", ALL_VALIDATORS)
    def test_valid_input_returns_empty_list(self, fn: object, valid_value: object) -> None:
        result = fn(valid_value)  # type: ignore[operator]
        assert result == [], f"{fn.__name__} returned errors for valid input: {result}"

    @pytest.mark.parametrize("fn,valid_value", ALL_VALIDATORS)
    def test_return_type_is_always_list(self, fn: object, valid_value: object) -> None:
        assert isinstance(fn(valid_value), list)  # type: ignore[operator]

    @pytest.mark.parametrize("fn,valid_value", ALL_VALIDATORS)
    def test_errors_are_validation_error_instances(self, fn: object, valid_value: object) -> None:
        fn_typed = fn  # type: ignore[assignment]
        for err in fn_typed(None):
            assert isinstance(err, ValidationError)

    def test_spec_example_event_fully_valid(self) -> None:
        """The spec §17 example event must produce zero errors across all validators."""
        all_errors = (
            validate_event_id(VALID_EVENT_ID)
            + validate_timestamp(VALID_TIMESTAMP)
            + validate_event_type(VALID_EVENT_TYPE)
            + validate_source(VALID_SOURCE)
            + validate_trace_id(VALID_TRACE_ID)
            + validate_span_id(VALID_SPAN_ID)
            + validate_signature(None)
        )
        assert all_errors == [], f"Spec §17 example produced errors: {all_errors}"

    def test_spec_example_with_signature_fully_valid(self) -> None:
        all_errors = (
            validate_event_id(VALID_EVENT_ID)
            + validate_timestamp(VALID_TIMESTAMP)
            + validate_event_type(VALID_EVENT_TYPE)
            + validate_source(VALID_SOURCE)
            + validate_trace_id(VALID_TRACE_ID)
            + validate_span_id(VALID_SPAN_ID)
            + validate_signature(VALID_SIGNATURE)
        )
        assert all_errors == []
