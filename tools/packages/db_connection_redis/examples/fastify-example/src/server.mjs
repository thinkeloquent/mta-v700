/**
 * Fastify example demonstrating db_connection_redis usage.
 *
 * Run with: npm run dev
 */

import Fastify from "fastify";
import {
    RedisConfig,
    getRedisClient,
} from "@internal/db_connection_redis";

// Global Redis client
let redis = null;

// Create Fastify instance
const fastify = Fastify({
    logger: true,
});

// Initialize Redis
async function initRedis() {
    const config = new RedisConfig({
        host: process.env.REDIS_HOST || "localhost",
        port: process.env.REDIS_PORT ? parseInt(process.env.REDIS_PORT) : 6379,
        password: process.env.REDIS_PASSWORD || undefined,
        db: process.env.REDIS_DB ? parseInt(process.env.REDIS_DB) : 0,
        useTls: process.env.REDIS_SSL === "true",
    });

    try {
        redis = getRedisClient(config);

        // Wait for connection
        await new Promise((resolve, reject) => {
            redis.on("ready", resolve);
            redis.on("error", reject);
            setTimeout(() => reject(new Error("Connection timeout")), 5000);
        });

        fastify.log.info("Redis connected");
    } catch (e) {
        fastify.log.warn(`Could not connect to Redis: ${e.message}`);
        redis = null;
    }
}

// Health check
fastify.get("/health", async (request, reply) => {
    if (!redis) {
        return {
            status: "degraded",
            redis: { connected: false, error: "Client not initialized" },
        };
    }

    try {
        const pong = await redis.ping();
        const info = await redis.info("server");
        const lines = info.split("\n");
        const version = lines.find((l) => l.startsWith("redis_version:"))?.split(":")[1]?.trim();
        const mode = lines.find((l) => l.startsWith("redis_mode:"))?.split(":")[1]?.trim();

        return {
            status: "healthy",
            redis: {
                connected: pong === "PONG",
                version,
                mode,
            },
        };
    } catch (e) {
        return {
            status: "degraded",
            redis: { connected: false, error: e.message },
        };
    }
});

// Get stats
fastify.get("/stats", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    try {
        const keysCount = await redis.dbsize();
        const memoryInfo = await redis.info("memory");
        const clientsInfo = await redis.info("clients");

        const memoryUsed = memoryInfo.match(/used_memory_human:(\S+)/)?.[1];
        const connectedClients = clientsInfo.match(/connected_clients:(\d+)/)?.[1];

        return {
            keys_count: keysCount,
            memory_used: memoryUsed,
            connected_clients: connectedClients ? parseInt(connectedClients) : null,
        };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

// Get key
fastify.get("/keys/:key", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { key } = request.params;

    try {
        const value = await redis.get(key);
        if (value === null) {
            return reply.code(404).send({ error: "Key not found" });
        }

        const ttl = await redis.ttl(key);
        return { key, value, ttl: ttl > 0 ? ttl : null };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

// Set key
fastify.post("/keys", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { key, value, ttl } = request.body;

    try {
        const strValue = typeof value === "object" ? JSON.stringify(value) : String(value);

        if (ttl) {
            await redis.setex(key, ttl, strValue);
        } else {
            await redis.set(key, strValue);
        }

        return { key, status: "set", ttl: ttl || null };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

// Delete key
fastify.delete("/keys/:key", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { key } = request.params;

    try {
        const deleted = await redis.del(key);
        if (deleted === 0) {
            return reply.code(404).send({ error: "Key not found" });
        }
        return { key, status: "deleted" };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

// List keys
fastify.get("/keys", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { pattern = "*", limit = 100 } = request.query;

    try {
        const keys = [];
        let cursor = "0";

        do {
            const [newCursor, results] = await redis.scan(cursor, "MATCH", pattern, "COUNT", limit);
            cursor = newCursor;
            keys.push(...results);
        } while (cursor !== "0" && keys.length < limit);

        return { pattern, keys: keys.slice(0, limit), count: keys.length };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

// Hash operations
fastify.get("/hash/:key", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { key } = request.params;

    try {
        const data = await redis.hgetall(key);
        if (!data || Object.keys(data).length === 0) {
            return reply.code(404).send({ error: "Hash not found" });
        }
        return { key, data };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

fastify.post("/hash", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { key, field, value } = request.body;

    try {
        await redis.hset(key, field, value);
        return { key, field, status: "set" };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

fastify.delete("/hash/:key/:field", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { key, field } = request.params;

    try {
        const deleted = await redis.hdel(key, field);
        if (deleted === 0) {
            return reply.code(404).send({ error: "Field not found" });
        }
        return { key, field, status: "deleted" };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

// List operations
fastify.get("/list/:key", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { key } = request.params;
    const { start = 0, stop = -1 } = request.query;

    try {
        const items = await redis.lrange(key, parseInt(start), parseInt(stop));
        const length = await redis.llen(key);
        return { key, items, length };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

fastify.post("/list", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { key, value, position = "right" } = request.body;

    try {
        let length;
        if (position === "left") {
            length = await redis.lpush(key, value);
        } else {
            length = await redis.rpush(key, value);
        }
        return { key, status: "pushed", length };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

fastify.delete("/list/:key", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { key } = request.params;
    const { position = "right" } = request.query;

    try {
        let value;
        if (position === "left") {
            value = await redis.lpop(key);
        } else {
            value = await redis.rpop(key);
        }

        if (value === null) {
            return reply.code(404).send({ error: "List empty or not found" });
        }
        return { key, value, status: "popped" };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

// Counter operations
fastify.post("/counter/:key/incr", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { key } = request.params;
    const { amount = 1 } = request.query;

    try {
        const value = await redis.incrby(key, parseInt(amount));
        return { key, value };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

fastify.post("/counter/:key/decr", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { key } = request.params;
    const { amount = 1 } = request.query;

    try {
        const value = await redis.decrby(key, parseInt(amount));
        return { key, value };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

// TTL operations
fastify.post("/keys/:key/expire", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { key } = request.params;
    const { seconds } = request.body;

    try {
        const result = await redis.expire(key, seconds);
        if (result === 0) {
            return reply.code(404).send({ error: "Key not found" });
        }
        return { key, ttl: seconds, status: "set" };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

fastify.delete("/keys/:key/expire", async (request, reply) => {
    if (!redis) {
        return reply.code(503).send({ error: "Redis not connected" });
    }

    const { key } = request.params;

    try {
        const result = await redis.persist(key);
        if (result === 0) {
            return reply.code(404).send({ error: "Key not found or no TTL" });
        }
        return { key, status: "persist" };
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

// Start server
async function start() {
    try {
        await initRedis();

        const port = process.env.PORT ? parseInt(process.env.PORT) : 3000;
        await fastify.listen({ port, host: "0.0.0.0" });
        fastify.log.info(`Server running on port ${port}`);
    } catch (err) {
        fastify.log.error(err);
        process.exit(1);
    }
}

// Graceful shutdown
const signals = ["SIGINT", "SIGTERM"];
signals.forEach((signal) => {
    process.on(signal, async () => {
        fastify.log.info(`Received ${signal}, shutting down...`);
        if (redis) {
            redis.disconnect();
            fastify.log.info("Redis disconnected");
        }
        await fastify.close();
        process.exit(0);
    });
});

start();
