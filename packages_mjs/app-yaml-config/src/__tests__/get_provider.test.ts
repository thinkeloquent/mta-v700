
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { AppYamlConfig } from '../core.js';
import { getProvider } from '../get_provider/index.js';
import { ProviderNotFoundError } from '../validators.js';

describe('getProvider', () => {
    let mockConfigInstance: any;

    beforeEach(() => {
        // Mock the singleton
        AppYamlConfig['instance'] = undefined;

        // Create a mock instance with desired config
        const mockConfigData = {
            global: {
                client: {
                    timeout_seconds: 60.0,
                    retries: 3
                },
                network: {
                    default_env: 'dev'
                }
            },
            providers: {
                test_provider: {
                    base_url: 'https://api.test',
                    client: {
                        timeout_seconds: 120.0
                    },
                    api_key: null,
                    overwrite_from_env: {
                        api_key: 'TEST_PROVIDER_API_KEY'
                    }
                },
                no_env_provider: {
                    api_key: 'hardcoded'
                }
            }
        };

        mockConfigInstance = {
            get: (key: string) => mockConfigData[key],
            getAll: () => mockConfigData
        };

        // Spy on getInstance to return our mock
        vi.spyOn(AppYamlConfig, 'getInstance').mockReturnValue(mockConfigInstance as AppYamlConfig);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        delete process.env.TEST_PROVIDER_API_KEY;
    });

    it('should retrieve a provider with merged global config', () => {
        const result = getProvider('test_provider');

        // Global fields
        expect(result.config.network.default_env).toBe('dev');
        expect(result.config.client.retries).toBe(3);

        // Provider overrides
        expect(result.config.base_url).toBe('https://api.test');
        expect(result.config.client.timeout_seconds).toBe(120.0);
    });

    it('should overwrite null value from environment variable', () => {
        process.env.TEST_PROVIDER_API_KEY = 'secret-123';

        const result = getProvider('test_provider');

        expect(result.config.api_key).toBe('secret-123');
        expect(result.envOverwrites).toContain('api_key');
        expect(result.config.overwrite_from_env).toBeUndefined();
    });

    it('should NOT overwrite if value is not null', () => {
        process.env.TEST_PROVIDER_API_KEY = 'secret-123';

        const result = getProvider('no_env_provider');
        expect(result.config.api_key).toBe('hardcoded');
    });

    it('should throw ProviderNotFoundError for missing provider', () => {
        expect(() => getProvider('unknown')).toThrow(ProviderNotFoundError);
    });

    it('should disable global merge when requested', () => {
        const result = getProvider('test_provider', undefined, { mergeGlobal: false });

        expect(result.config.network).toBeUndefined();
        expect(result.config.client.retries).toBeUndefined();
        expect(result.config.client.timeout_seconds).toBe(120.0);
    });
});
