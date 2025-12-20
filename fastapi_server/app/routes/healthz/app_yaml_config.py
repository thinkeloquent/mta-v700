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
