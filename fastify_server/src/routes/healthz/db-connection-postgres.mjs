/**
 * Postgres healthz routes.
 */

import {
  PostgresConfig,
  getPostgresClient,
  checkConnection,
} from '@internal/db_connection_postgres';

// SSL modes to try in order of preference
const SSL_MODES = [
  { mode: 'verify-full', description: 'SSL with full verification', rejectUnauthorized: true },
  { mode: 'verify-ca', description: 'SSL with CA verification', rejectUnauthorized: true },
  { mode: 'require', description: 'SSL required, no verification', rejectUnauthorized: false },
  { mode: 'prefer', description: 'SSL preferred', rejectUnauthorized: false },
  { mode: 'disable', description: 'No SSL', ssl: false },
];

async function tryConnection(sslMode) {
  try {
    const config = new PostgresConfig({ sslMode: sslMode.mode });
    const client = getPostgresClient(config);
    await checkConnection(client);
    await client.close();
    return {
      ssl_mode: sslMode.mode,
      description: sslMode.description,
      connected: true,
      error: null,
    };
  } catch (e) {
    return {
      ssl_mode: sslMode.mode,
      description: sslMode.description,
      connected: false,
      error: e.message,
    };
  }
}

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
        ssl_mode: config.sslMode,
        error: null,
      };
    } catch (e) {
      return {
        connected: false,
        host: null,
        database: null,
        ssl_mode: null,
        error: e.message,
      };
    }
  });

  fastify.get('/healthz/admin/db-connection-postgres/probe', async (request, reply) => {
    const config = new PostgresConfig();
    const results = [];

    for (const sslMode of SSL_MODES) {
      const result = await tryConnection(sslMode);
      results.push(result);
    }

    // Find first successful connection
    const successful = results.filter(r => r.connected);

    return {
      host: config.host,
      port: config.port,
      database: config.database,
      username: config.username,
      current_ssl_mode: config.sslMode,
      recommended_ssl_mode: successful.length > 0 ? successful[0].ssl_mode : null,
      results,
    };
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
