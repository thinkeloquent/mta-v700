
import { describe, expect, it, jest, beforeEach, afterEach } from '@jest/globals';
import { ProviderClient, ComputeAllResult } from '../src/provider/provider-client.js';
import { FetchClient } from '../src/client.js';
import { FetchStatus } from '../src/health/models.js';

// Mock FetchClient
jest.mock('../src/client.js');

describe('ProviderClient', () => {
    let mockClientRequest: any;
    let mockFetchClientCreate: any;
    let mockClose: any;

    beforeEach(() => {
        jest.clearAllMocks();

        mockClientRequest = jest.fn();
        mockClose = jest.fn();

        // Setup FetchClient mock
        (FetchClient as any).create = jest.fn().mockReturnValue({
            request: mockClientRequest,
            close: mockClose
        });
        mockFetchClientCreate = (FetchClient as any).create;
    });

    const validRuntimeConfig: ComputeAllResult = {
        config: {
            base_url: 'https://api.example.com',
            health_endpoint: '/health',
            headers: { 'X-Config-Header': 'config-val' }
        },
        headers: {
            'Authorization': 'Bearer token-123',
            'X-Precomputed': 'pre-val'
        },
        authConfig: {
            type: 'bearer',
            token: 'token-123',
            username: 'testuser'
        }
    };

    describe('Constructor', () => {
        it('should create instance with valid config', () => {
            const client = new ProviderClient('test-provider', validRuntimeConfig);
            expect(client).toBeInstanceOf(ProviderClient);
        });

        it('should throw if base_url is missing', () => {
            const invalidConfig = { config: {} } as any;
            expect(() => new ProviderClient('test', invalidConfig)).toThrow(/base_url is required/);
        });
    });

    describe('Client Creation & Requests', () => {
        it('should create client lazily with merged headers', async () => {
            const provider = new ProviderClient('test', validRuntimeConfig);

            // Client not created yet
            expect(mockFetchClientCreate).not.toHaveBeenCalled();

            mockClientRequest.mockResolvedValue({ status: 200, data: {} });

            // First request triggers creation
            await provider.get('/foo');

            expect(mockFetchClientCreate).toHaveBeenCalledTimes(1);
            const createArgs = mockFetchClientCreate.mock.calls[0][0];
            expect(createArgs.baseUrl).toBe('https://api.example.com');
            // Headers should be merged (pre-computed overrides config)
            expect(createArgs.headers).toEqual({
                'X-Config-Header': 'config-val',
                'Authorization': 'Bearer token-123',
                'X-Precomputed': 'pre-val'
            });
        });

        it('should delegate get() to client.request', async () => {
            const provider = new ProviderClient('test', validRuntimeConfig);
            mockClientRequest.mockResolvedValue({ status: 200, data: 'ok' });

            await provider.get('/users', { query: { id: 1 } });

            expect(mockClientRequest).toHaveBeenCalledWith(expect.objectContaining({
                method: 'GET',
                url: '/users',
                query: { id: 1 }
            }));
        });

        it('should reuse client instance', async () => {
            const provider = new ProviderClient('test', validRuntimeConfig);
            mockClientRequest.mockResolvedValue({ status: 200 });

            await provider.get('/1');
            await provider.get('/2');

            expect(mockFetchClientCreate).toHaveBeenCalledTimes(1);
        });
    });

    describe('checkHealth', () => {
        it('should return CONNECTED on 200 OK', async () => {
            const provider = new ProviderClient('test', validRuntimeConfig);

            mockClientRequest.mockResolvedValue({
                status: 200,
                statusText: 'OK',
                headers: new Map([['content-type', 'application/json']]),
                data: { status: 'ok' }
            });

            const result = await provider.checkHealth();

            expect(result.status).toBe(FetchStatus.CONNECTED);
            expect(result.provider_name).toBe('test');
            expect(result.response?.status_code).toBe(200);
            expect(mockClientRequest).toHaveBeenCalledWith(expect.objectContaining({
                method: 'GET',
                url: '/health'
            }));
        });

        it('should resolve placeholders in health endpoint', async () => {
            const configWithPlaceholder: ComputeAllResult = {
                config: {
                    base_url: 'http://api.com',
                    health_endpoint: '/users/:username/health'
                },
                authConfig: { username: 'alice' }
            };

            const provider = new ProviderClient('test', configWithPlaceholder);
            mockClientRequest.mockResolvedValue({ status: 200 });

            await provider.checkHealth();

            expect(mockClientRequest).toHaveBeenCalledWith(expect.objectContaining({
                url: '/users/alice/health'
            }));
        });

        it('should handle timeout errors', async () => {
            const provider = new ProviderClient('test', validRuntimeConfig);

            const error: any = new Error('Timeout');
            error.name = 'ConnectTimeoutError';

            mockClientRequest.mockRejectedValue(error);

            const result = await provider.checkHealth();

            expect(result.status).toBe(FetchStatus.TIMEOUT);
            expect(result.error?.type).toBe('TimeoutException');
        });

        it('should return CONFIG_ERROR if endpoint resolution fails', async () => {
            // Missing username for placeholder
            const configWithPlaceholder: ComputeAllResult = {
                config: {
                    base_url: 'http://api.com',
                    health_endpoint: { path: '' } // Invalid
                }
            };

            const provider = new ProviderClient('test', configWithPlaceholder);
            const result = await provider.checkHealth();

            expect(result.status).toBe(FetchStatus.CONFIG_ERROR);
            expect(result.error?.message).toMatch(/missing 'path'/);
        });
    });

    describe('Diagnostics', () => {
        it('getConfigUsed should return correct structure', () => {
            const provider = new ProviderClient('test', validRuntimeConfig);
            const info = provider.getConfigUsed();

            expect(info.baseUrl).toBe('https://api.example.com');
            expect(info.healthEndpoint).toBe('/health'); // resolved
            expect(info.authResolved).toBe(true);
            expect(info.authHeaderPresent).toBe(true);
        });

        it('getFetchOptionUsed should mask sensitive headers', () => {
            const provider = new ProviderClient('test', validRuntimeConfig);
            const info = provider.getFetchOptionUsed();

            expect(info.headers['Authorization']).toBe('****');
            expect(info.headers['X-Config-Header']).toBe('config-val');
        });

        it('getFetchOptionUsed should mask proxy credentials', () => {
            const proxyConfig: ComputeAllResult = {
                ...validRuntimeConfig,
                proxyConfig: { proxyUrl: 'http://user:pass@proxy.com:8080' }
            };

            const provider = new ProviderClient('test', proxyConfig);
            const info = provider.getFetchOptionUsed();

            expect(info.proxy).toBe('http://user:****@proxy.com:8080');
        });
    });
});
