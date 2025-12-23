from enum import Enum

class TokenResolverType(str, Enum):
    """Enumeration of token resolution strategies."""
    STATIC = 'static'
    STARTUP = 'startup'
    REQUEST = 'request'
