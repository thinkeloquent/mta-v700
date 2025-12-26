"""
Endpoint Context Compute Registry.

This file is the entry point for registering custom compute functions for
context-based template resolution via overwrite_from_context.

Unlike endpoint_auth_compute.py (for auth token resolution), this file
handles dynamic value resolution in YAML config templates using {{fn:name}} syntax.

Usage:
    from yaml_config_factory import register_startup, register_request

    @register_startup("my_startup_resolver")
    def resolve_at_startup(context):
        # context = {env, app, config, request}
        # Runs once when context is built
        return context['env'].get('MY_VALUE', 'default')

    @register_request("my_request_resolver")
    def resolve_per_request(context, request):
        # context = {env, app, config, request}
        # request = FastAPI Request object
        # Runs per request when template is resolved
        return request.headers.get("x-custom-header", "fallback")

YAML usage:
    overwrite_from_context:
      my_value: "{{fn:my_startup_resolver}}"
      custom_header: "{{fn:my_request_resolver}}"
"""

from yaml_config_factory import register_startup, register_request
from fastapi import Request
import os
import uuid
from datetime import datetime


# =============================================================================
# Startup Resolvers (run when context is built at startup)
# =============================================================================

@register_startup("get_build_info")
def resolve_build_info(context):
    """Get build information from environment or config."""
    return {
        "build_id": context['env'].get('BUILD_ID', 'dev-local'),
        "build_time": context['env'].get('BUILD_TIME', datetime.now().isoformat()),
        "git_sha": context['env'].get('GIT_SHA', 'unknown')
    }


@register_startup("get_service_name")
def resolve_service_name(context):
    """Get service name from app config."""
    return context['app'].get('name', 'mta-server')


# =============================================================================
# Request Resolvers (run per-request when template is resolved)
# =============================================================================

@register_request("compute_gemini_v2_token")
def resolve_gemini_v2_token(context, request: Request = None):
    """
    Compute dynamic token for gemini_openai_v2 provider.

    Priority:
    1. X-Gemini-Token header from request
    2. GEMINI_API_KEY from environment
    3. Fallback empty string
    """
    if request:
        # Check for token in request header
        token = request.headers.get("x-gemini-token")
        if token:
            return token

    # Fall back to environment variable
    return context['env'].get('GEMINI_API_KEY', '')


@register_request("compute_request_id")
def resolve_request_id(context, request: Request = None):
    """
    Get or generate a request ID for tracing.

    Uses X-Request-ID header if present, otherwise generates a new UUID.
    """
    if request:
        request_id = request.headers.get("x-request-id")
        if request_id:
            return request_id

    return str(uuid.uuid4())


@register_request("compute_tenant_id")
def resolve_tenant_id(context, request: Request = None):
    """
    Extract tenant ID from request headers or query params.
    """
    if request:
        # Try header first
        tenant_id = request.headers.get("x-tenant-id")
        if tenant_id:
            return tenant_id

        # Then query params
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id

    return "default"


@register_request("compute_user_agent")
def resolve_user_agent(context, request: Request = None):
    """
    Build a custom user agent string including app version.
    """
    app_name = context['app'].get('name', 'MTA-Server')
    app_version = context['app'].get('version', '0.0.0')

    base_ua = f"{app_name}/{app_version}"

    if request:
        client_ua = request.headers.get("user-agent", "")
        if client_ua:
            return f"{base_ua} (via {client_ua})"

    return base_ua
