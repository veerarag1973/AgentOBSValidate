"""JSON Schema export for the AgentOBS event envelope.

Implements the ``--export-schema`` feature (spec §18 roadmap).
Produces a JSON Schema Draft 2020-12 document that describes every
required and optional field in the AgentOBS event envelope.
"""

from __future__ import annotations

import json
from typing import Final

from agentobs_validate.schema.patterns import (
    BASE64_RE,
    EVENT_TYPE_RE,
    SOURCE_RE,
    SPAN_ID_RE,
    TIMESTAMP_RE,
    TRACE_ID_RE,
    ULID_RE,
)

# Versions for which a schema can be exported.
SUPPORTED_VERSIONS: Final[frozenset[str]] = frozenset({"0.1"})

# ---------------------------------------------------------------------------
# Schema document
# ---------------------------------------------------------------------------

_SCHEMA_0_1: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://github.com/veerarag1973/AgentOBSValidate/schema/agentobs-event-0.1.json",
    "title": "AgentOBS Event",
    "description": (
        "A single AgentOBS observability event.  All required envelope fields "
        "must be present and conform to the formats defined in the AgentOBS "
        "specification v0.1 (§7–§8)."
    ),
    "type": "object",
    "required": ["event_id", "timestamp", "event_type", "source", "trace_id", "span_id"],
    "additionalProperties": True,
    "properties": {
        "event_id": {
            "type": "string",
            "description": (
                "ULID identifier for this event.  "
                "26 characters, Crockford Base32 alphabet (spec §8.1)."
            ),
            "pattern": ULID_RE.pattern,
            "examples": ["01HZY7M4YQZB3D0V4K6Z5R9F7A"],
        },
        "timestamp": {
            "type": "string",
            "description": "RFC3339 / ISO8601 UTC timestamp (spec §8.2).",
            "pattern": TIMESTAMP_RE.pattern,
            "examples": ["2026-02-20T10:45:21.123Z"],
        },
        "event_type": {
            "type": "string",
            "description": (
                "Dot-delimited event type following the domain.category.action "
                "namespace pattern (spec §8.3)."
            ),
            "pattern": EVENT_TYPE_RE.pattern,
            "examples": ["agent.tool.called", "agent.llm.requested", "agent.plan.created"],
        },
        "source": {
            "type": "string",
            "description": (
                "Emitting component identifier in name@semver format (spec §8.4)."
            ),
            "pattern": SOURCE_RE.pattern,
            "examples": ["langchain@0.2.11", "spanforge@1.0.0"],
        },
        "trace_id": {
            "type": "string",
            "description": (
                "Distributed trace identifier: exactly 32 lowercase hex characters, "
                "compatible with W3C Trace Context / OpenTelemetry (spec §8.5)."
            ),
            "pattern": TRACE_ID_RE.pattern,
            "examples": ["4bf92f3577b34da6a3ce929d0e0e4736"],
        },
        "span_id": {
            "type": "string",
            "description": (
                "Distributed span identifier: exactly 16 lowercase hex characters, "
                "compatible with W3C Trace Context / OpenTelemetry (spec §8.6)."
            ),
            "pattern": SPAN_ID_RE.pattern,
            "examples": ["00f067aa0ba902b7"],
        },
        "signature": {
            "type": "object",
            "description": (
                "Optional HMAC-SHA256 signature for event integrity verification "
                "(spec §8.7).  When present, all sub-fields are validated."
            ),
            "required": ["algorithm", "value"],
            "additionalProperties": True,
            "properties": {
                "algorithm": {
                    "type": "string",
                    "const": "HMAC-SHA256",
                    "description": "Signing algorithm.  Must be exactly HMAC-SHA256.",
                },
                "key_id": {
                    "type": "string",
                    "description": "Opaque identifier for the signing key (informational).",
                    "examples": ["spanforge-key-1"],
                },
                "value": {
                    "type": "string",
                    "description": "Base64-encoded HMAC-SHA256 digest of the canonical event payload.",
                    "pattern": BASE64_RE.pattern,
                },
            },
        },
    },
}

# Map version string → schema dict
_SCHEMAS: Final[dict[str, dict]] = {"0.1": _SCHEMA_0_1}


def build_json_schema(schema_version: str = "0.1") -> dict:
    """Return the JSON Schema dict for *schema_version*.

    Parameters
    ----------
    schema_version:
        The AgentOBS schema version.  Must be one of
        :data:`SUPPORTED_VERSIONS`.

    Raises
    ------
    ValueError
        If *schema_version* is not in :data:`SUPPORTED_VERSIONS`.
    """
    if schema_version not in SUPPORTED_VERSIONS:
        raise ValueError(
            f"Schema version {schema_version!r} is not supported. "
            f"Supported versions: {', '.join(sorted(SUPPORTED_VERSIONS))}"
        )
    return _SCHEMAS[schema_version]


def export_schema(schema_version: str = "0.1") -> str:
    """Return a formatted JSON Schema string for *schema_version*.

    Parameters
    ----------
    schema_version:
        The AgentOBS schema version to export.

    Returns
    -------
    str
        A ``json.dumps``-formatted JSON Schema document (``indent=2``).
    """
    return json.dumps(build_json_schema(schema_version), indent=2)
