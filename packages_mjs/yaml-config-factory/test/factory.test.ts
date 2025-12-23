import { YamlConfigFactory } from '../src/index.js';
import { AuthConfig } from '@internal/fetch-auth-config';

describe('YamlConfigFactory', () => {
    const mockConfig = {
        getNested: (type: string, name: string) => {
            if (type === 'providers' && name === 'test') {
                return { api_auth_type: 'bearer' };
            }
            return undefined;
        }
    } as any;

    it('should compute valid path', () => {
        const mockFetch = jest.fn().mockReturnValue({
            type: 'bearer',
            token: 'resolved-token'
        } as AuthConfig);

        const factory = new YamlConfigFactory(mockConfig, mockFetch);
        const result = factory.compute('providers.test');

        expect(mockFetch).toHaveBeenCalledWith({
            providerName: 'test',
            providerConfig: { api_auth_type: 'bearer' }
        });
        expect(result.authConfig.token).toBe('resolved-token');
    });

    it('should throw on invalid path', () => {
        const factory = new YamlConfigFactory(mockConfig);
        expect(() => factory.compute('invalid')).toThrow('Invalid path format');
        expect(() => factory.compute('badType.name')).toThrow('Invalid config type');
    });

    it('should include headers when requested', () => {
        const mockFetch = jest.fn().mockReturnValue({
            type: 'bearer',
            token: 'xyz'
        } as AuthConfig);

        const mockEncode = jest.fn().mockReturnValue({
            Authorization: 'Bearer xyz'
        });

        const factory = new YamlConfigFactory(mockConfig, mockFetch, mockEncode);
        const result = factory.compute('providers.test', { includeHeaders: true });

        expect(result.headers).toEqual({ Authorization: 'Bearer xyz' });
    });
});
