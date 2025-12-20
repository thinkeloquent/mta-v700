/**
 * Redis healthz routes.
 */

import {
  RedisConfig,
  getRedisClient,
} from '@internal/db_connection_redis';

export default async function redisRoutes(fastify) {
  fastify.get('/healthz/admin/db-connection-redis/status', async (request, reply) => {
    let redis = null;
    try {
      const config = new RedisConfig();
      redis = getRedisClient(config);

      // Wait for ready or error
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error('Connection timeout')), 5000);
        redis.on('ready', () => {
          clearTimeout(timeout);
          resolve();
        });
        redis.on('error', (err) => {
          clearTimeout(timeout);
          reject(err);
        });
      });

      const pong = await redis.ping();
      const info = await redis.info('server');
      const lines = info.split('\n');
      const version = lines.find((l) => l.startsWith('redis_version:'))?.split(':')[1]?.trim();
      const mode = lines.find((l) => l.startsWith('redis_mode:'))?.split(':')[1]?.trim();

      redis.disconnect();

      return {
        connected: pong === 'PONG',
        version: version || null,
        mode: mode || null,
        error: null,
      };
    } catch (e) {
      if (redis) {
        redis.disconnect();
      }
      return {
        connected: false,
        version: null,
        mode: null,
        error: e.message,
      };
    }
  });

  fastify.get('/healthz/admin/db-connection-redis/config', async (request, reply) => {
    const config = new RedisConfig();
    return {
      host: config.host,
      port: config.port,
      db: config.db,
      use_tls: config.useTls,
    };
  });
}
