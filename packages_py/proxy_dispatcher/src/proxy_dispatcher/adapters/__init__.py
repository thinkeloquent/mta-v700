"""
Adapter registry.
"""
import logging
from typing import Dict, Type
from .base import BaseAdapter
from .adapter_httpx import HttpxAdapter

logger = logging.getLogger(__name__)

_adapters: Dict[str, Type[BaseAdapter]] = {}

def register_adapter(adapter_cls: Type[BaseAdapter]) -> None:
    """Register an adapter class."""
    # Instantiating to get the name property effectively requires the class to be instantiated or property allows class access
    # Easier to just instantiate temporarily or make name a class property.
    # For now, let's just make an instance.
    try:
        instance = adapter_cls()
        name = instance.name
        _adapters[name] = adapter_cls
        logger.debug(f"Registered adapter: {name}")
    except Exception as e:
        logger.error(f"Failed to register adapter {adapter_cls}: {e}")

def get_adapter(name: str) -> BaseAdapter:
    """Get an adapter instance by name."""
    if name not in _adapters:
        raise KeyError(f"Adapter '{name}' not found. Available: {list(_adapters.keys())}")
    return _adapters[name]()

# Register default adapters
register_adapter(HttpxAdapter)

__all__ = ["BaseAdapter", "HttpxAdapter", "register_adapter", "get_adapter"]
