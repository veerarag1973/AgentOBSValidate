"""Field name constants and envelope metadata for the AgentOBS event schema.

Spec reference: §7 Required Envelope Fields, §8 Field Specifications.
"""

from __future__ import annotations

from typing import Final

# ── Required envelope fields (spec §7) ──────────────────────────────────────

FIELD_EVENT_ID: Final[str] = "event_id"
FIELD_TIMESTAMP: Final[str] = "timestamp"
FIELD_EVENT_TYPE: Final[str] = "event_type"
FIELD_SOURCE: Final[str] = "source"
FIELD_TRACE_ID: Final[str] = "trace_id"
FIELD_SPAN_ID: Final[str] = "span_id"

# ── Optional fields (spec §8.7) ───────────────────────────────────────────────

FIELD_SIGNATURE: Final[str] = "signature"

# Signature sub-fields
FIELD_SIG_ALGORITHM: Final[str] = "algorithm"
FIELD_SIG_KEY_ID: Final[str] = "key_id"
FIELD_SIG_VALUE: Final[str] = "value"

# ── Sets for programmatic access ─────────────────────────────────────────────

REQUIRED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        FIELD_EVENT_ID,
        FIELD_TIMESTAMP,
        FIELD_EVENT_TYPE,
        FIELD_SOURCE,
        FIELD_TRACE_ID,
        FIELD_SPAN_ID,
    }
)

OPTIONAL_FIELDS: Final[frozenset[str]] = frozenset({FIELD_SIGNATURE})

# Ordered sequence used by the validation pipeline (spec §9)
REQUIRED_FIELDS_ORDERED: Final[tuple[str, ...]] = (
    FIELD_EVENT_ID,
    FIELD_TIMESTAMP,
    FIELD_EVENT_TYPE,
    FIELD_SOURCE,
    FIELD_TRACE_ID,
    FIELD_SPAN_ID,
)

# Supported HMAC algorithm (spec §8.7)
SUPPORTED_SIGNATURE_ALGORITHM: Final[str] = "HMAC-SHA256"
