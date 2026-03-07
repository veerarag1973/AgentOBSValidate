"""ValidationContext — shared configuration passed through the validation pipeline.

Carries per-run settings such as OTel mode, schema version, and the optional
HMAC key used for signature verification.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Import the single source of truth for supported versions.
from agentobs_validate.schema.json_schema import SUPPORTED_VERSIONS as SUPPORTED_SCHEMA_VERSIONS

__all__ = ["ValidationContext", "SUPPORTED_SCHEMA_VERSIONS"]


@dataclass
class ValidationContext:
    """Configuration for a single validation run.

    Attributes
    ----------
    otel_mode:
        When ``True``, camelCase field-name aliases defined by the W3C
        Trace Context / OpenTelemetry conventions are accepted in addition
        to the canonical AgentOBS snake_case names.
    schema_version:
        The AgentOBS schema version to validate against.  Must be one of
        :data:`SUPPORTED_SCHEMA_VERSIONS`.  Defaults to ``"0.1"``.
    key_bytes:
        Raw HMAC-SHA256 signing key.  When provided, events that carry a
        ``signature`` block will have their digest cryptographically
        verified against this key.  ``None`` means structural-only
        validation (spec §8.7 Phase 8 behaviour).
    """

    otel_mode: bool = False
    schema_version: str = "0.1"
    key_bytes: bytes | None = field(default=None, repr=False)
