from typing import Any
from .path_parser import parse_path

class SecurityError(Exception):
    pass

def resolve_path(obj: Any, path: str) -> Any:
    """
    Safely resolve a value from a nested object using a path string.
    Does not use eval(). Prevents access to private attributes (starting with _).
    """
    segments = parse_path(path)
    current = obj

    for segment in segments:
        if current is None:
            return None

        # Prevent attribute injection/private access
        if segment.startswith('_'):
             raise SecurityError(f"Unsafe path segment: {segment}")

        if isinstance(current, dict):
            current = current.get(segment)
        elif isinstance(current, (list, tuple)):
            if segment.isdigit():
                idx = int(segment)
                current = current[idx] if idx < len(current) else None
            else:
                return None
        elif hasattr(current, segment):
            current = getattr(current, segment)
        else:
            return None

    return current
