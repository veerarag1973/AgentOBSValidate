"""Per-field validator functions for the AgentOBS event envelope.

Each public function accepts the raw value extracted from an event dict
(``None`` when the field is absent) and returns a ``list[ValidationError]``.
An empty list means the field is valid.

Processing is non-short-circuit: all errors for a field are collected and
returned so callers see the full picture in one pass.

Spec reference: §8 Field Specifications, §9 Validation Process.
"""

from __future__ import annotations

from typing import Any

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
from agentobs_validate.schema.patterns import (
    BASE64_RE,
    EVENT_TYPE_RE,
    SOURCE_RE,
    SPAN_ID_RE,
    TIMESTAMP_RE,
    TRACE_ID_RE,
    ULID_RE,
)


def validate_event_id(value: Any) -> list[ValidationError]:
    """Validate the ``event_id`` envelope field (spec §8.1).

    Must be present and a valid 26-character Crockford Base32 ULID.

    Error codes emitted:
    - ``MISSING_EVENT_ID`` — field absent or ``None``
    - ``INVALID_ULID``     — present but fails ULID regex or is not a string
    """
    if value is None:
        return [
            ValidationError(
                code=MISSING_EVENT_ID,
                field=FIELD_EVENT_ID,
                message="event_id is required",
                value=None,
            )
        ]
    if not isinstance(value, str) or not ULID_RE.match(value):
        return [
            ValidationError(
                code=INVALID_ULID,
                field=FIELD_EVENT_ID,
                message="event_id must be a valid ULID (26 Crockford Base32 characters)",
                value=value,
            )
        ]
    return []


def validate_timestamp(value: Any) -> list[ValidationError]:
    """Validate the ``timestamp`` envelope field (spec §8.2).

    Must be present and an RFC3339/ISO8601 datetime string.

    Error codes emitted:
    - ``MISSING_TIMESTAMP``  — field absent or ``None``
    - ``INVALID_TIMESTAMP``  — present but fails RFC3339 regex or is not a string
    """
    if value is None:
        return [
            ValidationError(
                code=MISSING_TIMESTAMP,
                field=FIELD_TIMESTAMP,
                message="timestamp is required",
                value=None,
            )
        ]
    if not isinstance(value, str) or not TIMESTAMP_RE.match(value):
        return [
            ValidationError(
                code=INVALID_TIMESTAMP,
                field=FIELD_TIMESTAMP,
                message="timestamp must be an RFC3339/ISO8601 datetime string (e.g. 2026-02-20T10:45:21.123Z)",
                value=value,
            )
        ]
    return []


def validate_event_type(value: Any) -> list[ValidationError]:
    """Validate the ``event_type`` envelope field (spec §8.3).

    Must be present, a string, and follow the ``domain.category.action``
    namespace pattern.

    Error codes emitted:
    - ``INVALID_EVENT_TYPE`` — field absent or not a string
    - ``INVALID_NAMESPACE``  — present string but fails namespace regex
    """
    if value is None or not isinstance(value, str):
        return [
            ValidationError(
                code=INVALID_EVENT_TYPE,
                field=FIELD_EVENT_TYPE,
                message="event_type is required and must be a string",
                value=value,
            )
        ]
    if not EVENT_TYPE_RE.match(value):
        return [
            ValidationError(
                code=INVALID_NAMESPACE,
                field=FIELD_EVENT_TYPE,
                message="event_type must follow the pattern domain.category.action (e.g. agent.tool.called)",
                value=value,
            )
        ]
    return []


def validate_source(value: Any) -> list[ValidationError]:
    """Validate the ``source`` envelope field (spec §8.4).

    Must be present and follow the ``name@major.minor.patch`` format.

    Error codes emitted:
    - ``MISSING_SOURCE``        — field absent or ``None``
    - ``INVALID_SOURCE_FORMAT`` — present but fails source regex or is not a string
    """
    if value is None:
        return [
            ValidationError(
                code=MISSING_SOURCE,
                field=FIELD_SOURCE,
                message="source is required",
                value=None,
            )
        ]
    if not isinstance(value, str) or not SOURCE_RE.match(value):
        return [
            ValidationError(
                code=INVALID_SOURCE_FORMAT,
                field=FIELD_SOURCE,
                message="source must follow the format name@major.minor.patch (e.g. langchain@0.2.11)",
                value=value,
            )
        ]
    return []


def validate_trace_id(value: Any) -> list[ValidationError]:
    """Validate the ``trace_id`` envelope field (spec §8.5).

    Must be present and consist of 16 or 32 lowercase hexadecimal characters.

    Error codes emitted:
    - ``INVALID_TRACE_ID`` — field absent, not a string, or fails hex regex
    """
    if value is None or not isinstance(value, str) or not TRACE_ID_RE.match(value):
        return [
            ValidationError(
                code=INVALID_TRACE_ID,
                field=FIELD_TRACE_ID,
                message="trace_id must be 16 or 32 lowercase hexadecimal characters",
                value=value,
            )
        ]
    return []


def validate_span_id(value: Any) -> list[ValidationError]:
    """Validate the ``span_id`` envelope field (spec §8.6).

    Must be present and consist of exactly 16 lowercase hexadecimal characters.

    Error codes emitted:
    - ``INVALID_SPAN_ID`` — field absent, not a string, or fails hex regex
    """
    if value is None or not isinstance(value, str) or not SPAN_ID_RE.match(value):
        return [
            ValidationError(
                code=INVALID_SPAN_ID,
                field=FIELD_SPAN_ID,
                message="span_id must be exactly 16 lowercase hexadecimal characters",
                value=value,
            )
        ]
    return []


def validate_signature(value: Any) -> list[ValidationError]:
    """Validate the optional ``signature`` envelope field (spec §8.7).

    If absent (``None``), the field is skipped and no errors are emitted.
    When present, the sub-fields ``algorithm`` and ``value`` are validated.

    Note: This phase validates *structure only*. Cryptographic HMAC
    verification against a key is a roadmap item (spec §18).

    Error codes emitted:
    - ``UNSUPPORTED_ALGORITHM`` — ``algorithm`` absent or not ``HMAC-SHA256``
    - ``INVALID_SIGNATURE``     — ``value`` absent, not a string, empty, or
                                  not valid standard base64
    """
    if value is None:
        return []

    errors: list[ValidationError] = []

    if not isinstance(value, dict):
        # Cannot inspect sub-fields — emit both structural errors
        return [
            ValidationError(
                code=UNSUPPORTED_ALGORITHM,
                field=FIELD_SIG_ALGORITHM,
                message=f"signature.algorithm must be {SUPPORTED_SIGNATURE_ALGORITHM}",
                value=None,
            ),
            ValidationError(
                code=INVALID_SIGNATURE,
                field=FIELD_SIG_VALUE,
                message="signature.value must be a valid non-empty base64-encoded string",
                value=None,
            ),
        ]

    # Validate algorithm sub-field
    algorithm = value.get(FIELD_SIG_ALGORITHM)
    if algorithm != SUPPORTED_SIGNATURE_ALGORITHM:
        errors.append(
            ValidationError(
                code=UNSUPPORTED_ALGORITHM,
                field=FIELD_SIG_ALGORITHM,
                message=f"signature.algorithm must be {SUPPORTED_SIGNATURE_ALGORITHM}",
                value=algorithm,
            )
        )

    # Validate value sub-field (must be non-empty standard base64)
    sig_value = value.get(FIELD_SIG_VALUE)
    if (
        not isinstance(sig_value, str)
        or not sig_value
        or not BASE64_RE.match(sig_value)
    ):
        errors.append(
            ValidationError(
                code=INVALID_SIGNATURE,
                field=FIELD_SIG_VALUE,
                message="signature.value must be a valid non-empty base64-encoded string",
                value=sig_value,
            )
        )

    return errors
