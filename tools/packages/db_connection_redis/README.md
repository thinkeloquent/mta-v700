# Redis Database Connection

Unified Redis database connection package for Python and Node.js applications.

## Overview

This package provides a standardized way to connect to Redis, handling:
- Configuration from environment variables
- Connection pooling
- SSL/TLS defaults for cloud vendors (AWS ElastiCache, Redis Cloud, Upstash, Digital Ocean)
- Health checks
- Async and Sync clients

## Python Usage

```python
from db_connection_redis import RedisConfig, get_async_redis_client

# Config automatically loads from env vars and detects vendor defaults
config = RedisConfig()

# Get async client (aioredis/redis.asyncio)
client = await get_async_redis_client(config)

await client.set("key", "value")
```

## Node.js Usage

```javascript
import { RedisConfig, getRedisClient } from '@internal/db_connection_redis';

const config = new RedisConfig();
const client = getRedisClient(config);

await client.set("key", "value");
```
