
import { describe, it, expect, beforeEach, jest, afterEach } from '@jest/globals';
import { AppYamlConfig } from '../core';
import { getStorage, StorageConfig } from '../get_storage/index';
import { StorageNotFoundError } from '../validators';

describe('getStorage', () => {
    let mockConfigInstance: any;

    beforeEach(() => {
        // Mock the singleton
        // @ts-ignore
        AppYamlConfig['instance'] = null;

        // Create a mock instance with desired config
        const mockConfigData: any = {
            storage: {
                redis: {
                    host: 'localhost',
                    port: 6379
                },
                redis_env: {
                    host: null,
                    port: null,
                    overwrite_from_env: {
                        host: 'REDIS_HOST',
                        port: 'REDIS_PORT'
                    }
                },
                redis_fallback: {
                    host: null,
                    overwrite_from_env: {
                        host: 'PRIMARY_HOST'
                    }
                },
                mixed: {
                    host: 'explicit_host', // Should not be overwritten
                    port: null,
                    overwrite_from_env: {
                        host: 'REDIS_HOST',
                        port: 'REDIS_PORT'
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
        delete process.env.REDIS_HOST;
        delete process.env.REDIS_PORT;
        delete process.env.PRIMARY_HOST;
        delete process.env.FALLBACK_HOST_1;
        delete process.env.FALLBACK_HOST_2;
    });

    it('should retrieve a basic storage', () => {
        const result = getStorage('redis');
        expect(result.name).toBe('redis');
        expect(result.config.host).toBe('localhost');
        expect(result.config.port).toBe(6379);
        expect(result.envOverwrites).toHaveLength(0);
    });

    it('should throw StorageNotFoundError for unknown storage', () => {
        expect(() => getStorage('unknown')).toThrow(StorageNotFoundError);
    });

    it('should list storages', () => {
        const sc = new StorageConfig();
        const storages = sc.listStorages();
        expect(storages).toContain('redis');
        expect(storages).toContain('redis_env');
        expect(storages.length).toBe(4);
    });

    it('should check if storage exists', () => {
        const sc = new StorageConfig();
        expect(sc.hasStorage('redis')).toBe(true);
        expect(sc.hasStorage('unknown')).toBe(false);
    });

    it('should overwrite from primary env key', () => {
        process.env.REDIS_HOST = 'env_host';
        process.env.REDIS_PORT = '6380';
        const result = getStorage('redis_env');
        expect(result.config.host).toBe('env_host');
        expect(result.config.port).toBe('6380');
        expect(result.envOverwrites).toContain('host');
        expect(result.envOverwrites).toContain('port');
        expect(result.resolutionSources.host).toEqual({ source: 'env', envVar: 'REDIS_HOST' });
    });


    it('should prefer primary', () => {
        process.env.PRIMARY_HOST = 'primary_val';
        process.env.FALLBACK_HOST_1 = 'fallback_val';
        const result = getStorage('redis_fallback');
        expect(result.config.host).toBe('primary_val');
        expect(result.resolutionSources.host.source).toBe('env');
    });

    it('should NOT overwrite non-null values', () => {
        process.env.REDIS_HOST = 'env_host';
        process.env.REDIS_PORT = '9999';
        const result = getStorage('mixed');
        expect(result.config.host).toBe('explicit_host'); // Preserved
        expect(result.config.port).toBe('9999'); // Overwritten
    });

    it('should remove meta keys by default', () => {
        const result = getStorage('redis_env');
        expect(result.config.overwrite_from_env).toBeUndefined();
    });

    it('should keep meta keys if requested', () => {
        const result = getStorage('redis_env', undefined, { removeMetaKeys: false });
        expect(result.config.overwrite_from_env).toEqual({
            host: 'REDIS_HOST',
            port: 'REDIS_PORT'
        });
    });
});
