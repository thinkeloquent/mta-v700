"""
FastAPI example demonstrating db_connection_redis usage.

Run with: uvicorn main:app --reload
"""

import os
import json
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from db_connection_redis import (
    RedisConfig,
    get_async_redis_client,
    check_connection,
)


class KeyValue(BaseModel):
    key: str
    value: Any
    ttl: Optional[int] = None


class HashField(BaseModel):
    key: str
    field: str
    value: str


class ListItem(BaseModel):
    key: str
    value: str
    position: Optional[str] = "right"  # "left" or "right"


class HealthResponse(BaseModel):
    status: str
    redis: Dict[str, Any]


class CacheStats(BaseModel):
    keys_count: int
    memory_used: Optional[str] = None
    connected_clients: Optional[int] = None


# Global Redis client
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage Redis client lifecycle."""
    global redis_client

    config = RedisConfig(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD"),
        db=int(os.getenv("REDIS_DB", "0")),
        use_ssl=os.getenv("REDIS_SSL", "false").lower() == "true",
    )

    try:
        redis_client = await get_async_redis_client(config)
        await redis_client.ping()
        print("Redis client connected")
    except Exception as e:
        print(f"Warning: Could not connect to Redis: {e}")
        redis_client = None

    yield

    if redis_client:
        await redis_client.close()
        print("Redis client closed")


app = FastAPI(
    title="Redis FastAPI Example",
    description="Example API demonstrating db_connection_redis usage",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API and Redis health."""
    if not redis_client:
        return HealthResponse(
            status="degraded",
            redis={"connected": False, "error": "Client not initialized"},
        )

    try:
        pong = await redis_client.ping()
        info = await redis_client.info("server")
        return HealthResponse(
            status="healthy",
            redis={
                "connected": pong,
                "version": info.get("redis_version"),
                "mode": info.get("redis_mode"),
            },
        )
    except Exception as e:
        return HealthResponse(
            status="degraded",
            redis={"connected": False, "error": str(e)},
        )


@app.get("/stats", response_model=CacheStats)
async def get_stats():
    """Get Redis cache statistics."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        keys_count = await redis_client.dbsize()
        info = await redis_client.info("memory")
        clients_info = await redis_client.info("clients")

        return CacheStats(
            keys_count=keys_count,
            memory_used=info.get("used_memory_human"),
            connected_clients=clients_info.get("connected_clients"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# String operations
@app.get("/keys/{key}")
async def get_key(key: str):
    """Get value by key."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        value = await redis_client.get(key)
        if value is None:
            raise HTTPException(status_code=404, detail="Key not found")

        ttl = await redis_client.ttl(key)
        return {"key": key, "value": value, "ttl": ttl if ttl > 0 else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/keys")
async def set_key(data: KeyValue):
    """Set a key-value pair."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        value = data.value
        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        if data.ttl:
            await redis_client.setex(data.key, data.ttl, value)
        else:
            await redis_client.set(data.key, value)

        return {"key": data.key, "status": "set", "ttl": data.ttl}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/keys/{key}")
async def delete_key(key: str):
    """Delete a key."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        deleted = await redis_client.delete(key)
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Key not found")
        return {"key": key, "status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/keys")
async def list_keys(pattern: str = "*", limit: int = 100):
    """List keys matching pattern."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        keys = []
        async for key in redis_client.scan_iter(match=pattern, count=limit):
            keys.append(key)
            if len(keys) >= limit:
                break
        return {"pattern": pattern, "keys": keys, "count": len(keys)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Hash operations
@app.get("/hash/{key}")
async def get_hash(key: str):
    """Get all fields of a hash."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        data = await redis_client.hgetall(key)
        if not data:
            raise HTTPException(status_code=404, detail="Hash not found")
        return {"key": key, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/hash")
async def set_hash_field(data: HashField):
    """Set a hash field."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        await redis_client.hset(data.key, data.field, data.value)
        return {"key": data.key, "field": data.field, "status": "set"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/hash/{key}/{field}")
async def delete_hash_field(key: str, field: str):
    """Delete a hash field."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        deleted = await redis_client.hdel(key, field)
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Field not found")
        return {"key": key, "field": field, "status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# List operations
@app.get("/list/{key}")
async def get_list(key: str, start: int = 0, stop: int = -1):
    """Get list items."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        items = await redis_client.lrange(key, start, stop)
        length = await redis_client.llen(key)
        return {"key": key, "items": items, "length": length}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/list")
async def push_to_list(data: ListItem):
    """Push item to list."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        if data.position == "left":
            length = await redis_client.lpush(data.key, data.value)
        else:
            length = await redis_client.rpush(data.key, data.value)
        return {"key": data.key, "status": "pushed", "length": length}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/list/{key}")
async def pop_from_list(key: str, position: str = "right"):
    """Pop item from list."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        if position == "left":
            value = await redis_client.lpop(key)
        else:
            value = await redis_client.rpop(key)

        if value is None:
            raise HTTPException(status_code=404, detail="List empty or not found")
        return {"key": key, "value": value, "status": "popped"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Counter operations
@app.post("/counter/{key}/incr")
async def increment_counter(key: str, amount: int = 1):
    """Increment a counter."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        value = await redis_client.incrby(key, amount)
        return {"key": key, "value": value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/counter/{key}/decr")
async def decrement_counter(key: str, amount: int = 1):
    """Decrement a counter."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        value = await redis_client.decrby(key, amount)
        return {"key": key, "value": value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# TTL operations
@app.post("/keys/{key}/expire")
async def set_expiry(key: str, seconds: int):
    """Set expiry on a key."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        result = await redis_client.expire(key, seconds)
        if not result:
            raise HTTPException(status_code=404, detail="Key not found")
        return {"key": key, "ttl": seconds, "status": "set"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/keys/{key}/expire")
async def remove_expiry(key: str):
    """Remove expiry from a key."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        result = await redis_client.persist(key)
        if not result:
            raise HTTPException(status_code=404, detail="Key not found or no TTL")
        return {"key": key, "status": "persist"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
