
import { jest, describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { YamlConfigFactory, ComputeOptions } from '../src/index';
import { AppYamlConfig, ProxyResolutionResult } from '@internal/app-yaml-config';
import { AuthType } from '@internal/fetch-auth-config';

// Mock Dependencies
const mockAppConfig = {
    get: jest.fn(),
    getNested: jest.fn(),
    getLoadResult: jest.fn().mockReturnValue({ appEnv: 'dev', filesLoaded: [] })
} as unknown as AppYamlConfig;

const mockFetchAuth = jest.fn();
const mockEncodeAuth = jest.fn();

// Spy Helper
function setupConsoleSpy() {
    return {
        debug: jest.spyOn(console, 'debug').mockImplementation(() => { }),
        error: jest.spyOn(console, 'error').mockImplementation(() => { }),
    };
}

function restoreConsoleSpy(spies: any) {
    spies.debug.mockRestore();
    spies.error.mockRestore();
}

function expectLogContains(spy: any, text: string) {
    const calls = spy.mock.calls.flat().join(' ');
    expect(calls).toContain(text);
}

describe('YamlConfigFactory Optimization', () => {
    let factory: YamlConfigFactory;
    let consoleSpy: any;

    beforeEach(() => {
        jest.clearAllMocks();
        consoleSpy = setupConsoleSpy();
        factory = new YamlConfigFactory(
            mockAppConfig,
            mockFetchAuth as any,
            mockEncodeAuth as any,
            console // Pass real console, but methods are spied on
        );
    });

    afterEach(() => {
        restoreConsoleSpy(consoleSpy);
    });


    // =========================================================================
    // Statement & Branch Coverage
    // =========================================================================

    describe('compute() - Branch Coverage', () => {
        it('should compute only auth by default', () => {
            (mockAppConfig as any).getNested.mockReturnValue({ some: 'config' });
            mockFetchAuth.mockReturnValue({
                type: AuthType.BEARER,
                providerName: 'test',
                resolution: { tokenResolver: 'static', resolvedFrom: {}, isPlaceholder: false }
            });

            const result = factory.compute('providers.test');

            expect(result.authConfig).toBeDefined();
            expect(result.proxyConfig).toBeUndefined();
            expect(result.networkConfig).toBeUndefined();
            expect(result.config).toBeUndefined();

            expectLogContains(consoleSpy.debug, 'compute: Starting');
            expectLogContains(consoleSpy.debug, 'compute: Completed');
        });

        it('should compute all sections when requested', () => {
            // Setup Mocks
            (mockAppConfig as any).getNested.mockImplementation((type: string, name: string) => ({
                some: 'config',
                proxy_url: false
            }));
            (mockAppConfig as any).get.mockReturnValue({
                network: { default_environment: 'prod' }
            });
            mockFetchAuth.mockReturnValue({
                type: AuthType.NONE,
                providerName: 'test',
                resolution: { tokenResolver: 'static', resolvedFrom: {}, isPlaceholder: false }
            });

            const result = factory.compute('providers.test', {
                includeHeaders: true,
                includeProxy: true,
                includeNetwork: true,
                includeConfig: true
            });

            expect(result.authConfig).toBeDefined();
            expect(result.proxyConfig).toBeDefined();
            expect(result.networkConfig).toBeDefined();
            expect(result.config).toBeDefined();

            expectLogContains(consoleSpy.debug, 'compute: Resolving proxy');
            expectLogContains(consoleSpy.debug, 'compute: Resolving network config');
            expectLogContains(consoleSpy.debug, 'compute: Retrieving raw config');
        });
    });

    // =========================================================================
    // Boundary Value Analysis
    // =========================================================================

    describe('compute() - Boundary Values', () => {
        it('should throw Error for empty path', () => {
            expect(() => factory.compute('')).toThrow('Path cannot be empty');
            expectLogContains(consoleSpy.error, 'compute failed');
        });

        it('should throw Error for malformed path', () => {
            expect(() => factory.compute('providers')).toThrow("Invalid path format 'providers'");
        });

        it('should throw Error for invalid config type', () => {
            expect(() => factory.compute('invalid.test')).toThrow("Invalid config type 'invalid'");
        });

        it('should throw Error if config not found', () => {
            (mockAppConfig as any).getNested.mockReturnValue(undefined);
            (mockAppConfig as any).get.mockReturnValue(undefined);

            expect(() => factory.compute('providers.missing')).toThrow("Configuration not found for 'providers.missing'");
        });
    });


    // =========================================================================
    // Integration / Logic Tests
    // =========================================================================

    describe('computeProxy() Logic', () => {
        it('should resolve proxy correctly', () => {
            // Setup
            const rawConfig = { proxy_url: 'http://custom-proxy' };
            (mockAppConfig as any).getNested.mockReturnValue(rawConfig);

            const result = factory.computeProxy('providers.test', 'prod');

            expect(result.proxyUrl).toBe('http://custom-proxy');
            expect(result.source).toBe('provider_direct'); // Assuming resolveProviderProxy logic
        });
    });

    describe('computeNetwork() Logic', () => {
        it('should map complex network config', () => {
            const globalNet = {
                network: {
                    default_environment: 'staging',
                    proxy_urls: { dev: 'http://dev', staging: 'http://stage' },
                    agent_proxy: { http_proxy: 'http://agent' }
                }
            };
            (mockAppConfig as any).get.mockReturnValue(globalNet);

            const result = factory.computeNetwork();

            expect(result.defaultEnvironment).toBe('staging');
            expect(result.proxyUrls['staging']).toBe('http://stage');
            expect(result.agentProxy?.httpProxy).toBe('http://agent');
        });
    });
});
