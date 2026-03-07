"""Result dataclasses for the AgentOBS event validator engine.

Spec reference: §9 Validation Process, §10/§11 Output Formats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from agentobs_validate.errors.models import ValidationError


@dataclass
class EventResult:
    """Validation outcome for a single event.

    Attributes
    ----------
    index:
        1-based position of the event in the input (line number for JSONL,
        array index for JSON arrays).
    status:
        ``"pass"`` when *errors* is empty, ``"fail"`` otherwise.
    errors:
        All :class:`~agentobs_validate.errors.models.ValidationError`
        instances found for this event.  Empty list ↔ ``status == "pass"``.
    """

    index: int
    status: Literal["pass", "fail"]
    errors: list[ValidationError] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serialisable representation of this result."""
        return {
            "index": self.index,
            "status": self.status,
            "errors": [e.to_dict() for e in self.errors],
        }


@dataclass
class StreamResult:
    """Aggregated validation outcome for a stream of events.

    Attributes
    ----------
    events_checked:
        Total number of events processed.
    valid:
        Number of events with ``status == "pass"``.
    invalid:
        Number of events with ``status == "fail"``.
    events:
        Ordered list of per-event results (one :class:`EventResult` per
        input event).  The order matches the source document order.
    """

    events_checked: int
    valid: int
    invalid: int
    events: list[EventResult] = field(default_factory=list)
    schema_version: str = "0.1"

    def to_dict(self) -> dict:
        """Return a JSON-serialisable representation of this result."""
        return {
            "schema_version": self.schema_version,
            "events_checked": self.events_checked,
            "valid": self.valid,
            "invalid": self.invalid,
            "events": [e.to_dict() for e in self.events],
        }
