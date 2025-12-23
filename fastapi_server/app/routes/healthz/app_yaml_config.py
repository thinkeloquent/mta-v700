"""AppYamlConfig healthz routes."""

from fastapi import APIRouter, HTTPException
from app_yaml_config import AppYamlConfig, get_provider, get_service, get_storage

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
