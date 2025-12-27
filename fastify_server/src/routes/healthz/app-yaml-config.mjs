/**
 * AppYamlConfig healthz routes.
 */
import { AppYamlConfig, getProvider, getService, getStorage } from '@internal/app-yaml-config';
import { YamlConfigFactory } from '@internal/yaml-config-factory';

function maskValue(value, visibleChars = 20) {
  if (!value) return null;
  if (value.length <= visibleChars) return '****';
  return `${value.substring(0, visibleChars)}...`;
}

function isSensitiveHeader(headerName) {
  const lower = headerName.toLowerCase();
  // Mask authorization, api-key, token, secret headers
  return lower === 'authorization' ||
    lower.includes('api-key') ||
    lower.includes('apikey') ||
    lower.includes('token') ||
    lower.includes('secret') ||
    lower.includes('password') ||
    lower.includes('credential');
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
      Object.entries(headers || {}).map(([k, v]) => [
        k,
        isSensitiveHeader(k) ? maskValue(v) : v
      ])
    ),
    headersCount: Object.keys(headers || {}).length,
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

    // Helper to format runtime config response
    function formatRuntimeConfig(result) {
      return {
        config_type: result.configType,
        config_name: result.configName,
        auth: result.authConfig ? safeAuthResponse(result.authConfig, result.headers) : null,
        auth_error: result.authError ? {
          message: result.authError.message,
          code: result.authError.code,
          details: result.authError.details
        } : null,
        proxy: result.proxyConfig ? {
          proxy_url: result.proxyConfig.proxyUrl,
          resolution: {
            source: result.proxyConfig.source,
            env_var_used: result.proxyConfig.envVarUsed,
            original_value: result.proxyConfig.originalValue,
            global_proxy: result.proxyConfig.globalProxy,
            app_env: result.proxyConfig.appEnv,
          }
        } : null,
        network: result.networkConfig,
        config: result.config, // Raw merged config
      };
    }

    fastify.get('/provider/:name/fetch/status', async (request, reply) => {
      const { ProviderClient, FetchStatus } = await import('@internal/fetch-client');
      const config = AppYamlConfig.getInstance();
      const name = request.params.name;
      const timeout = parseFloat(request.query.timeout) || 10.0;
      const endpoint = request.query.endpoint || undefined;

      const allowed = config.get('expose_yaml_config_provider') || [];
      if (!allowed.includes(name)) {
        return reply.code(403).send({ error: `Provider '${name}' not in allowlist` });
      }

      let provider;
      let runtimeConfig = null;
      try {
        const factory = new YamlConfigFactory(config);
        runtimeConfig = await factory.computeAll(
          `providers.${name}`,
          undefined,
          request
        );

        // Check for auth errors
        if (runtimeConfig.authError) {
          // Build fetch_option_used manually for error case
          const preComputedHeaders = runtimeConfig.headers || {};
          const configHeaders = runtimeConfig.config.headers || {};
          const mergedHeaders = { ...configHeaders, ...preComputedHeaders };

          // Mask sensitive headers
          const maskedHeaders = {};
          for (const [k, v] of Object.entries(mergedHeaders)) {
            const lower = k.toLowerCase();
            if (['authorization', 'x-api-key', 'api-key', 'token', 'secret'].includes(lower)) {
              maskedHeaders[k] = v && v.length > 20 ? `${v.substring(0, 20)}...` : '****';
            } else {
              maskedHeaders[k] = v;
            }
          }

          return {
            provider_name: name,
            status: "config_error",
            latency_ms: 0,
            timestamp: new Date().toISOString(),
            request: {
              method: runtimeConfig.config.health_endpoint?.method || runtimeConfig.config.method || 'GET',
              url: runtimeConfig.config.base_url,
              timeout_seconds: Math.min(timeout, 30.0)
            },
            error: {
              type: "AuthConfigError",
              message: String(runtimeConfig.authError),
            },
            config_used: {
              base_url: runtimeConfig.config.base_url,
              health_endpoint: runtimeConfig.config.health_endpoint?.path || runtimeConfig.config.health_endpoint || 'UNKNOWN',
              method: runtimeConfig.config.health_endpoint?.method || runtimeConfig.config.method || 'GET',
              timeout_seconds: Math.min(timeout, 30.0),
              auth_type: runtimeConfig.authConfig?.type || null,
              auth_resolved: false,
              auth_header_present: !!mergedHeaders['Authorization'] || !!mergedHeaders['authorization'],
              is_placeholder: runtimeConfig.authConfig?.resolution?.isPlaceholder ?? null,
              proxy_url: runtimeConfig.proxyConfig?.proxyUrl || null,
              proxy_resolved: !!runtimeConfig.proxyConfig?.proxyUrl,
              headers_count: Object.keys(mergedHeaders).length
            },
            fetch_option_used: {
              method: runtimeConfig.config.health_endpoint?.method || runtimeConfig.config.method || 'GET',
              url: runtimeConfig.config.base_url,
              timeout_seconds: Math.min(timeout, 30.0),
              headers: maskedHeaders,
              headers_count: Object.keys(mergedHeaders).length,
              follow_redirects: runtimeConfig.config.follow_redirects ?? true,
              proxy: runtimeConfig.proxyConfig?.proxyUrl || null,
              verify_ssl: runtimeConfig.config.verify_ssl ?? true
            },
            runtime_config: formatRuntimeConfig(runtimeConfig)
          };
        }

        let result;
        try {
          provider = new ProviderClient(
            name,
            runtimeConfig,
            {
              timeoutSeconds: Math.min(timeout, 30.0),
              endpointOverride: endpoint
            }
          );
          result = await provider.checkHealth();
        } catch (e) {
          // Handle constructor validation errors or synchronous checks
          // ProviderClient constructor throws if base_url is missing
          const timestamp = new Date().toISOString();

          // Build fetch_option_used manually for error case
          const preComputedHeaders = runtimeConfig.headers || {};
          const configHeaders = runtimeConfig.config?.headers || {};
          const mergedHeaders = { ...configHeaders, ...preComputedHeaders };

          // Mask sensitive headers
          const maskedHeaders = {};
          for (const [k, v] of Object.entries(mergedHeaders)) {
            const lower = k.toLowerCase();
            if (['authorization', 'x-api-key', 'api-key', 'token', 'secret'].includes(lower)) {
              maskedHeaders[k] = v && v.length > 20 ? `${v.substring(0, 20)}...` : '****';
            } else {
              maskedHeaders[k] = v;
            }
          }

          return {
            provider_name: name,
            status: "config_error",
            latency_ms: 0,
            timestamp,
            request: {
              method: runtimeConfig.config?.health_endpoint?.method || runtimeConfig.config?.method || 'GET',
              url: runtimeConfig.config?.base_url || 'UNKNOWN',
              timeout_seconds: Math.min(timeout, 30.0)
            },
            config_used: {
              base_url: runtimeConfig.config?.base_url || 'UNKNOWN',
              health_endpoint: runtimeConfig.config?.health_endpoint?.path || runtimeConfig.config?.health_endpoint || 'UNKNOWN',
              method: runtimeConfig.config?.health_endpoint?.method || runtimeConfig.config?.method || 'GET',
              timeout_seconds: Math.min(timeout, 30.0),
              auth_type: runtimeConfig.authConfig?.type || null,
              auth_resolved: false,
              auth_header_present: !!mergedHeaders['Authorization'] || !!mergedHeaders['authorization'],
              is_placeholder: null,
              proxy_url: runtimeConfig.proxyConfig?.proxyUrl || null,
              proxy_resolved: !!runtimeConfig.proxyConfig?.proxyUrl,
              headers_count: Object.keys(mergedHeaders).length
            },
            fetch_option_used: {
              method: runtimeConfig.config?.health_endpoint?.method || runtimeConfig.config?.method || 'GET',
              url: runtimeConfig.config?.base_url || 'UNKNOWN',
              timeout_seconds: Math.min(timeout, 30.0),
              headers: maskedHeaders,
              headers_count: Object.keys(mergedHeaders).length,
              follow_redirects: runtimeConfig.config?.follow_redirects ?? true,
              proxy: runtimeConfig.proxyConfig?.proxyUrl || null,
              verify_ssl: runtimeConfig.config?.verify_ssl ?? true
            },
            error: {
              type: "ConfigError",
              message: e.message
            },
            runtime_config: formatRuntimeConfig(runtimeConfig)
          };
        } finally {
          if (provider) await provider.close();
        }

        const formattedConfig = formatRuntimeConfig(runtimeConfig);

        return {
          provider_name: result.provider_name,
          status: result.status,
          latency_ms: result.latency_ms,
          timestamp: result.timestamp,
          request: result.request,
          response: result.response,
          config_used: formattedConfig,
          fetch_option_used: result.fetch_option_used,
          error: result.error,
        };

      } catch (err) {
        request.log.error(err);

        // Build fetch_option_used if runtimeConfig is available
        const timestamp = new Date().toISOString();

        if (runtimeConfig && runtimeConfig.config) {
          const preComputedHeaders = runtimeConfig.headers || {};
          const configHeaders = runtimeConfig.config.headers || {};
          const mergedHeaders = { ...configHeaders, ...preComputedHeaders };

          // Mask sensitive headers
          const maskedHeaders = {};
          for (const [k, v] of Object.entries(mergedHeaders)) {
            const lower = k.toLowerCase();
            if (['authorization', 'x-api-key', 'api-key', 'token', 'secret'].includes(lower)) {
              maskedHeaders[k] = v && v.length > 20 ? `${v.substring(0, 20)}...` : '****';
            } else {
              maskedHeaders[k] = v;
            }
          }

          const method = runtimeConfig.config.health_endpoint?.method || runtimeConfig.config.method || 'GET';
          const healthEndpoint = runtimeConfig.config.health_endpoint?.path || runtimeConfig.config.health_endpoint || 'UNKNOWN';

          return reply.code(500).send({
            provider_name: name,
            status: "error",
            latency_ms: 0,
            timestamp,
            request: {
              method,
              url: runtimeConfig.config.base_url || 'UNKNOWN',
              timeout_seconds: Math.min(timeout, 30.0)
            },
            error: {
              type: err.name || 'Error',
              message: err.message
            },
            config_used: {
              base_url: runtimeConfig.config.base_url || 'UNKNOWN',
              health_endpoint: healthEndpoint,
              method,
              timeout_seconds: Math.min(timeout, 30.0),
              auth_type: runtimeConfig.authConfig?.type || null,
              auth_resolved: !!runtimeConfig.authConfig?.token,
              auth_header_present: !!mergedHeaders['Authorization'] || !!mergedHeaders['authorization'],
              is_placeholder: runtimeConfig.authConfig?.resolution?.isPlaceholder ?? null,
              proxy_url: runtimeConfig.proxyConfig?.proxyUrl || null,
              proxy_resolved: !!runtimeConfig.proxyConfig?.proxyUrl,
              headers_count: Object.keys(mergedHeaders).length
            },
            fetch_option_used: {
              method,
              url: runtimeConfig.config.base_url || 'UNKNOWN',
              timeout_seconds: Math.min(timeout, 30.0),
              headers: maskedHeaders,
              headers_count: Object.keys(mergedHeaders).length,
              follow_redirects: runtimeConfig.config.follow_redirects ?? true,
              proxy: runtimeConfig.proxyConfig?.proxyUrl || null,
              verify_ssl: runtimeConfig.config.verify_ssl ?? true
            },
            runtime_config: formatRuntimeConfig(runtimeConfig)
          });
        }

        // Fallback if runtimeConfig not available
        return reply.code(500).send({
          provider_name: name,
          status: "error",
          latency_ms: 0,
          timestamp,
          request: { method: 'UNKNOWN', url: 'UNKNOWN', timeout_seconds: Math.min(timeout, 30.0) },
          error: {
            type: err.name || 'Error',
            message: err.message
          },
          config_used: {
            base_url: 'UNKNOWN',
            health_endpoint: 'UNKNOWN',
            method: 'UNKNOWN',
            timeout_seconds: Math.min(timeout, 30.0),
            auth_type: null,
            auth_resolved: false,
            auth_header_present: false,
            is_placeholder: null,
            proxy_url: null,
            proxy_resolved: false,
            headers_count: 0
          },
          fetch_option_used: {
            method: 'UNKNOWN',
            url: 'UNKNOWN',
            timeout_seconds: Math.min(timeout, 30.0),
            headers: {},
            headers_count: 0,
            follow_redirects: true,
            proxy: null,
            verify_ssl: true
          }
        });
      }
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

    // ==================== Auth Config Routes (Updated to use YamlConfigFactory) ====================

    fastify.get('/provider/:name/auth_config', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const name = request.params.name;

      const allowed = config.get('expose_yaml_config_provider') || [];
      if (!allowed.includes(name)) {
        return reply.code(403).send({ error: `Provider '${name}' not in allowlist` });
      }

      try {
        const factory = new YamlConfigFactory(config);
        const result = await factory.compute(`providers.${name}`, { includeHeaders: true }, request);
        return safeAuthResponse(result.authConfig, result.headers);
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
        const factory = new YamlConfigFactory(config);
        const result = await factory.compute(`services.${name}`, { includeHeaders: true }, request);
        return safeAuthResponse(result.authConfig, result.headers);
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
        const factory = new YamlConfigFactory(config);
        const result = await factory.compute(`storages.${name}`, { includeHeaders: true }, request);
        return safeAuthResponse(result.authConfig, result.headers);
      } catch (err) {
        return reply.code(500).send({ error: err.message });
      }
    });

    // ==================== Proxy Config Routes (Updated to use YamlConfigFactory) ====================

    fastify.get('/provider/:name/proxy', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const name = request.params.name;

      const allowed = config.get('expose_yaml_config_provider') || [];
      if (!allowed.includes(name)) {
        return reply.code(403).send({ error: `Provider '${name}' not in allowlist` });
      }

      try {
        const factory = new YamlConfigFactory(config);
        const proxyResult = factory.computeProxy(`providers.${name}`);

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

    fastify.get('/provider/:name/runtime_config', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const name = request.params.name;

      const allowed = config.get('expose_yaml_config_provider') || [];
      if (!allowed.includes(name)) {
        return reply.code(403).send({ error: `Provider '${name}' not in allowlist` });
      }

      try {
        const factory = new YamlConfigFactory(config);
        const result = await factory.computeAll(`providers.${name}`, undefined, request);
        return formatRuntimeConfig(result);
      } catch (err) {
        return reply.code(500).send({ error: err.message });
      }
    });

    fastify.get('/service/:name/runtime_config', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const name = request.params.name;

      const allowed = config.get('expose_yaml_config_service') || [];
      if (!allowed.includes(name)) {
        return reply.code(403).send({ error: `Service '${name}' not in allowlist` });
      }

      try {
        const factory = new YamlConfigFactory(config);
        const result = await factory.computeAll(`services.${name}`, undefined, request);
        return formatRuntimeConfig(result);
      } catch (err) {
        return reply.code(500).send({ error: err.message });
      }
    });

    fastify.get('/storage/:name/runtime_config', async (request, reply) => {
      const config = AppYamlConfig.getInstance();
      const name = request.params.name;

      const allowed = config.get('expose_yaml_config_storage') || [];
      if (!allowed.includes(name)) {
        return reply.code(403).send({ error: `Storage '${name}' not in allowlist` });
      }

      try {
        const factory = new YamlConfigFactory(config);
        const result = await factory.computeAll(`storages.${name}`, undefined, request);
        return formatRuntimeConfig(result);
      } catch (err) {
        return reply.code(500).send({ error: err.message });
      }
    });
  }, { prefix: '/healthz/admin/app-yaml-config' });
}
