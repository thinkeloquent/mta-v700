import { YamlConfigFactory } from '../src/index.js';
import { AuthConfig } from '@internal/fetch-auth-config';

describe('YamlConfigFactory', () => {
    const mockConfig = {
        getNested: (keys: string[]) => {
            const [type, name] = keys;
            if (type === 'providers' && name === 'test') {
                return { api_auth_type: 'bearer' };
            }
            return undefined;
        },
        getAll: () => ({}),
        getLoadResult: () => ({ appEnv: 'test' }),
        get: (key: string) => {
            if (key === 'providers') {
                return {
                    test: { api_auth_type: 'bearer' }
                };
            }
            return {};
        },
        isInitialized: () => true
    } as any;

    it('should compute valid path', async () => {
        const mockFetch = jest.fn().mockReturnValue({
            type: 'bearer',
            token: 'resolved-token'
        } as AuthConfig);

        const factory = new YamlConfigFactory(mockConfig, mockFetch);
        const result = await factory.compute('providers.test');

        expect(mockFetch).toHaveBeenCalledWith({
            providerName: 'test',
            providerConfig: { api_auth_type: 'bearer' },
            request: undefined
        });
        expect(result.authConfig?.token).toBe('resolved-token');
    });

    it('should throw on invalid path', async () => {
        const factory = new YamlConfigFactory(mockConfig);
        await expect(factory.compute('invalid')).rejects.toThrow('Invalid path format');
        await expect(factory.compute('badType.name')).rejects.toThrow('Invalid config type');
    });

    it('should include headers when requested', async () => {
        const mockFetch = jest.fn().mockReturnValue({
            type: 'bearer',
            token: 'xyz'
        } as AuthConfig);

        const mockEncode = jest.fn().mockReturnValue({
            Authorization: 'Bearer xyz'
        });

        const factory = new YamlConfigFactory(mockConfig, mockFetch, mockEncode);
        const result = await factory.compute('providers.test', { includeHeaders: true });

        expect(result.headers).toEqual({ Authorization: 'Bearer xyz' });
    });
});
