"""Pre-compiled regular expression patterns for AgentOBS field validation.

All patterns are compiled once at import time for performance (spec §14).

Spec reference: §8.1–§8.7.
"""

from __future__ import annotations

import re
from typing import Final

# ── event_id: ULID (spec §8.1) ───────────────────────────────────────────────
# Crockford Base32 alphabet: 0-9 and A-Z excluding I, L, O, U
# 26 characters exactly.
ULID_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

# ── timestamp: RFC3339 / ISO8601 (spec §8.2) ─────────────────────────────────
# Accepts: YYYY-MM-DDTHH:MM:SS[.fractional]Z
# Fractional seconds are optional. Only UTC (Z suffix) accepted per spec example.
# More lenient offset forms (+HH:MM) are also accepted for real-world compatibility.
TIMESTAMP_RE: Final[re.Pattern[str]] = re.compile(
    r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])"
    r"T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d"
    r"(?:\.\d+)?"
    r"(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
)

# ── event_type: domain.category.action namespace (spec §8.3) ─────────────────
EVENT_TYPE_RE: Final[re.Pattern[str]] = re.compile(
    r"^[a-z0-9]+\.[a-z0-9]+\.[a-z0-9_]+$"
)

# ── source: name@semver (spec §8.4) ──────────────────────────────────────────
SOURCE_RE: Final[re.Pattern[str]] = re.compile(
    r"^[a-zA-Z0-9\-_]+@[0-9]+\.[0-9]+\.[0-9]+$"
)

# ── trace_id: 16 or 32 lowercase hex chars (spec §8.5) ───────────────────────
TRACE_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{16,32}$")

# ── span_id: exactly 16 lowercase hex chars (spec §8.6) ──────────────────────
SPAN_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{16}$")

# ── signature.value: Base64 (spec §8.7) ──────────────────────────────────────
# Standard base64 alphabet with optional padding.  Does not accept URL-safe
# variants intentionally — spec only references standard base64.
BASE64_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$"
)
