
import { YamlConfigFactory } from '../src/index.js';
import { ContextBuilder } from '../src/context.js';
import { ContextComputeRegistry } from '../src/compute-registry.js';
import { AppYamlConfig } from '@internal/app-yaml-config';

// Mock dependencies
const mockFetchAuthConfig = jest.fn();
const mockEncodeAuth = jest.fn();

describe('Overwrite From Context Integration', () => {
    let mockAppConfig: AppYamlConfig;

    beforeEach(() => {
        // Reset registry and mocks
        jest.clearAllMocks();

        // Mock AppYamlConfig
        mockAppConfig = {
            get: jest.fn(),
            getAll: jest.fn().mockReturnValue({}),
            getLoadResult: jest.fn().mockReturnValue({ appEnv: 'test' }),
            getNested: jest.fn(),
            isInitialized: jest.fn().mockReturnValue(true)
        } as unknown as AppYamlConfig;
    });

    it('should resolve templates in overwrite_from_context', async () => {
        // Setup config with overwrite_from_context
        const rawConfig = {
            base_url: "http://original.com",
            headers: { "X-Original": "true" },
            overwrite_from_context: {
                base_url: "{{env.API_URL}}",
                headers: {
                    "X-Tenant": "{{request.query.tenant_id}}"
                }
            }
        };

        (mockAppConfig.getNested as jest.Mock).mockReturnValue(rawConfig);
        (mockAppConfig.get as jest.Mock).mockImplementation((key: string) => {
            if (key === 'providers') return { test_provider: rawConfig };
            return {};
        });

        // Define Context Environment
        process.env.API_URL = "http://overwritten.com";

        // Setup Factory
        const factory = new YamlConfigFactory(mockAppConfig, mockFetchAuthConfig, mockEncodeAuth);

        // Call compute with request
        const request = {
            query: { tenant_id: "acme-corp" }
        };

        const computeResult = await factory.compute('providers.test_provider', {
            includeConfig: true,
            resolveTemplates: true
        }, request);

        expect(computeResult.config).toMatchObject({
            base_url: "http://overwritten.com",
            headers: {
                "X-Original": "true",
                "X-Tenant": "acme-corp"
            }
        });

        expect(computeResult.config?.overwrite_from_context).toBeUndefined(); // Should be removed
    });

    it('should resolve registered functions', async () => {
        // Register a function
        ContextComputeRegistry.registerRequest('get_custom_token', (ctx, req) => {
            return `token-${req.query.user_id}`;
        });

        const rawConfig = {
            api_key: "default",
            overwrite_from_context: {
                api_key: "{{fn:get_custom_token}}"
            }
        };

        (mockAppConfig.getNested as jest.Mock).mockReturnValue(rawConfig);
        (mockAppConfig.get as jest.Mock).mockImplementation((key: string) => {
            if (key === 'providers') return { test_func: rawConfig };
            return {};
        });

        const factory = new YamlConfigFactory(mockAppConfig, mockFetchAuthConfig, mockEncodeAuth);

        const request = { query: { user_id: '123' } };

        const result = await factory.compute('providers.test_func', {
            includeConfig: true
        }, request);

        expect(result.config?.api_key).toBe('token-123');
    });
});
