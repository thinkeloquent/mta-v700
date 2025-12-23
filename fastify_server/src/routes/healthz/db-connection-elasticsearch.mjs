/**
 * Elasticsearch healthz routes.
 */

import {
  ElasticsearchConfig,
  checkConnection,
} from '@internal/db-connection-elasticsearch';
import { AppYamlConfig } from '@internal/app-yaml-config';
import { YamlConfigFactory, createRuntimeConfigResponse } from '@internal/yaml-config-factory';

export default async function elasticsearchRoutes(fastify) {
  fastify.get('/healthz/admin/db-connection-elasticsearch/status', async (request, reply) => {
    const config = new ElasticsearchConfig();
    const result = await checkConnection(config);
    return {
      connected: result.success,
      cluster_name: result.info?.cluster_name || null,
      version: result.info?.version?.number || null,
      error: result.error || null,
    };
  });

  fastify.get('/healthz/admin/db-connection-elasticsearch/config', async (request, reply) => {
    const configInstance = AppYamlConfig.getInstance();
    const factory = new YamlConfigFactory(configInstance);
    // @ts-ignore - computeAll is typed but we are in JS
    const result = factory.computeAll('storages.elasticsearch');
    return createRuntimeConfigResponse(result);
  });
}
