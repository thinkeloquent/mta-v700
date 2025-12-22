
import { AppYamlConfig } from '../core';
import { getProvider } from '../get_provider/index';
import { ProviderNotFoundError } from '../validators';
import { ProviderConfig } from '../get_provider/provider_config';

describe('getProvider', () => {
    let mockConfigInstance: any;

    beforeEach(() => {
        // Mock the singleton
        // @ts-ignore
        AppYamlConfig['instance'] = null;

        // Create a mock instance with desired config
        const mockConfigData: any = {
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
                },
                array_provider: {
                    api_key: null,
                    overwrite_from_env: {
                        api_key: ['PRIMARY_KEY', 'SECONDARY_KEY']
                    }
                },
                fallback_provider: {
                    api_key: null,
                    overwrite_from_env: {
                        api_key: 'PRIMARY_KEY'
                    },
                    fallbacks_from_env: {
                        api_key: ['FALLBACK_KEY_1']
                    }
                }
            }
        };

        mockConfigInstance = {
            get: (key: string) => mockConfigData[key],
            getAll: () => mockConfigData
        };

        // Spy on getInstance to return our mock
        jest.spyOn(AppYamlConfig, 'getInstance').mockReturnValue(mockConfigInstance as AppYamlConfig);
    });

    afterEach(() => {
        jest.restoreAllMocks();
        delete process.env.TEST_PROVIDER_API_KEY;
        delete process.env.PRIMARY_KEY;
        delete process.env.SECONDARY_KEY;
        delete process.env.FALLBACK_KEY_1;
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

    describe('Array Overwrites and Fallbacks', () => {
        it('should resolve using first available env var in overwrite array', () => {
            process.env.PRIMARY_KEY = 'primary_val';
            process.env.SECONDARY_KEY = 'secondary_val';

            const pc = new ProviderConfig(mockConfigInstance);
            const result = pc.get('array_provider');

            expect(result.config.api_key).toBe('primary_val');
            expect(result.envOverwrites).toContain('api_key');
            expect(result.resolutionSources.api_key).toEqual({ source: 'overwrite', envVar: 'PRIMARY_KEY' });
        });

        it('should resolve using second available env var if first missing', () => {
            // PRIMARY_KEY missing
            process.env.SECONDARY_KEY = 'secondary_val';

            const pc = new ProviderConfig(mockConfigInstance);
            const result = pc.get('array_provider');

            expect(result.config.api_key).toBe('secondary_val');
            expect(result.envOverwrites).toContain('api_key');
            expect(result.resolutionSources.api_key).toEqual({ source: 'overwrite', envVar: 'SECONDARY_KEY' });
        });

        it('should use fallback if overwrite fails', () => {
            // PRIMARY_KEY missing
            process.env.FALLBACK_KEY_1 = 'fallback_val';

            const pc = new ProviderConfig(mockConfigInstance);
            const result = pc.get('fallback_provider');

            expect(result.config.api_key).toBe('fallback_val');
            expect(result.envOverwrites).toContain('api_key');
            expect(result.resolutionSources.api_key).toEqual({ source: 'fallback', envVar: 'FALLBACK_KEY_1' });
        });
    });
});
