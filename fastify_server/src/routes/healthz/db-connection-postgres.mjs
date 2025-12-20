/**
 * Postgres healthz routes.
 */

import {
  PostgresConfig,
  getPostgresClient,
  checkConnection,
} from '@internal/db_connection_postgres';

export default async function postgresRoutes(fastify) {
  fastify.get('/healthz/admin/db-connection-postgres/status', async (request, reply) => {
    try {
      const config = new PostgresConfig();
      const client = getPostgresClient(config);
      await checkConnection(client);
      await client.close();
      return {
        connected: true,
        host: config.host,
        database: config.database,
        error: null,
      };
    } catch (e) {
      return {
        connected: false,
        host: null,
        database: null,
        error: e.message,
      };
    }
  });

  fastify.get('/healthz/admin/db-connection-postgres/config', async (request, reply) => {
    const config = new PostgresConfig();
    return {
      host: config.host,
      port: config.port,
      database: config.database,
      username: config.username,
      ssl_mode: config.sslMode,
      max_connections: config.maxConnections,
    };
  });
}
