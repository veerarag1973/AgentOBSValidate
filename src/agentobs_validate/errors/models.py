"""ValidationError dataclass — the single error unit emitted by every validator.

Matches the Error Object Schema defined in spec §12.

Fields
------
code    : machine-readable error code (from errors.codes)
field   : the offending envelope field name (from schema.fields)
message : human-readable explanation
value   : the raw invalid value that triggered the error, or None when the
          field is absent entirely
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ValidationError:
    """A single field-level validation failure.

    Immutable and hashable so it can be safely stored in sets or used as a
    dict key if needed.

    Note: ``slots=True`` is available from Python 3.10+.  We target 3.9+
    so slots are omitted here; the memory cost is acceptable at this scale.

    Spec reference: §12 Error Object Schema.
    """

    code: str
    field: str
    message: str
    value: Any = field(default=None, hash=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict matching spec §12.

        ``value`` is always included so consumers can inspect what was
        received, including ``None`` for missing fields.
        """
        return {
            "code": self.code,
            "field": self.field,
            "message": self.message,
            "value": self.value,
        }
