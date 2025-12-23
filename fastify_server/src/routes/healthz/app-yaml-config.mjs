import { AppYamlConfig } from '@internal/app-yaml-config';

export default async function (fastify, opts) {
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
        const authConfig = value.authConfig;
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
}
