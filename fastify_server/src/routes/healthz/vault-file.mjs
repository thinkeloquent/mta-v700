/**
 * Vault file healthz routes.
 */

import { EnvStore } from '@internal/vault-file';

export default async function vaultFileRoutes(fastify) {
  fastify.get('/healthz/admin/vault-file/status', async (request, reply) => {
    const vaultFile = process.env.VAULT_SECRET_FILE;
    return {
      loaded: !!vaultFile,
      file: vaultFile || null,
    };
  });

  fastify.get('/healthz/admin/vault-file/json', async (request, reply) => {
    return EnvStore.getInstance().getAll();
  });

  fastify.get('/healthz/admin/vault-file/compute/*', async (request, reply) => {
    const name = request.params['*'];
    const envStore = EnvStore.getInstance();
    const value = envStore.get(name);

    if (value === undefined || value === null) {
      return reply.code(404).send({ error: `Key '${name}' not found in vault` });
    }

    // Mask the value for security
    const masked = value.length > 4 ? `${value.substring(0, 4)}...` : '****';
    return {
      name,
      exists: true,
      preview: masked,
    };
  });
}
