/**
 * Elasticsearch healthz routes.
 */

import {
  ElasticsearchConfig,
  getElasticsearchClient,
  checkConnection,
} from '@internal/db-connection-elasticsearch';

export default async function elasticsearchRoutes(fastify) {
  fastify.get('/healthz/admin/db-connection-elasticsearch/status', async (request, reply) => {
    const result = await checkConnection();
    return {
      connected: result.success,
      cluster_name: result.info?.cluster_name || null,
      version: result.info?.version?.number || null,
      error: result.error || null,
    };
  });

  fastify.get('/healthz/admin/db-connection-elasticsearch/config', async (request, reply) => {
    const config = new ElasticsearchConfig();
    return {
      host: config.options.host,
      port: config.options.port,
      scheme: config.options.scheme,
      vendor_type: config.options.vendorType,
      use_tls: config.options.useTls,
      verify_certs: config.options.verifyCerts,
    };
  });
}
