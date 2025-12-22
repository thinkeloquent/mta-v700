/**
 * AppYamlConfig healthz routes.
 */

import { AppYamlConfig, getProvider, getService, getStorage } from '@internal/app-yaml-config';

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


  const getExposeComputeAllowlist = () => {
    const config = AppYamlConfig.getInstance();
    return config.get('expose_yaml_config_compute') || [];
  };

  fastify.get('/healthz/admin/app-yaml-config/compute/:name', async (request, reply) => {
    const { name } = request.params;

    if (!getExposeComputeAllowlist().includes(name)) {
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


  const getExposeProviderAllowlist = () => {
    const config = AppYamlConfig.getInstance();
    return config.get('expose_yaml_config_provider') || [];
  };

  fastify.get('/healthz/admin/app-yaml-config/provider/:name', async (request, reply) => {
    const { name } = request.params;

    if (!getExposeProviderAllowlist().includes(name)) {
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

  const getExposeServiceAllowlist = () => {
    const config = AppYamlConfig.getInstance();
    return config.get('expose_yaml_config_service') || [];
  };

  fastify.get('/healthz/admin/app-yaml-config/service/:name', async (request, reply) => {
    const { name } = request.params;

    if (!getExposeServiceAllowlist().includes(name)) {
      reply.code(403);
      return { error: 'Access denied to this service configuration' };
    }

    try {
      const result = getService(name);
      return result;
    } catch (e) {
      if (e.name === 'ServiceNotFoundError') {
        reply.code(404);
        return { error: `Service '${name}' not found` };
      }
      throw e;
    }
  });

  fastify.get('/healthz/admin/app-yaml-config/services', async (request, reply) => {
    const config = AppYamlConfig.getInstance();
    const services = config.get('services') || {};
    return Object.keys(services);
  });

  const getExposeStorageAllowlist = () => {
    const config = AppYamlConfig.getInstance();
    return config.get('expose_yaml_config_storage') || [];
  };

  fastify.get('/healthz/admin/app-yaml-config/storage/:name', async (request, reply) => {
    const { name } = request.params;

    if (!getExposeStorageAllowlist().includes(name)) {
      reply.code(403);
      return { error: 'Access denied to this storage configuration' };
    }

    try {
      const result = getStorage(name);
      return result;
    } catch (e) {
      if (e.name === 'StorageNotFoundError') {
        reply.code(404);
        return { error: `Storage '${name}' not found` };
      }
      throw e;
    }
  });

  fastify.get('/healthz/admin/app-yaml-config/storages', async (request, reply) => {
    const config = AppYamlConfig.getInstance();
    const storages = config.get('storage') || {};
    return Object.keys(storages);
  });
}

