from typing import Any, Dict, Set, Optional
from runtime_template_resolver import resolve
from copy import deepcopy
from .compute_registry import ContextComputeRegistry
import re

# Pattern to detect template types
TEMPLATE_PATTERN = re.compile(r'\{\{[^}]+\}\}|\$\.[a-zA-Z_]')
FUNCTION_PATTERN = re.compile(r'^\{\{fn:([a-zA-Z_][a-zA-Z0-9_]*)\}\}$')

def has_template(value: str) -> bool:
    if not value:
        return False
    return bool(TEMPLATE_PATTERN.search(value))

def is_function_ref(value: str) -> tuple[bool, str]:
    """Check if value is a function reference. Returns (is_fn, resolver_name)."""
    if not value:
        return False, ""
    match = FUNCTION_PATTERN.match(value.strip())
    if match:
        return True, match.group(1)
    return False, ""

async def resolve_value(value: str, context: Dict[str, Any], request: Any = None) -> Any:
    """Resolve a single value - either function or template."""
    is_fn, resolver_name = is_function_ref(value)
    if is_fn:
        # Function resolution via registry
        return await ContextComputeRegistry.resolve(resolver_name, context, request)
    elif has_template(value):
        # Template resolution via runtime-template-resolver
        return resolve(value, context)
    return value

async def resolve_deep(obj: Any, context: Dict[str, Any], request: Any = None, visited: Optional[Set[int]] = None) -> Any:
    """Recursively resolve templates and functions in nested objects."""
    if visited is None:
        visited = set()

    obj_id = id(obj)
    if obj_id in visited:
        return obj

    if isinstance(obj, str):
        return await resolve_value(obj, context, request)

    if isinstance(obj, dict):
        visited.add(obj_id)
        result = {}
        for key, value in obj.items():
            result[key] = await resolve_deep(value, context, request, visited)
        return result

    if isinstance(obj, list):
        visited.add(obj_id)
        # Process list sequentially to preserve order
        items = []
        for item in obj:
            items.append(await resolve_deep(item, context, request, visited))
        return items

    return obj  # Primitives

def deep_merge(base: Dict, overlay: Dict) -> Dict:
    """Deep merge overlay into base, overlay values take precedence."""
    # Start with a deep copy of base to avoid mutation
    result = deepcopy(base)
    
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
            
    return result

class ContextResolver:
    """Resolves templates and functions from overwrite_from_context meta key."""

    def __init__(self, context: Dict[str, Any], request: Any = None):
        self.context = context
        self.request = request

    async def apply_context_overwrite(self, config: Dict[str, Any], context_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply overwrite_from_context to config.

        Args:
            config: The config dict (after overwrite_from_env applied)
            context_meta: The overwrite_from_context meta key value

        Returns:
            Config with templates/functions resolved and merged
        """
        if not context_meta:
            return config

        # Resolve all templates and functions in the context_meta
        resolved_overlay = await resolve_deep(context_meta, self.context, self.request)

        # Deep merge resolved values into config
        return deep_merge(config, resolved_overlay)
