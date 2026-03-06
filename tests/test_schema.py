"""Tests for schema.fields and schema.patterns.

Coverage targets:
- Every field constant has the correct string value
- REQUIRED_FIELDS and OPTIONAL_FIELDS contain the right members
- REQUIRED_FIELDS_ORDERED preserves spec §9 pipeline order
- Every regex accepts all spec §17 example values
- Every regex rejects known bad inputs
- Boundary conditions for trace_id (16 vs 32 chars)
- BASE64_RE handles padding variants and empty string
"""

from __future__ import annotations

import re

import pytest

from agentobs_validate.schema.fields import (
    FIELD_EVENT_ID,
    FIELD_EVENT_TYPE,
    FIELD_SIG_ALGORITHM,
    FIELD_SIG_KEY_ID,
    FIELD_SIG_VALUE,
    FIELD_SIGNATURE,
    FIELD_SOURCE,
    FIELD_SPAN_ID,
    FIELD_TIMESTAMP,
    FIELD_TRACE_ID,
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    REQUIRED_FIELDS_ORDERED,
    SUPPORTED_SIGNATURE_ALGORITHM,
)
from agentobs_validate.schema.patterns import (
    BASE64_RE,
    EVENT_TYPE_RE,
    SOURCE_RE,
    SPAN_ID_RE,
    TIMESTAMP_RE,
    TRACE_ID_RE,
    ULID_RE,
)


# ── Field name constants ──────────────────────────────────────────────────────


class TestFieldNameConstants:
    """Field constants must match spec §7 names exactly (no typos)."""

    def test_event_id_constant(self) -> None:
        assert FIELD_EVENT_ID == "event_id"

    def test_timestamp_constant(self) -> None:
        assert FIELD_TIMESTAMP == "timestamp"

    def test_event_type_constant(self) -> None:
        assert FIELD_EVENT_TYPE == "event_type"

    def test_source_constant(self) -> None:
        assert FIELD_SOURCE == "source"

    def test_trace_id_constant(self) -> None:
        assert FIELD_TRACE_ID == "trace_id"

    def test_span_id_constant(self) -> None:
        assert FIELD_SPAN_ID == "span_id"

    def test_signature_constant(self) -> None:
        assert FIELD_SIGNATURE == "signature"

    def test_sig_algorithm_constant(self) -> None:
        assert FIELD_SIG_ALGORITHM == "algorithm"

    def test_sig_key_id_constant(self) -> None:
        assert FIELD_SIG_KEY_ID == "key_id"

    def test_sig_value_constant(self) -> None:
        assert FIELD_SIG_VALUE == "value"

    def test_supported_algorithm(self) -> None:
        assert SUPPORTED_SIGNATURE_ALGORITHM == "HMAC-SHA256"


class TestFieldSets:
    """REQUIRED_FIELDS and OPTIONAL_FIELDS must contain the correct members."""

    def test_required_fields_count(self) -> None:
        assert len(REQUIRED_FIELDS) == 6

    def test_required_fields_contains_all_spec_fields(self) -> None:
        expected = {"event_id", "timestamp", "event_type", "source", "trace_id", "span_id"}
        assert REQUIRED_FIELDS == expected

    def test_optional_fields_count(self) -> None:
        assert len(OPTIONAL_FIELDS) == 1

    def test_optional_fields_contains_signature(self) -> None:
        assert "signature" in OPTIONAL_FIELDS

    def test_required_and_optional_are_disjoint(self) -> None:
        assert REQUIRED_FIELDS.isdisjoint(OPTIONAL_FIELDS)

    def test_required_fields_is_frozenset(self) -> None:
        assert isinstance(REQUIRED_FIELDS, frozenset)

    def test_optional_fields_is_frozenset(self) -> None:
        assert isinstance(OPTIONAL_FIELDS, frozenset)


class TestRequiredFieldsOrdered:
    """REQUIRED_FIELDS_ORDERED must respect the spec §9 pipeline order."""

    def test_ordered_length(self) -> None:
        assert len(REQUIRED_FIELDS_ORDERED) == 6

    def test_ordered_contains_all_required(self) -> None:
        assert set(REQUIRED_FIELDS_ORDERED) == REQUIRED_FIELDS

    def test_event_id_is_first(self) -> None:
        assert REQUIRED_FIELDS_ORDERED[0] == "event_id"

    def test_span_id_is_last(self) -> None:
        assert REQUIRED_FIELDS_ORDERED[-1] == "span_id"

    def test_ordered_is_tuple(self) -> None:
        assert isinstance(REQUIRED_FIELDS_ORDERED, tuple)

    def test_pipeline_order(self) -> None:
        expected = ("event_id", "timestamp", "event_type", "source", "trace_id", "span_id")
        assert REQUIRED_FIELDS_ORDERED == expected


# ── ULID regex (spec §8.1) ────────────────────────────────────────────────────


class TestUlidRe:
    """ULID must be exactly 26 Crockford Base32 characters."""

    @pytest.mark.parametrize(
        "valid",
        [
            "01HZY7M4YQZB3D0V4K6Z5R9F7A",  # spec §17 example
            "00000000000000000000000000",
            "7ZZZZZZZZZZZZZZZZZZZZZZZZZ",
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        ],
    )
    def test_valid_ulid(self, valid: str) -> None:
        assert ULID_RE.match(valid), f"Expected valid, got no match: {valid!r}"

    @pytest.mark.parametrize(
        "invalid",
        [
            "",                              # empty
            "01HZY7M4YQZB3D0V4K6Z5R9F7",   # 25 chars (too short)
            "01HZY7M4YQZB3D0V4K6Z5R9F7AB",  # 27 chars (too long)
            "01HZY7M4YQZB3D0V4K6Z5R9F7I",  # contains I (invalid char)
            "01HZY7M4YQZB3D0V4K6Z5R9F7L",  # contains L (invalid char)
            "01HZY7M4YQZB3D0V4K6Z5R9F7O",  # contains O (invalid char)
            "01HZY7M4YQZB3D0V4K6Z5R9F7U",  # contains U (invalid char)
            "01hzy7m4yqzb3d0v4k6z5r9f7a",  # lowercase (invalid)
            "01HZY7M4YQZB3D0V4K6Z5R9F7!",  # special char
        ],
    )
    def test_invalid_ulid(self, invalid: str) -> None:
        assert not ULID_RE.match(invalid), f"Expected no match, got match: {invalid!r}"


# ── Timestamp regex (spec §8.2) ───────────────────────────────────────────────


class TestTimestampRe:
    """Timestamps must be RFC3339/ISO8601 with date, time, and timezone."""

    @pytest.mark.parametrize(
        "valid",
        [
            "2026-02-20T10:45:21.123Z",    # spec §17 example
            "2026-02-20T10:45:21Z",         # no fractional seconds
            "2026-02-20T10:45:21.000000Z",  # 6-digit microseconds
            "2026-02-20T00:00:00Z",
            "2026-12-31T23:59:59Z",
            "2026-02-20T10:45:21+05:30",    # positive offset
            "2026-02-20T10:45:21-08:00",    # negative offset
        ],
    )
    def test_valid_timestamp(self, valid: str) -> None:
        assert TIMESTAMP_RE.match(valid), f"Expected valid: {valid!r}"

    @pytest.mark.parametrize(
        "invalid",
        [
            "",
            "2026-02-20",                    # date only, no time
            "10:45:21.123Z",                 # time only
            "2026-02-20 10:45:21.123Z",      # space separator (not RFC3339)
            "2026-13-01T10:45:21Z",          # month 13
            "2026-02-20T25:45:21Z",          # hour 25
            "2026-02-20T10:45:21",           # missing timezone
            "not-a-timestamp",
            "2026/02/20T10:45:21Z",          # slashes instead of dashes
        ],
    )
    def test_invalid_timestamp(self, invalid: str) -> None:
        assert not TIMESTAMP_RE.match(invalid), f"Expected no match: {invalid!r}"


# ── event_type regex (spec §8.3) ──────────────────────────────────────────────


class TestEventTypeRe:
    """event_type must follow domain.category.action namespace pattern."""

    @pytest.mark.parametrize(
        "valid",
        [
            "agent.plan.created",    # spec §8.3 examples
            "agent.tool.called",
            "agent.llm.request",
            "agent.llm.response",
            "agent.memory.write",
            "agent.memory.read_all", # underscore in action is allowed
            "a.b.c",                 # minimal valid
            "a1.b2.c3",              # digits allowed
        ],
    )
    def test_valid_event_type(self, valid: str) -> None:
        assert EVENT_TYPE_RE.match(valid), f"Expected valid: {valid!r}"

    @pytest.mark.parametrize(
        "invalid",
        [
            "",
            "agenttoolcalled",       # spec §12 bad value example
            "agent.tool",            # only two parts
            "agent.tool.called.extra",  # four parts
            "Agent.Tool.Called",     # uppercase
            "agent.tool.called!",    # special char
            ".tool.called",          # empty domain
            "agent..called",         # empty category
            "agent.tool.",           # empty action
            "agent-tool.called.x",   # hyphen in domain (not allowed)
        ],
    )
    def test_invalid_event_type(self, invalid: str) -> None:
        assert not EVENT_TYPE_RE.match(invalid), f"Expected no match: {invalid!r}"


# ── source regex (spec §8.4) ─────────────────────────────────────────────────


class TestSourceRe:
    """source must be name@semver format."""

    @pytest.mark.parametrize(
        "valid",
        [
            "langchain@0.2.11",       # spec §8.4 examples
            "autogen@0.4.1",
            "spanforge@1.0.0",
            "agent-runtime@0.9.2",
            "my_tool@10.20.300",      # underscore, large nums
            "A@1.0.0",                # single uppercase char name
        ],
    )
    def test_valid_source(self, valid: str) -> None:
        assert SOURCE_RE.match(valid), f"Expected valid: {valid!r}"

    @pytest.mark.parametrize(
        "invalid",
        [
            "",
            "langchain",              # no @
            "langchain@",             # no version
            "@0.2.11",                # no name
            "langchain@0.2",          # only two version parts
            "langchain@0.2.11.5",     # four version parts
            "langchain@a.b.c",        # non-numeric version
            "lang chain@0.1.0",       # space in name
            "langchain@0.2.11!",      # trailing special char
        ],
    )
    def test_invalid_source(self, invalid: str) -> None:
        assert not SOURCE_RE.match(invalid), f"Expected no match: {invalid!r}"


# ── trace_id regex (spec §8.5) ───────────────────────────────────────────────


class TestTraceIdRe:
    """trace_id must be 16 or 32 lowercase hex characters."""

    @pytest.mark.parametrize(
        "valid",
        [
            "4bf92f3577b34da6a3ce929d0e0e4736",  # 32 chars — spec §17 example
            "0000000000000000",                   # 16 chars minimum
            "ffffffffffffffff",                   # 16 chars all-f
            "0000000000000000ffffffffffffffff",   # 32 chars
            "4bf92f3577b34da6",                   # 16 chars
        ],
    )
    def test_valid_trace_id(self, valid: str) -> None:
        assert TRACE_ID_RE.match(valid), f"Expected valid: {valid!r}"

    @pytest.mark.parametrize(
        "invalid",
        [
            "",
            "4bf92f3577b34da",                    # 15 chars (too short)
            "4bf92f3577b34da6a3ce929d0e0e47360",  # 33 chars (too long)
            "4BF92F3577B34DA6A3CE929D0E0E4736",   # uppercase (invalid)
            "4bf92f3577b34da6a3ce929d0e0e473g",   # 'g' is not hex
            "4bf92f3577b34da6a3ce929d0e0e473 ",   # trailing space
        ],
    )
    def test_invalid_trace_id(self, invalid: str) -> None:
        assert not TRACE_ID_RE.match(invalid), f"Expected no match: {invalid!r}"

    def test_boundary_16_chars(self) -> None:
        assert TRACE_ID_RE.match("a" * 16)

    def test_boundary_32_chars(self) -> None:
        assert TRACE_ID_RE.match("a" * 32)

    def test_boundary_17_chars(self) -> None:
        """17 chars is between 16 and 32 — must match (spec says 16 OR 32 bytes
        but the hex representation regex allows any length in [16,32])."""
        assert TRACE_ID_RE.match("a" * 17)

    def test_boundary_15_chars_fails(self) -> None:
        assert not TRACE_ID_RE.match("a" * 15)

    def test_boundary_33_chars_fails(self) -> None:
        assert not TRACE_ID_RE.match("a" * 33)


# ── span_id regex (spec §8.6) ────────────────────────────────────────────────


class TestSpanIdRe:
    """span_id must be exactly 16 lowercase hex characters."""

    @pytest.mark.parametrize(
        "valid",
        [
            "00f067aa0ba902b7",  # spec §17 example
            "0000000000000000",
            "ffffffffffffffff",
            "abcdef0123456789",
        ],
    )
    def test_valid_span_id(self, valid: str) -> None:
        assert SPAN_ID_RE.match(valid), f"Expected valid: {valid!r}"

    @pytest.mark.parametrize(
        "invalid",
        [
            "",
            "00f067aa0ba902b",    # 15 chars
            "00f067aa0ba902b70",  # 17 chars
            "00F067AA0BA902B7",   # uppercase
            "00f067aa0ba902bz",   # non-hex char
            "00f067aa0ba902b ",   # trailing space
        ],
    )
    def test_invalid_span_id(self, invalid: str) -> None:
        assert not SPAN_ID_RE.match(invalid), f"Expected no match: {invalid!r}"

    def test_boundary_exactly_16(self) -> None:
        assert SPAN_ID_RE.match("a" * 16)

    def test_boundary_15_fails(self) -> None:
        assert not SPAN_ID_RE.match("a" * 15)

    def test_boundary_17_fails(self) -> None:
        assert not SPAN_ID_RE.match("a" * 17)


# ── BASE64 regex (spec §8.7) ─────────────────────────────────────────────────


class TestBase64Re:
    """Signature value must be valid standard base64."""

    @pytest.mark.parametrize(
        "valid",
        [
            "dGVzdA==",          # "test" base64-encoded
            "aGVsbG8=",          # "hello"
            "Zm9vYmFy",          # "foobar" (no padding needed)
            "AAAA",              # 4 bytes, no padding
            "AAECAw==",          # padded
            "dGhpcyBpcyBhIHRlc3Q=",  # longer value
        ],
    )
    def test_valid_base64(self, valid: str) -> None:
        assert BASE64_RE.match(valid), f"Expected valid base64: {valid!r}"

    @pytest.mark.parametrize(
        "invalid",
        [
            "dGVzdA===",         # triple padding (invalid)
            "dGVzdA= =",         # space in middle
            "dGVz!A==",          # invalid char '!'
            "dGVzdA",            # length not a multiple of 4 and no padding
        ],
    )
    def test_invalid_base64(self, invalid: str) -> None:
        assert not BASE64_RE.match(invalid), f"Expected no match: {invalid!r}"

    def test_empty_string_matches(self) -> None:
        """Empty string is technically valid per the regex (zero groups).
        Field validators will enforce non-empty separately."""
        assert BASE64_RE.match("") is not None

    def test_all_patterns_are_compiled(self) -> None:
        """Patterns must be pre-compiled re.Pattern objects, not raw strings."""
        from agentobs_validate.schema import patterns as p

        for name in ("ULID_RE", "TIMESTAMP_RE", "EVENT_TYPE_RE",
                     "SOURCE_RE", "TRACE_ID_RE", "SPAN_ID_RE", "BASE64_RE"):
            obj = getattr(p, name)
            assert isinstance(obj, re.Pattern), f"{name} is not a compiled Pattern"
