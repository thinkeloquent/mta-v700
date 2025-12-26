
import { YamlConfigFactory, ComputeOptions, ContextComputeRegistry } from '../src/index.js';
import { AppYamlConfig } from '@internal/app-yaml-config';
import { fetchAuthConfig } from '@internal/fetch-auth-config';
import { encodeAuth } from '@internal/fetch-auth-encoding';

/**
 * Example demonstrating how to use overwrite_from_context to dynamically
 * update configuration values based on request context or environment variables.
 */
async function main() {
    console.log("Starting overwrite_from_context example...");

    // 1. Register a custom function for context resolution
    // This allows you to use {{fn:get_tenant_token}} in your YAML config
    ContextComputeRegistry.registerRequest('get_tenant_token', (context, request) => {
        const tenantId = request?.query?.tenant_id || 'default-tenant';
        return `token-for-${tenantId}`;
    });

    // 2. Mock AppYamlConfig with a configuration containing overwrite_from_context
    // In a real app, this would come from your YAML files
    const mockAppConfig = {
        getNested: (path: string) => {
            return {
                base_url: "http://original.com",
                api_key: "default-key",
                headers: {
                    "X-Custom": "original"
                },
                overwrite_from_context: {
                    // Resolve {{env.API_URL_OVERRIDE}} from process.env
                    base_url: "{{env.API_URL_OVERRIDE}}",
                    // Resolve {{fn:get_tenant_token}} using our registered function
                    api_key: "{{fn:get_tenant_token}}",
                    headers: {
                        // Resolve deep nested templates
                        "X-Custom": "custom-{{request.query.region}}"
                    }
                }
            };
        },
        get: (key: string) => ({}),
        getLoadResult: () => ({ appEnv: 'dev' }),
        getAll: () => ({})
    } as unknown as AppYamlConfig;

    // 3. Setup Factory
    const factory = new YamlConfigFactory(
        mockAppConfig,
        fetchAuthConfig,
        encodeAuth
    );

    // 4. Setup Environment and Request Context
    process.env.API_URL_OVERRIDE = "http://overwritten-url.com";

    const request = {
        query: {
            tenant_id: "acme-corp",
            region: "us-east"
        }
    };

    // 5. Compute Configuration
    // We must pass includeConfig: true AND resolveTemplates: true
    const result = await factory.compute('providers.test_provider', {
        includeConfig: true,
        resolveTemplates: true
    }, request);

    // 6. Output Result
    console.log("\nComputed Configuration:");
    console.log(JSON.stringify(result.config, null, 2));

    // Expected Output:
    // {
    //   "base_url": "http://overwritten-url.com",
    //   "api_key": "token-for-acme-corp",
    //   "headers": {
    //     "X-Custom": "custom-us-east"
    //   }
    // }
}

main().catch(console.error);
