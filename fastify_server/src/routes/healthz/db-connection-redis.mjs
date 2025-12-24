/**
 * Redis healthz routes.
 */

import {
  RedisConfig,
  getRedisClient,
} from '@internal/db_connection_redis';
import { AppYamlConfig } from '@internal/app-yaml-config';
import { YamlConfigFactory, createRuntimeConfigResponse } from '@internal/yaml-config-factory';

export default async function redisRoutes(fastify) {

  async function checkConnection(config) {
    let redis = null;
    try {
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
  }

  fastify.get('/healthz/admin/db-connection-redis/status', async (request, reply) => {
    const config = new RedisConfig();
    return checkConnection(config);
  });

  fastify.get('/healthz/admin/db-connection-redis/config', async (request, reply) => {
    const configInstance = AppYamlConfig.getInstance();
    const factory = new YamlConfigFactory(configInstance);
    // @ts-ignore - computeAll is typed but we are in JS
    const result = await factory.computeAll('storages.redis', undefined, request);
    return createRuntimeConfigResponse(result);
  });
}
