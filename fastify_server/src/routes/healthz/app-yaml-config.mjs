/**
 * AppYamlConfig healthz routes.
 */
import { AppYamlConfig, getProvider, getService, getStorage, resolveProviderProxy } from '@internal/app-yaml-config';
import { fetchAuthConfig } from '@internal/fetch-auth-config';
import { encodeAuth } from '@internal/fetch-auth-encoding';

function buildCredentials(authConfig) {
  const creds = {};
  if (authConfig.token) creds.token = authConfig.token;
  if (authConfig.username) creds.username = authConfig.username;
  if (authConfig.password) creds.password = authConfig.password;
  if (authConfig.email) creds.email = authConfig.email;
  if (authConfig.headerName) creds.headerKey = authConfig.headerName;
  if (authConfig.headerValue) creds.headerValue = authConfig.headerValue;
  return creds;
}

function maskValue(value, visibleChars = 20) {
  if (!value) return null;
  if (value.length <= visibleChars) return '****';
  return `${value.substring(0, visibleChars)}...`;
}

function safeAuthResponse(authConfig, headers) {
  return {
    authType: authConfig.type,
    providerName: authConfig.providerName,
    resolution: {
      resolvedFrom: authConfig.resolution.resolvedFrom,
      tokenResolver: authConfig.resolution.tokenResolver,
      isPlaceholder: authConfig.resolution.isPlaceholder,
    },
    credentials: {
      tokenResolved: !!authConfig.token,
      tokenPreview: maskValue(authConfig.token),
      username: authConfig.username,
      email: authConfig.email,
      passwordResolved: !!authConfig.password,
      headerName: authConfig.headerName,
    },
    headers: Object.fromEntries(
      Object.entries(headers).map(([k, v]) => [
        k,
        k.toLowerCase() === 'authorization' ? maskValue(v) : v
      ])
    ),
    headersCount: Object.keys(headers).length,
  };
}

export default async function appYamlConfigRoutes(fastify, opts) {
  // Register with prefix
  fastify.register(async function (fastify) {

    // ==================== Status & JSON ====================

    fastify.get('/status', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const loadResult = config.getLoadResult();
      return {
        initialized: config.isInitialized(),
        app_env: loadResult?.appEnv || null,
        files_loaded: loadResult?.filesLoaded || [],
      };
    });

    fastify.get('/json', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      return config.getAll();
    });

    // ==================== Compute ====================

    fastify.get('/compute/*', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const name = request.params['*'];

      // 1. Check Standard Allowlist
      const allowedCompute = config.get('expose_yaml_config_compute') || [];

      // 2. Check Auth Allowlist
      const isAuthRequest = name.startsWith('auth:');

      if (isAuthRequest) {
        const pathParts = name.substring(5).split('.');
        if (pathParts.length !== 2) {
          return reply.code(400).send({ error: 'Invalid auth path format' });
        }

        const configType = pathParts[0];
        const configName = pathParts[1];

        const exposeAuth = config.get('expose_yaml_config_compute_auth') || {};
        const allowedNames = exposeAuth[configType] || [];

        if (!allowedNames.includes(configName)) {
          return reply.code(403).send({ error: `${name} not in allowlist` });
        }
      } else if (!allowedCompute.includes(name)) {
        return reply.code(403).send({ error: `${name} not in allowlist` });
      }

      try {
        const value = config.getComputed(name);

        if (isAuthRequest) {
          // Safe transformation
          const authConfig = value?.authConfig;
          if (authConfig) {
            const safeVal = {
              type: authConfig.type,
              providerName: authConfig.providerName,
              tokenResolved: !!authConfig.token,
              tokenSource: authConfig.resolution?.resolvedFrom || 'unknown',
              username: authConfig.username,
              tokenPreview: authConfig.token ? `${authConfig.token.substring(0, 4)}...` : null
            };
            return { name, value: safeVal };
          }
        }

        return { name, value };
      } catch (err) {
        request.log.error(err);
        return reply.code(500).send({ error: err.message });
      }
    });

    // ==================== Providers ====================

    fastify.get('/providers', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const providers = config.get('providers') || {};
      return { providers: Object.keys(providers) };
    });

    fastify.get('/provider/*', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const name = request.params['*'];

      // Check allowlist
      const allowed = config.get('expose_yaml_config_provider') || [];
      if (!allowed.includes(name)) {
        return reply.code(403).send({ error: `Provider '${name}' not in allowlist` });
      }

      try {
        const result = getProvider(name, config);
        return {
          name: result.name,
          config: result.config,
          envOverwrites: result.envOverwrites,
          globalMerged: result.globalMerged,
        };
      } catch (err) {
        return reply.code(404).send({ error: err.message });
      }
    });

    // ==================== Services ====================

    fastify.get('/services', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const services = config.get('services') || {};
      return { services: Object.keys(services) };
    });

    fastify.get('/service/*', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const name = request.params['*'];

      // Check allowlist
      const allowed = config.get('expose_yaml_config_service') || [];
      if (!allowed.includes(name)) {
        return reply.code(403).send({ error: `Service '${name}' not in allowlist` });
      }

      try {
        const result = getService(name, config);
        return {
          name: result.name,
          config: result.config,
          envOverwrites: result.envOverwrites,
        };
      } catch (err) {
        return reply.code(404).send({ error: err.message });
      }
    });

    // ==================== Storages ====================

    fastify.get('/storages', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const storages = config.get('storage') || {};
      return { storages: Object.keys(storages) };
    });

    fastify.get('/storage/*', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const name = request.params['*'];

      // Check allowlist
      const allowed = config.get('expose_yaml_config_storage') || [];
      if (!allowed.includes(name)) {
        return reply.code(403).send({ error: `Storage '${name}' not in allowlist` });
      }

      try {
        const result = getStorage(name, config);
        return {
          name: result.name,
          config: result.config,
          envOverwrites: result.envOverwrites,
        };
      } catch (err) {
        return reply.code(404).send({ error: err.message });
      }
    });

    fastify.get('/provider/:name/auth_config', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const name = request.params.name;

      const allowed = config.get('expose_yaml_config_provider') || [];
      if (!allowed.includes(name)) {
        return reply.code(403).send({ error: `Provider '${name}' not in allowlist` });
      }

      try {
        const result = getProvider(name, config, { removeMetaKeys: false });
        const authConfig = fetchAuthConfig({
          providerName: name,
          providerConfig: result.config
        });
        const creds = buildCredentials(authConfig);
        const headers = encodeAuth(authConfig.type, creds);
        return safeAuthResponse(authConfig, headers);
      } catch (err) {
        return reply.code(500).send({ error: err.message });
      }
    });

    fastify.get('/service/:name/auth_config', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const name = request.params.name;

      const allowed = config.get('expose_yaml_config_service') || [];
      if (!allowed.includes(name)) {
        return reply.code(403).send({ error: `Service '${name}' not in allowlist` });
      }

      try {
        const result = getService(name, config, { removeMetaKeys: false });
        const authConfig = fetchAuthConfig({
          providerName: name,
          providerConfig: result.config
        });
        const creds = buildCredentials(authConfig);
        const headers = encodeAuth(authConfig.type, creds);
        return safeAuthResponse(authConfig, headers);
      } catch (err) {
        return reply.code(500).send({ error: err.message });
      }
    });

    fastify.get('/storage/:name/auth_config', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const name = request.params.name;

      const allowed = config.get('expose_yaml_config_storage') || [];
      if (!allowed.includes(name)) {
        return reply.code(403).send({ error: `Storage '${name}' not in allowlist` });
      }

      try {
        const result = getStorage(name, config, { removeMetaKeys: false });
        const authConfig = fetchAuthConfig({
          providerName: name,
          providerConfig: result.config
        });
        const creds = buildCredentials(authConfig);
        const headers = encodeAuth(authConfig.type, creds);
        return safeAuthResponse(authConfig, headers);
      } catch (err) {
        return reply.code(500).send({ error: err.message });
      }
    });

    fastify.get('/provider/:name/proxy', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const name = request.params.name;

      // Check allowlist
      const allowed = config.get('expose_yaml_config_provider') || [];
      if (!allowed.includes(name)) {
        return reply.code(403).send({ error: `Provider '${name}' not in allowlist` });
      }

      try {
        const result = getProvider(name, config, { removeMetaKeys: false });
        const globalConfig = config.get('global') || {};
        const loadResult = config.getLoadResult();
        const appEnv = loadResult?.appEnv || 'dev';

        const proxyResult = resolveProviderProxy(
          name,
          result.config,
          globalConfig,
          appEnv
        );

        return {
          provider_name: name,
          proxy_url: proxyResult.proxyUrl,
          resolution: {
            source: proxyResult.source,
            env_var_used: proxyResult.envVarUsed,
            original_value: proxyResult.originalValue,
            global_proxy: proxyResult.globalProxy,
            app_env: proxyResult.appEnv,
          },
        };
      } catch (err) {
        return reply.code(500).send({ error: err.message });
      }
    });
  }, { prefix: '/healthz/admin/app-yaml-config' });
}
