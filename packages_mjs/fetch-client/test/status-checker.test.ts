import { jest } from '@jest/globals';
import { FetchStatusChecker } from '../src/health/status-checker.js';
import { FetchStatus } from '../src/health/models.js';
import { FetchClient } from '../src/client.js';

describe('FetchStatusChecker', () => {
    let mockRuntimeConfig;

    beforeEach(() => {
        mockRuntimeConfig = {
            config: {
                base_url: 'https://api.example.com',
                health_endpoint: '/health',
                headers: { 'Accept': 'application/json' }
            },
            authConfig: {
                type: 'bearer',
                token: 'test-token',
                resolution: { is_placeholder: false }
            }
        };
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    it('should return CONNECTED status on successful request', async () => {
        // Mock FetchClient.create and its instance logic
        const mockClient = {
            request: (jest.fn() as any).mockResolvedValue({
                status: 200,
                statusText: 'OK',
                headers: new Map([['content-type', 'application/json']]),
                data: '{"status":"ok"}',
            }),
            close: jest.fn()
        };

        const createSpy = jest.spyOn(FetchClient, 'create').mockReturnValue(mockClient as any);

        const checker = new FetchStatusChecker('test-provider', mockRuntimeConfig);
        const result = await checker.check();

        expect(result.status).toBe(FetchStatus.CONNECTED);
        expect(result.latency_ms).toBeGreaterThan(0);
        expect(result.response?.status_code).toBe(200);
        expect(createSpy).toHaveBeenCalled();
        expect(mockClient.request).toHaveBeenCalledWith(expect.objectContaining({
            method: 'GET',
            url: '/health'
        }));
    });

    it('should return CONFIG_ERROR when base_url is missing', async () => {
        mockRuntimeConfig.config = {}; // Remove base_url

        const checker = new FetchStatusChecker('test-provider', mockRuntimeConfig);
        const result = await checker.check();

        expect(result.status).toBe(FetchStatus.CONFIG_ERROR);
        expect(result.error?.message).toContain('base_url is required');
    });

    it('should handle request timeout', async () => {
        const mockClient = {
            request: (jest.fn() as any).mockRejectedValue({
                name: 'ConnectTimeoutError',
                code: 'UND_ERR_CONNECT_TIMEOUT',
                message: 'Connect Timeout'
            }),
            close: jest.fn()
        };
        jest.spyOn(FetchClient, 'create').mockReturnValue(mockClient as any);

        const checker = new FetchStatusChecker('test-provider', mockRuntimeConfig);
        const result = await checker.check();

        expect(result.status).toBe(FetchStatus.TIMEOUT);
        expect(result.error?.type).toBe('TimeoutException');
    });

    it('should handle connection error', async () => {
        const mockClient = {
            request: (jest.fn() as any).mockRejectedValue({
                name: 'SocketError',
                code: 'UND_ERR_SOCKET',
                message: 'Socket Error'
            }),
            close: jest.fn()
        };
        jest.spyOn(FetchClient, 'create').mockReturnValue(mockClient as any);

        const checker = new FetchStatusChecker('test-provider', mockRuntimeConfig);
        const result = await checker.check();

        expect(result.status).toBe(FetchStatus.CONNECTION_ERROR);
        expect(result.error?.type).toBe('ConnectError');
    });

    it('should use configured method from config top-level', async () => {
        mockRuntimeConfig.config.method = 'post';
        const mockClient = {
            request: (jest.fn() as any).mockResolvedValue({ status: 200, headers: {}, data: '' }),
            close: jest.fn()
        };
        jest.spyOn(FetchClient, 'create').mockReturnValue(mockClient as any);

        const checker = new FetchStatusChecker('test-provider', mockRuntimeConfig);
        await checker.check();

        expect(mockClient.request).toHaveBeenCalledWith(expect.objectContaining({
            method: 'POST'
        }));
    });

    it('should resolve method and path from health_endpoint object', async () => {
        mockRuntimeConfig.config.health_endpoint = { path: '/status', method: 'head' };
        const mockClient = {
            request: (jest.fn() as any).mockResolvedValue({ status: 200, headers: {}, data: '' }),
            close: jest.fn()
        };
        jest.spyOn(FetchClient, 'create').mockReturnValue(mockClient as any);

        const checker = new FetchStatusChecker('test-provider', mockRuntimeConfig);
        await checker.check();

        expect(mockClient.request).toHaveBeenCalledWith(expect.objectContaining({
            method: 'HEAD',
            url: '/status'
        }));
    });

    it('should return fetch_option_used with masked headers', async () => {
        mockRuntimeConfig.headers = { 'Authorization': 'Bearer secret-token' };
        const mockClient = {
            request: (jest.fn() as any).mockResolvedValue({ status: 200, headers: {}, data: '' }),
            close: jest.fn()
        };
        jest.spyOn(FetchClient, 'create').mockReturnValue(mockClient as any);

        const checker = new FetchStatusChecker('test-provider', mockRuntimeConfig);
        const result = await checker.check();

        expect(result.fetch_option_used).toBeDefined();
        expect(result.fetch_option_used?.method).toBe('GET');
        expect(result.fetch_option_used?.headers['Authorization']).toBe('****');
    });
});
