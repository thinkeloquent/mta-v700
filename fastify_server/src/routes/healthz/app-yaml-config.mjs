/**
 * AppYamlConfig healthz routes.
 */

import { AppYamlConfig } from '@internal/app-yaml-config';

export default async function appYamlConfigRoutes(fastify) {
  fastify.get('/healthz/admin/app-yaml-config/status', async (request, reply) => {
    const config = AppYamlConfig.getInstance();
    const loadResult = config.getLoadResult?.() || null;
    return {
      initialized: config.isInitialized?.() ?? true,
      appEnv: loadResult?.appEnv || null,
      filesLoaded: loadResult?.filesLoaded || [],
    };
  });

  fastify.get('/healthz/admin/app-yaml-config/json', async (request, reply) => {
    const config = AppYamlConfig.getInstance();
    return config.getAll();
  });
}
