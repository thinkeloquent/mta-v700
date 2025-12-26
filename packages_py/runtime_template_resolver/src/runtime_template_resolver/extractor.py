from typing import List, Dict, Any
from .patterns import PATTERNS

def extract_placeholders(template: str) -> List[Dict[str, Any]]:
    """Extract all placeholders from a template string."""
    placeholders = []
    
    # Extract mustache placeholders
    for match in PATTERNS["MUSTACHE"].finditer(template):
        placeholders.append({
            "raw": match.group(0),
            "path": match.group(1).strip(),
            "default": match.group(2),
            "start": match.start(),
            "end": match.end(),
            "syntax": "MUSTACHE"
        })
        
    # Extract dot path placeholders
    for match in PATTERNS["DOT_PATH"].finditer(template):
        placeholders.append({
            "raw": match.group(0),
            "path": match.group(1),
            "default": None,
            "start": match.start(),
            "end": match.end(),
            "syntax": "DOT_PATH"
        })
        
    return placeholders
