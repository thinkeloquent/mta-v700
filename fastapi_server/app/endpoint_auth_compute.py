"""
Endpoint Auth Compute Registry.

This file is the entry point for registering custom compute functions for
authentication token resolution.

Usage:
    from fetch_auth_config import register_startup, register_request
    from fastapi import Request

    @register_startup("my_custom_provider")
    async def resolve_my_provider_startup() -> str:
        # Compute token at startup (e.g. fetch from secret manager)
        return "my-startup-token"

    @register_request("my_request_provider")
    async def resolve_my_provider_request(request: Request) -> str:
        # Compute token per request (e.g. extract from header)
        return request.headers.get("X-Custom-Token")
"""

from fetch_auth_config import register_startup, register_request
# from fastapi import Request  # Uncomment if using request resolvers
