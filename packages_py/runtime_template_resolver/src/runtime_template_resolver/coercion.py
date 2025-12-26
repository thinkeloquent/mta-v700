from typing import Any
import json

def coerce_to_string(value: Any) -> str:
    """Convert value to string for template replacement."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)
