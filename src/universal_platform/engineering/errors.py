"""Typed errors for engineering input and model failures."""

class EngineeringError(Exception):
    """Base class for expected engineering-domain errors."""

class DimensionMismatchError(EngineeringError):
    """Raised when quantities with incompatible dimensions are combined."""

class InvalidModelError(EngineeringError):
    """Raised when a model violates its declared contract."""

class SolverError(EngineeringError):
    """Raised when a numerical solve cannot produce a valid result."""
