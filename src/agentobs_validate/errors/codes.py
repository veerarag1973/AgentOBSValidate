"""Machine-readable error code constants for AgentOBS validation.

All codes correspond 1:1 with spec §8 field error definitions.
Using string constants (not Enum) keeps serialisation trivial and avoids
round-trip conversion in JSON output.

Spec reference: §8.1–§8.7, §12 Error Object Schema.
"""

from __future__ import annotations

from typing import Final

# ── event_id (spec §8.1) ─────────────────────────────────────────────────────
MISSING_EVENT_ID: Final[str] = "MISSING_EVENT_ID"
INVALID_ULID: Final[str] = "INVALID_ULID"

# ── timestamp (spec §8.2) ────────────────────────────────────────────────────
MISSING_TIMESTAMP: Final[str] = "MISSING_TIMESTAMP"
INVALID_TIMESTAMP: Final[str] = "INVALID_TIMESTAMP"

# ── event_type (spec §8.3) ───────────────────────────────────────────────────
INVALID_EVENT_TYPE: Final[str] = "INVALID_EVENT_TYPE"
INVALID_NAMESPACE: Final[str] = "INVALID_NAMESPACE"

# ── source (spec §8.4) ───────────────────────────────────────────────────────
MISSING_SOURCE: Final[str] = "MISSING_SOURCE"
INVALID_SOURCE_FORMAT: Final[str] = "INVALID_SOURCE_FORMAT"

# ── trace_id (spec §8.5) ─────────────────────────────────────────────────────
INVALID_TRACE_ID: Final[str] = "INVALID_TRACE_ID"

# ── span_id (spec §8.6) ──────────────────────────────────────────────────────
INVALID_SPAN_ID: Final[str] = "INVALID_SPAN_ID"

# ── signature (spec §8.7) ────────────────────────────────────────────────────
INVALID_SIGNATURE: Final[str] = "INVALID_SIGNATURE"
UNSUPPORTED_ALGORITHM: Final[str] = "UNSUPPORTED_ALGORITHM"
SIGNATURE_MISMATCH: Final[str] = "SIGNATURE_MISMATCH"

# ── Complete catalog for programmatic use ─────────────────────────────────────
ALL_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        MISSING_EVENT_ID,
        INVALID_ULID,
        MISSING_TIMESTAMP,
        INVALID_TIMESTAMP,
        INVALID_EVENT_TYPE,
        INVALID_NAMESPACE,
        MISSING_SOURCE,
        INVALID_SOURCE_FORMAT,
        INVALID_TRACE_ID,
        INVALID_SPAN_ID,
        INVALID_SIGNATURE,
        UNSUPPORTED_ALGORITHM,
        SIGNATURE_MISMATCH,
    }
)
