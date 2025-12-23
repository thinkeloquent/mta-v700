
import { describe, it, expect, beforeEach, jest, afterEach } from '@jest/globals';
import { AppYamlConfig } from '../core';
import { getService, ServiceConfig } from '../get_service/index';
import { ServiceNotFoundError } from '../validators';

describe('getService', () => {
    let mockConfigInstance: any;

    beforeEach(() => {
        // Mock the singleton
        // @ts-ignore
        AppYamlConfig['instance'] = null;

        // Create a mock instance with desired config
        const mockConfigData: any = {
            services: {
                test_service: {
                    api_version: 'v1',
                    headers: { 'X-Test': 'true' },
                    key: null,
                    overwrite_from_env: {
                        key: 'TEST_VAR'
                    }
                },
                array_service: {
                    key: null,
                    overwrite_from_env: {
                        key: ['VAR1', 'VAR2']
                    }
                },
                fallback_service: {
                    key: null,
                    overwrite_from_env: {
                        key: 'PRIMARY'
                    },
                    fallbacks_from_env: {
                        key: ['FB1', 'FB2']
                    }
                },
                meta_service: {
                    key: null,
                    overwrite_from_env: {},
                    fallbacks_from_env: {}
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
        delete process.env.TEST_VAR;
        delete process.env.VAR1;
        delete process.env.VAR2;
        delete process.env.PRIMARY;
        delete process.env.FB1;
        delete process.env.FB2;
    });

    it('should retrieve a basic service', () => {
        const result = getService('test_service');
        expect(result.name).toBe('test_service');
        expect(result.config.api_version).toBe('v1');
        expect(result.config.headers['X-Test']).toBe('true');
    });

    it('should throw ServiceNotFoundError for unknown service', () => {
        expect(() => getService('unknown')).toThrow(ServiceNotFoundError);
    });

    it('should list services', () => {
        const sc = new ServiceConfig();
        const services = sc.listServices();
        expect(services).toContain('test_service');
        expect(services).toContain('array_service');
        expect(services.length).toBe(4);
    });

    it('should check if service exists', () => {
        const sc = new ServiceConfig();
        expect(sc.hasService('test_service')).toBe(true);
        expect(sc.hasService('missing')).toBe(false);
    });

    it('should overwrite with single string env var', () => {
        process.env.TEST_VAR = 'env_value';
        const result = getService('test_service');
        expect(result.config.key).toBe('env_value');
        expect(result.envOverwrites).toContain('key');
        expect(result.resolutionSources.key).toEqual({ source: 'env', envVar: 'TEST_VAR' });
    });

    it('should overwrite with array env var (first found)', () => {
        process.env.VAR1 = 'val1';
        process.env.VAR2 = 'val2';
        const result = getService('array_service');
        expect(result.config.key).toBe('val1');
        expect(result.resolutionSources.key.envVar).toBe('VAR1');
    });

    it('should overwrite with array env var (second found)', () => {
        process.env.VAR2 = 'val2';
        const result = getService('array_service');
        expect(result.config.key).toBe('val2');
        expect(result.resolutionSources.key.envVar).toBe('VAR2');
    });


    it('should remove meta keys from result', () => {
        const result = getService('meta_service');
        expect(result.config.overwrite_from_env).toBeUndefined();
    });
});
