"""Validation schemas and custom exceptions."""

class ValidationError(Exception):
    """Raised when validation fails (e.g., malformed YAML)."""
    pass

class ConfigNotInitializedError(Exception):
    """Raised when accessing config before initialize()."""
    pass

class ConfigAlreadyInitializedError(Exception):
    """Raised on second initialize() call."""
    pass

class ComputedKeyNotFoundError(Exception):
    """Raised when get_computed() key doesn't exist."""
    pass

class CircularDependencyError(Exception):
    """Raised when computed functions have circular dependencies."""
    pass
