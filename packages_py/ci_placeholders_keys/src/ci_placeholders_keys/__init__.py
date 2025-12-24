"""
ci_placeholders_keys - Credential key constants, string transformations, and UUID key mapping utilities
"""

# Constants
from .constants import (
    USER_NAME,
    PASS_WORD,
    PASS_KEY,
    SECRET_KEY,
    UPPER_CASE,
    LOWER_CASE,
    SNAKE_CASE,
    KEBAB_CASE,
    CaseType,
)

# String transformations
from .transforms import (
    upper_case,
    lower_case,
    get_key_name,
)

# Key mapping
from .key_mapping import (
    Key01,
    Key02,
    Key03,
    Key04,
    KeyMapping,
    create_key_mapping,
    get_key_value,
    get_mapped_key,
    has_key,
    get_keys,
    get_values,
)

__all__ = [
    # Constants
    'USER_NAME',
    'PASS_WORD',
    'PASS_KEY',
    'SECRET_KEY',
    'UPPER_CASE',
    'LOWER_CASE',
    'SNAKE_CASE',
    'KEBAB_CASE',
    'CaseType',
    # Transforms
    'upper_case',
    'lower_case',
    'get_key_name',
    # Key mapping
    'Key01',
    'Key02',
    'Key03',
    'Key04',
    'KeyMapping',
    'create_key_mapping',
    'get_key_value',
    'get_mapped_key',
    'has_key',
    'get_keys',
    'get_values',
]
