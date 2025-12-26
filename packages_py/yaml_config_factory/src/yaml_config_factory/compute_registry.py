from typing import Callable, Dict, Any, Optional, Awaitable, Union
import inspect
import asyncio

class ContextComputeRegistry:
    """Registry for context compute functions (similar to auth compute pattern)."""

    _startup_resolvers: Dict[str, Callable] = {}
    _request_resolvers: Dict[str, Callable] = {}

    @classmethod
    def register_startup(cls, name: str):
        """Decorator to register a startup-time resolver."""
        def decorator(fn: Callable):
            cls._startup_resolvers[name] = fn
            return fn
        return decorator

    @classmethod
    def register_request(cls, name: str):
        """Decorator to register a request-time resolver."""
        def decorator(fn: Callable):
            cls._request_resolvers[name] = fn
            return fn
        return decorator

    @classmethod
    async def resolve(cls, name: str, context: Dict[str, Any], request: Any = None) -> Any:
        """Resolve a value using registered function."""
        # Try request resolver first
        if name in cls._request_resolvers:
            fn = cls._request_resolvers[name]
            # Check if function accepts request arg
            sig = inspect.signature(fn)
            if 'request' in sig.parameters:
                result = fn(context, request=request)
            else:
                result = fn(context)
            
            if inspect.isawaitable(result):
                return await result
            return result

        # Then startup resolver
        if name in cls._startup_resolvers:
            fn = cls._startup_resolvers[name]
            result = fn(context)
            if inspect.isawaitable(result):
                return await result
            return result

        raise ValueError(f"No resolver registered for '{name}'")

    @classmethod
    def has_resolver(cls, name: str) -> bool:
        return name in cls._startup_resolvers or name in cls._request_resolvers

# Convenience decorators
register_startup = ContextComputeRegistry.register_startup
register_request = ContextComputeRegistry.register_request
