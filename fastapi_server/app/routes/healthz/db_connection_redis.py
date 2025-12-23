"""Redis healthz routes."""

from fastapi import APIRouter
from db_connection_redis import (
    RedisConfig,
    get_async_redis_client,
)
from app_yaml_config import AppYamlConfig
from yaml_config_factory import YamlConfigFactory, create_runtime_config_response

router = APIRouter(prefix="/healthz/admin/db-connection-redis", tags=["Admin"])


async def check_connection(config: RedisConfig) -> dict:
    """Check Redis connection with specific config."""
    redis_client = None
    try:
        redis_client = await get_async_redis_client(config)
        pong = await redis_client.ping()
        info = await redis_client.info("server")
        await redis_client.close()
        return {
            "success": pong,
            "info": info,
            "error": None,
        }
    except Exception as e:
        if redis_client:
            await redis_client.close()
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/status")
async def redis_status():
    """Redis connection status."""
    redis_client = None
    try:
        config = RedisConfig()
        redis_client = await get_async_redis_client(config)
        pong = await redis_client.ping()
        info = await redis_client.info("server")
        await redis_client.close()
        return {
            "connected": pong,
            "version": info.get("redis_version"),
            "mode": info.get("redis_mode"),
            "error": None,
        }
    except Exception as e:
        if redis_client:
            await redis_client.close()
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
