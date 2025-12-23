import { ComputeResult } from './types.js';

export function createRuntimeConfigResponse(result: ComputeResult): Record<string, any> {
    const response: Record<string, any> = {
        config_type: result.configType,
        config_name: result.configName,
        auth_config: null,
        proxy_config: null,
        config: result.config
    };

    if (result.authConfig) {
        response.auth_config = {
            type: result.authConfig.type,
            // Add minimal resolution info if available, otherwise just type
            // Future enhancement: plumb resolution source
        };
    }

    if (result.proxyConfig) {
        response.proxy_config = {
            source: result.proxyConfig.source,
            proxy_url: result.proxyConfig.proxyUrl
        };
    }

    return response;
}
