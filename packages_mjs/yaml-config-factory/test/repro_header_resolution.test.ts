
import { YamlConfigFactory } from '../src/index.js';
import { AppYamlConfig } from '@internal/app-yaml-config';
import { jest } from '@jest/globals';

// Mock dependencies
const mockFetchAuthConfig = jest.fn() as any;
const mockEncodeAuth = jest.fn() as any;

describe('Header Resolution Reproduction', () => {
    let mockAppConfig: AppYamlConfig;

    beforeEach(() => {
        jest.clearAllMocks();
        mockAppConfig = {
            get: jest.fn(),
            getAll: jest.fn().mockReturnValue({}),
            getLoadResult: jest.fn().mockReturnValue({ appEnv: 'test' }),
            getNested: jest.fn(),
            isInitialized: jest.fn().mockReturnValue(true)
        } as unknown as AppYamlConfig;
    });

    it('should resolve header when present in request', async () => {
        const rawConfig = {
            overwrite_from_context: {
                resolved_header: "{{request.headers.x-test-header}}"
            }
        };

        (mockAppConfig.getNested as jest.Mock).mockReturnValue(rawConfig);
        (mockAppConfig.get as jest.Mock).mockReturnValue({
            test_provider: rawConfig
        });

        const factory = new YamlConfigFactory(mockAppConfig, mockFetchAuthConfig, mockEncodeAuth);

        const request = {
            headers: {
                'x-test-header': 'resolved-value'
            }
        };

        const result = await factory.compute('providers.test_provider', {
            includeConfig: true,
            resolveTemplates: true
        }, request);

        expect(result.config?.resolved_header).toBe('resolved-value');
    });

    it('should NOT resolve header when missing in request (returns template)', async () => {
        const rawConfig = {
            overwrite_from_context: {
                resolved_header: "{{request.headers.x-missing-header}}"
            }
        };

        (mockAppConfig.getNested as jest.Mock).mockReturnValue(rawConfig);
        (mockAppConfig.get as jest.Mock).mockReturnValue({
            test_provider: rawConfig
        });

        const factory = new YamlConfigFactory(mockAppConfig, mockFetchAuthConfig, mockEncodeAuth);

        const request = {
            headers: {
                'x-other-header': 'value'
            }
        };

        const result = await factory.compute('providers.test_provider', {
            includeConfig: true,
            resolveTemplates: true
        }, request);

        // Standard behavior of runtime-template-resolver is to keep template if key path missing
        expect(result.config?.resolved_header).toBe('{{request.headers.x-missing-header}}');
    });
});
