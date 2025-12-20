class RedisConfigError(ValueError):
    """Raised when configuration is invalid."""
    pass

class RedisConnectionError(ConnectionError):
    """Raised when Redis connection fails."""
    pass

class RedisImportError(ImportError):
    """Raised when required dependencies are missing."""
    pass
