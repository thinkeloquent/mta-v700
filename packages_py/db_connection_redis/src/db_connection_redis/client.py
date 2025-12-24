import logging
import redis
from redis.asyncio import Redis as AsyncRedis
from typing import Optional

from .config import RedisConfig
from .exceptions import RedisConnectionError

logger = logging.getLogger(__name__)

async def get_async_redis_client(config: Optional[RedisConfig] = None) -> AsyncRedis:
    """Get an asynchronous Redis client."""
    if config is None:
        config = RedisConfig()
        
    kwargs = config.get_connection_kwargs()
    logger.info(f"Creating async Redis client for {config.host}:{config.port}")
    
    return AsyncRedis(**kwargs)

# Alias for consistent naming
get_redis_client = get_async_redis_client

def get_sync_redis_client(config: Optional[RedisConfig] = None) -> redis.Redis:
    """Get a synchronous Redis client."""
    if config is None:
        config = RedisConfig()
        
    kwargs = config.get_connection_kwargs()
    logger.info(f"Creating sync Redis client for {config.host}:{config.port}")
    
    return redis.Redis(**kwargs)

async def check_connection(config: Optional[RedisConfig] = None) -> bool:
    """Check Redis connectivity."""
    client = await get_async_redis_client(config)
    try:
        await client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False
    finally:
        await client.aclose()

async def check_connection_status(config: Optional[RedisConfig] = None) -> dict:
    """Check Redis connection and return detailed status."""
    if config is None:
        config = RedisConfig()
    redis_client = None
    try:
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

def format_connection_error(error: Exception) -> str:
    """Format Redis connection error for logging."""
    return f"Redis Connection Error: {str(error)}"
