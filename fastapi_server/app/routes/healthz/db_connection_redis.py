"""Redis healthz routes."""

from fastapi import APIRouter
from db_connection_redis import (
    RedisConfig,
    check_connection_status,
)
from app_yaml_config import AppYamlConfig
from yaml_config_factory import YamlConfigFactory, create_runtime_config_response

router = APIRouter(prefix="/healthz/admin/db-connection-redis", tags=["Admin"])

@router.get("/status")
async def redis_status():
    """Redis connection status."""
    try:
        config = RedisConfig()
        return await check_connection_status(config)
    except Exception as e:
        return {
            "connected": False,
            "version": None,
            "mode": None,
            "error": str(e),
        }


@router.get("/config")
async def redis_config():
    """Redis configuration."""
    config_instance = AppYamlConfig.get_instance()
    factory = YamlConfigFactory(config_instance)
    result = factory.compute_all("storages.redis")
    return create_runtime_config_response(result)
