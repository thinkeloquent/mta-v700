"""Redis healthz routes."""

from fastapi import APIRouter
from db_connection_redis import (
    RedisConfig,
    get_async_redis_client,
)

router = APIRouter(prefix="/healthz/admin/db-connection-redis", tags=["Admin"])


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
    config = RedisConfig()
    return {
        "host": config.host,
        "port": config.port,
        "db": config.db,
        "use_ssl": config.use_ssl,
    }
