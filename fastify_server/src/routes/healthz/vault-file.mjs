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
}
