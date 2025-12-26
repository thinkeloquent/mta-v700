from typing import Any, Dict
from .patterns import PATTERNS
from .resolver import resolve_path
from .coercion import coerce_to_string

def resolve(template: str, context: Dict[str, Any]) -> str:
    """
    Resolve placeholders in template string using context.
    Supports {{path}} and $.path syntax.
    """
    if not template:
        return ""
        
    result = template
    
    # Process mustache syntax {{path}}
    def replace_mustache(match):
        path = match.group(1).strip()
        default_val = match.group(2)
        val = resolve_path(context, path)
        if val is None:
            return default_val if default_val is not None else match.group(0)
        return coerce_to_string(val)
        
    result = PATTERNS["MUSTACHE"].sub(replace_mustache, result)
    
    # Process dot path syntax $.path
    def replace_dot(match):
        path = match.group(1)
        val = resolve_path(context, path)
        if val is None:
            return match.group(0) # Keep literal if not found (simple default for now)
        return coerce_to_string(val)
        
    result = PATTERNS["DOT_PATH"].sub(replace_dot, result)
    
    # Restore escaped placeholders
    result = PATTERNS["ESCAPED_DOT"].sub("$.", result)
    result = PATTERNS["ESCAPED_MUSTACHE"].sub("{{", result)
    
    return result
