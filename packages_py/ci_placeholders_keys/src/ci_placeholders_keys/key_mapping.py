"""
UUID key mapping system
"""
import uuid
from typing import Optional

# Pre-defined UUID keys for consistent key mapping across applications
Key01 = str(uuid.uuid4())
Key02 = str(uuid.uuid4())
Key03 = str(uuid.uuid4())
Key04 = str(uuid.uuid4())

# Type alias for key mapping
KeyMapping = dict[str, str]


def create_key_mapping(entries: list[tuple[str, str]]) -> KeyMapping:
    """
    Create a key mapping from entries

    Example:
        >>> create_key_mapping([(Key01, 'user_name'), (Key02, 'password')])
        {Key01: 'user_name', Key02: 'password'}
    """
    return {key: value for key, value in entries}


def get_key_value(mapping: KeyMapping, key_id: str) -> Optional[str]:
    """
    Get value from key mapping (returns None if key not found)
    Similar to lodash .get() behavior
    """
    return mapping.get(key_id)


def get_mapped_key(mapping: KeyMapping, key_id: str, fallback: str = '') -> str:
    """
    Get value from key mapping with fallback

    Args:
        mapping: The key mapping object
        key_id: The key ID to look up
        fallback: Default value if key not found (defaults to empty string)
    """
    return mapping.get(key_id, fallback)


def has_key(mapping: KeyMapping, key_id: str) -> bool:
    """Check if a key exists in the mapping"""
    return key_id in mapping


def get_keys(mapping: KeyMapping) -> list[str]:
    """Get all keys from a mapping"""
    return list(mapping.keys())


def get_values(mapping: KeyMapping) -> list[str]:
    """Get all values from a mapping"""
    return list(mapping.values())
