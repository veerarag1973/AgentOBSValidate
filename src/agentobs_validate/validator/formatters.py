"""Output formatters for the AgentOBS event validator.

Spec reference:
  §10  Human Output Format   (default CLI output)
  §11  JSON Output Format    (--json flag)
  §12  Error Object Schema
"""

from __future__ import annotations

import json

from agentobs_validate.validator.results import StreamResult

# Separator line used in the human summary block (spec §10)
_SUMMARY_SEPARATOR = "------"


def format_human(result: StreamResult) -> str:
    """Return the human-readable validation report (spec §10).

    Layout::

        ✔ Event 1  valid
        ✔ Event 2  valid
        ✖ Event 3  INVALID_ULID
        ✖ Event 4  INVALID_EVENT_TYPE INVALID_NAMESPACE

        Summary
        ------
        events_checked: 4
        valid: 2
        invalid: 2

    Multiple error codes for a single event are joined with a single space.

    Parameters
    ----------
    result:
        The :class:`~agentobs_validate.validator.results.StreamResult` to format.

    Returns
    -------
    str
        The complete report as a single string (no trailing newline).
    """
    lines: list[str] = []

    for event in result.events:
        if event.status == "pass":
            lines.append(f"\u2714 Event {event.index}  valid")
        else:
            codes = " ".join(e.code for e in event.errors)
            lines.append(f"\u2716 Event {event.index}  {codes}")

    lines.append("")
    lines.append("Summary")
    lines.append(_SUMMARY_SEPARATOR)
    lines.append(f"events_checked: {result.events_checked}")
    lines.append(f"valid: {result.valid}")
    lines.append(f"invalid: {result.invalid}")

    return "\n".join(lines)


def format_json(result: StreamResult) -> str:
    """Return the machine-readable JSON validation report (spec §11).

    Structure::

        {
          "summary": {
            "events_checked": 4,
            "valid": 2,
            "invalid": 2
          },
          "events": [
            {"index": 1, "status": "pass"},
            {"index": 3, "status": "fail", "errors": [...]}
          ]
        }

    Key behaviours (spec §11):
    - ``pass`` events omit the ``errors`` key entirely.
    - ``fail`` events include full error objects per spec §12
      (``code``, ``field``, ``message``, ``value``).
    - Output is formatted with ``indent=2``.

    Parameters
    ----------
    result:
        The :class:`~agentobs_validate.validator.results.StreamResult` to format.

    Returns
    -------
    str
        A ``json.dumps``-formatted string.
    """
    summary = {
        "events_checked": result.events_checked,
        "valid": result.valid,
        "invalid": result.invalid,
    }

    events: list[dict] = []
    for event in result.events:
        ev_dict: dict = {"index": event.index, "status": event.status}
        if event.status == "fail":
            ev_dict["errors"] = [e.to_dict() for e in event.errors]
        events.append(ev_dict)

    return json.dumps({"summary": summary, "events": events}, indent=2)
