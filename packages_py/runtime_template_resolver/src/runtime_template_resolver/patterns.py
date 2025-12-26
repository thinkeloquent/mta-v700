import re

PATTERNS = {
    # $.path.to.value
    "DOT_PATH": re.compile(r'\$\.([a-zA-Z_]\w*(?:\.\w+|\[\d+\]|\["[^"]+"\]|\[\'[^ \']+\'\])*)'),

    # {{path.to.value}} or {{path|"default"}}
    "MUSTACHE": re.compile(r'\{\{([^}|]+)(?:\|"([^"]*)")?\}\}'),

    # Escaped variants
    "ESCAPED_DOT": re.compile(r'\\\$\.'),
    "ESCAPED_MUSTACHE": re.compile(r'\\\{\{'),
}
