import { fetchAuthConfig, AuthType, AuthConfig } from '../src/index.js';

describe('fetch-auth-config imports', () => {
    it('should export AuthType', () => {
        expect(AuthType).toBeDefined();
        expect(AuthType.BASIC).toBe('basic');
    });

    it('should export fetchAuthConfig', () => {
        expect(fetchAuthConfig).toBeDefined();
    });
});
