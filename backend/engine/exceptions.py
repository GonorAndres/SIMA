"""
Actuarial Exception Hierarchy - Validation Layer
=================================================

Central, domain-aware exceptions for the SIMA actuarial engine.

These replace raw ``KeyError`` / ``ValueError``泄漏 at engine boundaries with
structured errors that carry the *actuarial* reason a computation failed,
so the API layer can map them to clean 422 responses.

Design:
-------
- ``ActuarialError`` -- base for all engine domain errors.
- ``ActuarialValidationError`` -- an input violated a documented actuarial rule.
- ``ActuarialComputationError`` -- inputs were individually valid but a
  computation could not be performed (e.g. degenerate annuity denominator).

Every error carries three optional structured fields:
    - ``field``:       the offending input name (may be ``None`` for cross-field).
    - ``constraint``:  human-readable rule that was violated.
    - ``message``:     user-facing explanation.
"""


class ActuarialError(Exception):
    """Base class for all actuarial-engine domain errors."""

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        constraint: str | None = None,
    ) -> None:
        self.message = message
        self.field = field
        self.constraint = constraint
        super().__init__(self._render())

    def _render(self) -> str:
        parts = [self.message]
        if self.field is not None:
            parts.append(f"field={self.field}")
        if self.constraint is not None:
            parts.append(f"constraint={self.constraint}")
        return " | ".join(parts)

    def to_dict(self) -> dict[str, object]:
        """Structured representation suitable for JSON API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "field": self.field,
            "constraint": self.constraint,
        }


class ActuarialValidationError(ActuarialError):
    """An input value violated a documented actuarial validation rule."""

    pass


class ActuarialComputationError(ActuarialError):
    """
    Inputs were individually valid but a computation cannot be performed.

    Examples: an annuity-due denominator that collapses to zero, an
    ill-conditioned graduation system, etc.
    """

    pass


class DataQualityError(ActuarialError):
    """A loaded data file failed a schema or quality check."""

    pass
