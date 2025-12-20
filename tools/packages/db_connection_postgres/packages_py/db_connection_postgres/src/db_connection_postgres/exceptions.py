class DatabaseConfigError(ValueError):
    """Raised when configuration is invalid."""
    pass

class DatabaseConnectionError(RuntimeError):
    """Raised when database connection fails."""
    pass

class DatabaseImportError(ImportError):
    """Raised when required dependencies are missing."""
    pass
