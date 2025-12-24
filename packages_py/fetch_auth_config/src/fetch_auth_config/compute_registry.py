import asyncio
from typing import Dict, Callable, Any, Optional, Union, Awaitable
from .errors import ComputeFunctionNotFoundError, ComputeFunctionError

# Types
StartupComputeFn = Callable[[Any], Union[str, Awaitable[str]]]
RequestComputeFn = Callable[[Any], Union[str, Awaitable[str]]]

class ComputeRegistry:
    _startup_resolvers: Dict[str, StartupComputeFn] = {}
    _request_resolvers: Dict[str, RequestComputeFn] = {}

    @classmethod
    def register_startup(cls, provider_name: str):
        def decorator(fn: StartupComputeFn):
            cls._startup_resolvers[provider_name] = fn
            return fn
        return decorator

    @classmethod
    def register_request(cls, provider_name: str):
        def decorator(fn: RequestComputeFn):
            cls._request_resolvers[provider_name] = fn
            return fn
        return decorator

    @classmethod
    async def resolve_startup(cls, provider_name: str, app: Any) -> str:
        fn = cls._startup_resolvers.get(provider_name)
        if not fn:
            raise ComputeFunctionNotFoundError(provider_name, "startup")
        
        try:
            result = fn(app)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)
        except Exception as e:
            if isinstance(e, ComputeFunctionNotFoundError):
                raise e
            raise ComputeFunctionError(provider_name, e)

    @classmethod
    async def resolve_request(cls, provider_name: str, request: Any) -> str:
        fn = cls._request_resolvers.get(provider_name)
        if not fn:
            raise ComputeFunctionNotFoundError(provider_name, "request")
        
        try:
            result = fn(request)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)
        except Exception as e:
             if isinstance(e, ComputeFunctionNotFoundError):
                raise e
             raise ComputeFunctionError(provider_name, e)

# Module-level aliases for cleaner imports
register_startup = ComputeRegistry.register_startup
register_request = ComputeRegistry.register_request

