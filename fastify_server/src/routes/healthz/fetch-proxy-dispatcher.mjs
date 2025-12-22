/**
 * Fetch Proxy Dispatcher health check.
 */
import { AppYamlConfig } from '@internal/app-yaml-config';
import { ProxyDispatcherFactory, FactoryConfigSchema } from '@internal/proxy-dispatcher';

export default async function fetchProxyDispatcherRoutes(fastify) {
    fastify.get('/healthz/fetch-proxy-dispatcher', async (request, reply) => {
        // 1. Get singleton config
        const config = AppYamlConfig.getInstance();

        // 2. Get network config (raw dict access)
        // Access global.network.proxy_urls
        const globalConfig = config.get('global') || {};
        const networkConfig = globalConfig.network || {};

        // 3. Use ProxyDispatcher to resolve
        // Map raw config to FactoryConfig structure
        const factoryConfigData = {
            defaultEnvironment: networkConfig.default_environment,
            proxyUrls: networkConfig.proxy_urls,
            agentProxy: networkConfig.agent_proxy, // camelCase mapping might be needed if raw yaml is snake_case?
            // Wait, app-yaml-config loads raw yaml, so keys are usually snake_case.
            // ProxyDispatcherFactory expects camelCase config object (FactoryConfig).
            // networkConfig is from yaml, so snake_case keys.
            // We need to map manually.

            caBundle: networkConfig.ca_bundle,
            cert: networkConfig.cert,
            certVerify: networkConfig.cert_verify
        };

        // agent_proxy in yaml is snake_case: { http_proxy: ..., https_proxy: ... }
        // FactoryConfig.agentProxy expects { httpProxy: ..., httpsProxy: ... }
        if (networkConfig.agent_proxy) {
            factoryConfigData.agentProxy = {
                httpProxy: networkConfig.agent_proxy.http_proxy,
                httpsProxy: networkConfig.agent_proxy.https_proxy
            };
        }

        // FactoryConfig from @internal/proxy-dispatcher is camelCase
        // We already mapped above.

        const factory = new ProxyDispatcherFactory(factoryConfigData);

        const result = factory.getProxyDispatcher();

        return {
            status: 'ok',
            resolved_proxy_url: result.config.proxyUrl,
            config_source: {
                default_environment: factoryConfigData.defaultEnvironment,
                proxy_urls_keys: networkConfig.proxy_urls ? Object.keys(networkConfig.proxy_urls) : [],
            },
            dispatcher_config: result.config
        };
    });
}
