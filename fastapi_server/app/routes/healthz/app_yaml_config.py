"""AppYamlConfig healthz routes."""

from fastapi import APIRouter, HTTPException
from app_yaml_config import AppYamlConfig, get_provider, get_service, get_storage
from fetch_auth_config import fetch_auth_config, AuthConfig
from fetch_auth_encoding import encode_auth

def _build_credentials(auth_config: AuthConfig) -> dict:
    """Build credentials dict for encode_auth from AuthConfig."""
    creds = {}
    if auth_config.token:
        creds['token'] = auth_config.token
    if auth_config.username:
        creds['username'] = auth_config.username
    if auth_config.password:
        creds['password'] = auth_config.password
    if auth_config.email:
        creds['email'] = auth_config.email
    if auth_config.header_name:
        creds['header_key'] = auth_config.header_name
    if auth_config.header_value:
        creds['header_value'] = auth_config.header_value
    return creds

def _mask_value(value: str, visible_chars: int = 20) -> str:
    """Mask a secret value for safe display."""
    if not value:
        return None
    if len(value) <= visible_chars:
        return "****"
    return f"{value[:visible_chars]}..."

def _safe_auth_response(auth_config: AuthConfig, headers: dict) -> dict:
    """Build a safe response without exposing raw secrets."""
    return {
        "auth_type": auth_config.type.value if hasattr(auth_config.type, 'value') else str(auth_config.type),
        "provider_name": auth_config.provider_name,
        "resolution": {
            "resolved_from": auth_config.resolution.resolved_from,
            "token_resolver": auth_config.resolution.token_resolver.value if hasattr(auth_config.resolution.token_resolver, 'value') else str(auth_config.resolution.token_resolver),
            "is_placeholder": auth_config.resolution.is_placeholder,
        },
        "credentials": {
            "token_resolved": bool(auth_config.token),
            "token_preview": _mask_value(auth_config.token),
            "username": auth_config.username,  # Usually not sensitive
            "email": auth_config.email,
            "password_resolved": bool(auth_config.password),
            "header_name": auth_config.header_name,
        },
        "headers": {
            # Mask Authorization header value
            k: _mask_value(v) if k.lower() == "authorization" else v
            for k, v in headers.items()
        },
        "headers_count": len(headers),
    }

router = APIRouter(prefix="/healthz/admin/app-yaml-config", tags=["Admin"])


@router.get("/status")
async def get_status():
    """Get AppYamlConfig status."""
    config = AppYamlConfig.get_instance()
    load_result = config.get_load_result()
    return {
        "initialized": config.is_initialized(),
        "app_env": load_result.app_env if load_result else None,
        "files_loaded": load_result.files_loaded if load_result else [],
    }


@router.get("/json")
async def get_json():
    """Get full config as JSON."""
    config = AppYamlConfig.get_instance()
    return config.get_all()


@router.get("/compute/{name:path}")
async def get_compute(name: str):
    """Get computed value by name, supports auth:providers.x pattern."""
    config = AppYamlConfig.get_instance()

    # 1. Check Standard Compute Allowlist
    allowed_compute = config.get("expose_yaml_config_compute") or []

    # 2. Check Auth Compute Allowlist
    is_auth_request = name.startswith("auth:")
    if is_auth_request:
        path_parts = name[5:].split(".")  # Remove 'auth:'
        if len(path_parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid auth path format")

        config_type = path_parts[0]  # providers, services
        config_name = path_parts[1]

        expose_auth = config.get("expose_yaml_config_compute_auth") or {}
        allowed_names = expose_auth.get(config_type) or []

        if config_name not in allowed_names:
            raise HTTPException(status_code=403, detail=f"{name} not in allowlist")

    elif name not in allowed_compute:
        raise HTTPException(status_code=403, detail=f"{name} not in allowlist")

    try:
        value = config.get_computed(name)

        if is_auth_request:
            # Transform for safe display
            auth_config = value.get("auth_config") if isinstance(value, dict) else None
            if auth_config:
                safe_val = {
                    "type": getattr(auth_config, 'type', None),
                    "provider_name": getattr(auth_config, 'provider_name', None),
                    "token_resolved": bool(getattr(auth_config, 'token', None)),
                    "token_source": getattr(auth_config.resolution, 'resolved_from', 'unknown') if hasattr(auth_config, 'resolution') and auth_config.resolution else "unknown",
                    "username": getattr(auth_config, 'username', None),
                    "token_preview": f"{auth_config.token[:4]}..." if getattr(auth_config, 'token', None) else None
                }
                return {"name": name, "value": safe_val}

        return {"name": name, "value": value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Providers ====================

@router.get("/providers")
async def list_providers():
    """List all provider names."""
    config = AppYamlConfig.get_instance()
    providers = config.get("providers") or {}
    return {"providers": list(providers.keys())}


@router.get("/provider/{name}")
async def get_provider_config(name: str):
    """Get provider config by name."""
    config = AppYamlConfig.get_instance()

    # Check allowlist
    allowed = config.get("expose_yaml_config_provider") or []
    if name not in allowed:
        raise HTTPException(status_code=403, detail=f"Provider '{name}' not in allowlist")

    try:
        result = get_provider(name, config)
        return {
            "name": result.name,
            "config": result.config,
            "env_overwrites": result.env_overwrites,
            "global_merged": result.global_merged,
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Services ====================

@router.get("/services")
async def list_services():
    """List all service names."""
    config = AppYamlConfig.get_instance()
    services = config.get("services") or {}
    return {"services": list(services.keys())}


@router.get("/service/{name}")
async def get_service_config(name: str):
    """Get service config by name."""
    config = AppYamlConfig.get_instance()

    # Check allowlist
    allowed = config.get("expose_yaml_config_service") or []
    if name not in allowed:
        raise HTTPException(status_code=403, detail=f"Service '{name}' not in allowlist")

    try:
        result = get_service(name, config)
        return {
            "name": result.name,
            "config": result.config,
            "env_overwrites": result.env_overwrites,
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Storages ====================

@router.get("/storages")
async def list_storages():
    """List all storage names."""
    config = AppYamlConfig.get_instance()
    storages = config.get("storage") or {}
    return {"storages": list(storages.keys())}


@router.get("/storage/{name}")
async def get_storage_config(name: str):
    """Get storage config by name."""
    config = AppYamlConfig.get_instance()

    # Check allowlist
    allowed = config.get("expose_yaml_config_storage") or []
    if name not in allowed:
        raise HTTPException(status_code=403, detail=f"Storage '{name}' not in allowlist")

    try:
        result = get_storage(name, config)
        return {
            "name": result.name,
            "config": result.config,
            "env_overwrites": result.env_overwrites,
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/provider/{name}/auth_config")
async def get_provider_auth_config(name: str):
    """Resolve auth config for a provider."""
    config = AppYamlConfig.get_instance()

    # Check allowlist
    allowed = config.get("expose_yaml_config_provider") or []
    if name not in allowed:
        raise HTTPException(status_code=403, detail=f"Provider '{name}' not in allowlist")

    try:
        # 1. Get provider config
        # detailed options not imported yet, need to import ProviderOptions etc or pass dict?
        # get_provider sig: (name, config=None, options=None). options is ProviderOptions.
        from app_yaml_config import ProviderOptions
        result = get_provider(name, config, options=ProviderOptions(remove_meta_keys=False))
        provider_config = result.config

        # 2. Resolve auth from env vars
        auth_config = fetch_auth_config(name, provider_config)

        # 3. Encode to headers
        creds = _build_credentials(auth_config)
        headers = encode_auth(auth_config.type.value, **creds)

        # 4. Return safe response
        return _safe_auth_response(auth_config, headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/service/{name}/auth_config")
async def get_service_auth_config(name: str):
    """Resolve auth config for a service."""
    config = AppYamlConfig.get_instance()

    allowed = config.get("expose_yaml_config_service") or []
    if name not in allowed:
        raise HTTPException(status_code=403, detail=f"Service '{name}' not in allowlist")

    try:
        from app_yaml_config import ServiceOptions
        result = get_service(name, config, options=ServiceOptions(remove_meta_keys=False))
        auth_config = fetch_auth_config(name, result.config)
        creds = _build_credentials(auth_config)
        headers = encode_auth(auth_config.type.value, **creds)
        return _safe_auth_response(auth_config, headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage/{name}/auth_config")
async def get_storage_auth_config(name: str):
    """Resolve auth config for a storage."""
    config = AppYamlConfig.get_instance()

    allowed = config.get("expose_yaml_config_storage") or []
    if name not in allowed:
        raise HTTPException(status_code=403, detail=f"Storage '{name}' not in allowlist")

    try:
        from app_yaml_config import StorageOptions
        result = get_storage(name, config, options=StorageOptions(remove_meta_keys=False))
        auth_config = fetch_auth_config(name, result.config)
        creds = _build_credentials(auth_config)
        headers = encode_auth(auth_config.type.value, **creds)
        return _safe_auth_response(auth_config, headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/provider/{name}/proxy")
async def get_provider_proxy(name: str):
    """Compute the runtime proxy URL for a provider."""
    config = AppYamlConfig.get_instance()

    # Check allowlist
    allowed = config.get("expose_yaml_config_provider") or []
    if name not in allowed:
        raise HTTPException(status_code=403, detail=f"Provider '{name}' not in allowlist")

    try:
        from app_yaml_config import ProviderOptions
        from app_yaml_config.resolve_proxy import resolve_provider_proxy

        result = get_provider(name, config, options=ProviderOptions(remove_meta_keys=False))
        global_config = config.get("global") or {}
        load_result = config.get_load_result()
        app_env = load_result.app_env if load_result else "dev"

        proxy_result = resolve_provider_proxy(
            name,
            result.config,
            global_config,
            app_env
        )

        return {
            "provider_name": name,
            "proxy_url": proxy_result.proxy_url,
            "resolution": {
                "source": proxy_result.source,
                "env_var_used": proxy_result.env_var_used,
                "original_value": proxy_result.original_value,
                "global_proxy": proxy_result.global_proxy,
                "app_env": proxy_result.app_env,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
