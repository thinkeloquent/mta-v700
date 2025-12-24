/**
 * Tests for config and auth handlers.
 */
import { AuthConfigSchema, resolveConfig, ClientConfigSchema } from '../src/config.js';
import { createAuthHandler } from '../src/auth/auth-handler.js';
import { RequestContext } from '../src/types.js';

describe('AuthConfig Validation', () => {
    test('validates basic auth', () => {
        // Valid
        expect(() => AuthConfigSchema.parse({
            type: 'basic',
            username: 'user',
            password: 'pass'
        })).not.toThrow();

        // Invalid
        expect(() => AuthConfigSchema.parse({
            type: 'basic',
            username: 'user'
        })).toThrow("Basic auth requires 'username' and 'password'");
    });

    test('validates complex bearer', () => {
        // Valid
        expect(() => AuthConfigSchema.parse({
            type: 'bearer_username_token',
            username: 'user',
            rawApiKey: 'token'
        })).not.toThrow();

        // Invalid
        expect(() => AuthConfigSchema.parse({
            type: 'bearer_username_token',
            username: 'user'
        })).toThrow("bearer_username_token requires 'username' and 'rawApiKey'");
    });
});

describe('createAuthHandler', () => {
    test('creates handler for basic auth', () => {
        const config = {
            type: 'basic',
            username: 'user',
            password: 'pass'
        };
        // @ts-ignore
        const handler = createAuthHandler(config);
        const headers = handler.getHeader({} as RequestContext);

        const expectedVal = Buffer.from('user:pass').toString('base64');
        expect(headers).toEqual({ Authorization: `Basic ${expectedVal}` });
    });

    test('creates handler for complex bearer', () => {
        const config = {
            type: 'bearer_username_token',
            username: 'user',
            rawApiKey: 'token'
        };
        // @ts-ignore
        const handler = createAuthHandler(config);
        const headers = handler.getHeader({} as RequestContext);

        const expectedVal = Buffer.from('user:token').toString('base64');
        expect(headers).toEqual({ Authorization: `Bearer ${expectedVal}` });
    });

    test('creates handler for simple bearer', () => {
        const config = {
            type: 'bearer',
            rawApiKey: 'token'
        };
        // @ts-ignore
        const handler = createAuthHandler(config);
        const headers = handler.getHeader({} as RequestContext);

        expect(headers).toEqual({ Authorization: 'Bearer token' });
    });
});

describe('Client Config', () => {
    test('resolves defaults', () => {
        const config = {
            baseUrl: 'https://api.example.com',
            auth: {
                type: 'x-api-key',
                rawApiKey: 'key'
            }
        };
        // @ts-ignore
        const resolved = resolveConfig(config);

        expect(resolved.baseUrl).toBe('https://api.example.com');
        expect(resolved.timeout.connect).toBe(5000);
        expect(resolved.serializer).toBeDefined();
    });
});
