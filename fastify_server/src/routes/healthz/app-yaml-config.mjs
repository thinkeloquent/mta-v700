/**
 * AppYamlConfig healthz routes.
 */

import { AppYamlConfig, getProvider } from '@internal/app-yaml-config';

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


  const EXPOSE_YAML_CONFIG_COMPUTE = ['proxy_url'];

  fastify.get('/healthz/admin/app-yaml-config/compute/:name', async (request, reply) => {
    const { name } = request.params;

    if (!EXPOSE_YAML_CONFIG_COMPUTE.includes(name)) {
      reply.code(403);
      return { error: 'Access denied to this computed property' };
    }

    const config = AppYamlConfig.getInstance();
    try {
      const val = config.getComputed(name);
      return { name, value: val };
    } catch (e) {
      if (e.name === 'ComputedKeyNotFoundError' || e.message.includes('not defined')) {
        reply.code(404);
        return { error: `Computed key '${name}' not found` };
      }
      throw e;
    }
  });


  const EXPOSE_YAML_CONFIG_PROVIDER = ['gemini_openai'];

  fastify.get('/healthz/admin/app-yaml-config/provider/:name', async (request, reply) => {
    const { name } = request.params;

    if (!EXPOSE_YAML_CONFIG_PROVIDER.includes(name)) {
      reply.code(403);
      return { error: 'Access denied to this provider configuration' };
    }

    try {
      const result = getProvider(name);
      return result;
    } catch (e) {
      if (e.name === 'ProviderNotFoundError') {
        reply.code(404);
        return { error: `Provider '${name}' not found` };
      }
      throw e;
    }
  });

  fastify.get('/healthz/admin/app-yaml-config/providers', async (request, reply) => {
    const config = AppYamlConfig.getInstance();
    const providers = config.get('providers') || {};
    return Object.keys(providers);
  });
}

