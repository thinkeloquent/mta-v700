"""
Sensitive Value Detection and Masking
"""
import os
import re
from typing import Any
from .logger import get_log_level

SENSITIVE_KEY_PATTERNS = [
    re.compile(r'KEY', re.IGNORECASE),
    re.compile(r'SECRET', re.IGNORECASE),
    re.compile(r'PASSWORD', re.IGNORECASE),
    re.compile(r'TOKEN', re.IGNORECASE),
    re.compile(r'CREDENTIAL', re.IGNORECASE),
    re.compile(r'AUTH', re.IGNORECASE),
    re.compile(r'PRIVATE', re.IGNORECASE)
]

SENSITIVE_VALUE_PREFIXES = [
    'sk-', 'pk-', 'Bearer ', 'Basic ', 'eyJ'
]

_log_mask = True
if os.getenv('VAULT_FILE_LOG_MASK', '').lower() == 'false':
    _log_mask = False

def set_log_mask(enabled: bool) -> None:
    global _log_mask
    _log_mask = enabled

def is_sensitive_key(key: str) -> bool:
    return any(p.search(key) for p in SENSITIVE_KEY_PATTERNS)

def is_sensitive_value(value: str) -> bool:
    if not value:
        return False
    return any(value.startswith(p) for p in SENSITIVE_VALUE_PREFIXES)

def mask_value(key: str, value: Any) -> str:
    if not _log_mask:
        return str(value)
    
    # Trace level check - similar to TS implementation considerations
    # For now, relying on explicit check against _log_mask
    
    val_str = str(value)
    if not val_str:
        return val_str

    if is_sensitive_key(key) or is_sensitive_value(val_str):
        return '[REDACTED]'

    return val_str
