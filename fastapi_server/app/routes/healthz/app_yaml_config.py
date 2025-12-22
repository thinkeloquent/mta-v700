"""AppYamlConfig healthz routes."""

from fastapi import APIRouter
from ...app_yaml_config import AppYamlConfig

router = APIRouter(prefix="/healthz/admin/app-yaml-config", tags=["Admin"])


@router.get("/status")
async def app_yaml_config_status():
    """AppYamlConfig status."""
    config = AppYamlConfig.get_instance()
    load_result = config.get_load_result()
    return {
        "initialized": config.is_initialized(),
        "app_env": load_result.app_env if load_result else None,
        "files_loaded": load_result.files_loaded if load_result else [],
    }


@router.get("/json")
async def app_yaml_config_json():
    """AppYamlConfig contents as JSON."""
    config = AppYamlConfig.get_instance()
    return config.get_all()



def _get_expose_compute_allowlist() -> set:
    """Get allowlist from YAML config."""
    config = AppYamlConfig.get_instance()
    return set(config.get("expose_yaml_config_compute") or [])


@router.get("/compute/{name}")
async def app_yaml_config_compute(name: str):
    """Get a computed configuration value."""
    if name not in _get_expose_compute_allowlist():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Access denied to this computed property")

    config = AppYamlConfig.get_instance()
    try:
        val = config.get_computed(name)
        return {"name": name, "value": val}
    except Exception as e:
        # Catching generic exception as specific exceptions might not be imported here
        # Ideally we should import ComputedKeyNotFoundError
        from ...app_yaml_config import AppYamlConfig as AppConfigModule
        # Re-import to be safe or check exception type string
        if "ComputedKeyNotFoundError" in str(type(e)):
             from fastapi import HTTPException
             raise HTTPException(status_code=404, detail=f"Computed key '{name}' not found")
        raise e


def _get_expose_provider_allowlist() -> set:
    """Get allowlist from YAML config."""
    config = AppYamlConfig.get_instance()
    return set(config.get("expose_yaml_config_provider") or [])


@router.get("/provider/{name}")
async def app_yaml_config_provider(name: str):
    """Get a provider configuration."""
    if name not in _get_expose_provider_allowlist():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Access denied to this provider configuration")

    try:
        from dataclasses import asdict
        from ...app_yaml_config import get_provider, ProviderNotFoundError
        
        result = get_provider(name)
        return asdict(result)
    except Exception as e:
        if "ProviderNotFoundError" in str(type(e)):
             from fastapi import HTTPException
             raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")
        raise e



@router.get("/providers")
async def app_yaml_config_list_providers():
    """List all available providers."""
    config = AppYamlConfig.get_instance()
    providers = config.get("providers") or {}
    return list(providers.keys())


def _get_expose_service_allowlist() -> set:
    """Get allowlist from YAML config."""
    config = AppYamlConfig.get_instance()
    return set(config.get("expose_yaml_config_service") or [])


@router.get("/service/{name}")
async def app_yaml_config_service(name: str):
    """Get a service configuration."""
    if name not in _get_expose_service_allowlist():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Access denied to this service configuration")

    try:
        from dataclasses import asdict
        from ...app_yaml_config import get_service, ServiceNotFoundError
        
        result = get_service(name)
        return asdict(result)
    except Exception as e:
        if "ServiceNotFoundError" in str(type(e)):
             from fastapi import HTTPException
             raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
        raise e


@router.get("/services")
async def app_yaml_config_list_services():
    """List all available services."""
    config = AppYamlConfig.get_instance()
    services = config.get("services") or {}
    return list(services.keys())


def _get_expose_storage_allowlist() -> set:
    """Get allowlist from YAML config."""
    config = AppYamlConfig.get_instance()
    return set(config.get("expose_yaml_config_storage") or [])


@router.get("/storage/{name}")
async def app_yaml_config_storage(name: str):
    """Get a storage configuration."""
    if name not in _get_expose_storage_allowlist():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Access denied to this storage configuration")

    try:
        from dataclasses import asdict
        from ...app_yaml_config import get_storage, StorageNotFoundError
        
        result = get_storage(name)
        return asdict(result)
    except Exception as e:
        if "StorageNotFoundError" in str(type(e)):
             from fastapi import HTTPException
             raise HTTPException(status_code=404, detail=f"Storage '{name}' not found")
        raise e


@router.get("/storages")
async def app_yaml_config_list_storages():
    """List all available storages."""
    config = AppYamlConfig.get_instance()
    storages = config.get("storage") or {}
    return list(storages.keys())

