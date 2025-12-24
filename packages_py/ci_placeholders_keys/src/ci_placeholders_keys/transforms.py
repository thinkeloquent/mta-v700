"""
String transformation utilities
"""
import re
from .constants import UPPER_CASE, LOWER_CASE, SNAKE_CASE, KEBAB_CASE, CaseType


def upper_case(input_str: str) -> str:
    """
    Convert string to uppercase, removing special characters (keeps alphanumeric and $)

    Example:
        >>> upper_case('$catDog')
        '$CAT DOG'
    """
    # Replace special chars (except $ and space) with space
    result = re.sub(r'[^a-zA-Z0-9$\s]', ' ', input_str)
    # Insert space before uppercase in camelCase
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', result)
    # Convert to uppercase
    result = result.upper()
    # Collapse multiple spaces
    result = re.sub(r'\s+', ' ', result)
    return result.strip()


def lower_case(input_str: str) -> str:
    """
    Convert string to lowercase, removing special characters (keeps alphanumeric and $)

    Example:
        >>> lower_case('$catDog')
        '$cat dog'
    """
    # Replace special chars (except $ and space) with space
    result = re.sub(r'[^a-zA-Z0-9$\s]', ' ', input_str)
    # Insert space before uppercase in camelCase
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', result)
    # Convert to lowercase
    result = result.lower()
    # Collapse multiple spaces
    result = re.sub(r'\s+', ' ', result)
    return result.strip()


def get_key_name(input_str: str, case_type: CaseType = SNAKE_CASE) -> str:
    """
    Normalize string to valid key name format

    - Replaces special characters with underscore (or hyphen for KEBAB_CASE)
    - Removes duplicate separators
    - Applies case transformation

    Examples:
        >>> get_key_name('Cat-Dog', LOWER_CASE)
        'cat_dog'
        >>> get_key_name('Cat--Dog', LOWER_CASE)
        'cat_dog'
        >>> get_key_name('API Key', UPPER_CASE)
        'API_KEY'
    """
    # Trim whitespace
    result = input_str.strip()

    # Insert separator before uppercase letters in camelCase
    result = re.sub(r'([a-z])([A-Z])', r'\1_\2', result)

    # Replace special characters with underscore
    result = re.sub(r'[^a-zA-Z0-9_]', '_', result)

    # Collapse multiple underscores
    result = re.sub(r'_+', '_', result)

    # Remove leading/trailing underscores
    result = result.strip('_')

    # Apply case transformation
    if case_type == UPPER_CASE:
        result = result.upper()
    elif case_type in (LOWER_CASE, SNAKE_CASE):
        result = result.lower()
    elif case_type == KEBAB_CASE:
        result = result.lower().replace('_', '-')

    return result
