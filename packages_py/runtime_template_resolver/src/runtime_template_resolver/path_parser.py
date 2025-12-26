from typing import List
import re

def parse_path(path: str) -> List[str]:
    """
    Parse a path string into segments.
    Supports dot notation (a.b.c) and bracket notation (a['b'][0]).
    """
    if not path:
        return []

    # If simple dot path, split
    if '[' not in path and '"' not in path and "'" not in path:
        return path.split('.')
        
    segments = []
    current = ""
    in_bracket = False
    in_quote = False
    quote_char = None
    
    i = 0
    while i < len(path):
        char = path[i]
        
        if in_quote:
            if char == quote_char:
                in_quote = False
                quote_char = None
                segments.append(current)
                current = ""
            else:
                current += char
        elif in_bracket:
            if char == '"' or char == "'":
                in_quote = True
                quote_char = char
            elif char == ']':
                in_bracket = False
                if current: # was numeric index
                    segments.append(current)
                    current = ""
            else:
                current += char
        else: # Normal state
            if char == '.':
                if current:
                    segments.append(current)
                    current = ""
            elif char == '[':
                if current:
                    segments.append(current)
                    current = ""
                in_bracket = True
            else:
                current += char
        i += 1
        
    if current:
        segments.append(current)
        
    return segments
