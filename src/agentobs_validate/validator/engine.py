"""Core validation engine for the AgentOBS event validator.

Spec reference: §9 Validation Process.
"""

from __future__ import annotations

from typing import Iterator

from agentobs_validate.schema.fields import (
    FIELD_SIGNATURE,
    REQUIRED_FIELDS_ORDERED,
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
from agentobs_validate.validator.results import EventResult, StreamResult

# Map field name → validator function (must match REQUIRED_FIELDS_ORDERED order)
_FIELD_VALIDATORS = {
    REQUIRED_FIELDS_ORDERED[0]: validate_event_id,
    REQUIRED_FIELDS_ORDERED[1]: validate_timestamp,
    REQUIRED_FIELDS_ORDERED[2]: validate_event_type,
    REQUIRED_FIELDS_ORDERED[3]: validate_source,
    REQUIRED_FIELDS_ORDERED[4]: validate_trace_id,
    REQUIRED_FIELDS_ORDERED[5]: validate_span_id,
}


def validate_event(index: int, event: dict) -> EventResult:
    """Validate a single event dict and return an :class:`~agentobs_validate.validator.results.EventResult`.

    All field validators run regardless of prior errors (non-short-circuit).
    The optional ``signature`` field is validated only when it is present in
    *event*.

    Parameters
    ----------
    index:
        1-based position of *event* in the input stream.
    event:
        Raw event dict decoded from JSON.

    Returns
    -------
    EventResult
        ``status="pass"`` when no errors were found; ``"fail"`` otherwise.
    """
    errors = []

    # Run all required-field validators in pipeline order (spec §9)
    for field_name in REQUIRED_FIELDS_ORDERED:
        validator = _FIELD_VALIDATORS[field_name]
        errors.extend(validator(event.get(field_name)))

    # Validate optional signature field only when present (spec §8.7)
    if FIELD_SIGNATURE in event:
        errors.extend(validate_signature(event[FIELD_SIGNATURE]))

    status = "fail" if errors else "pass"
    return EventResult(index=index, status=status, errors=errors)


def validate_stream(events: Iterator[tuple[int, dict]]) -> StreamResult:
    """Validate every event in *events* and return a :class:`~agentobs_validate.validator.results.StreamResult`.

    Parameters
    ----------
    events:
        An iterator that yields ``(position, event_dict)`` pairs, as
        produced by :func:`~agentobs_validate.validator.input_parser.iter_events`.

    Returns
    -------
    StreamResult
        Aggregated counts and per-event results.
    """
    event_results: list[EventResult] = []
    valid = 0
    invalid = 0

    for index, event in events:
        result = validate_event(index, event)
        event_results.append(result)
        if result.status == "pass":
            valid += 1
        else:
            invalid += 1

    return StreamResult(
        events_checked=valid + invalid,
        valid=valid,
        invalid=invalid,
        events=event_results,
    )
