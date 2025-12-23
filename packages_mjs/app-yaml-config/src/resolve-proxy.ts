
export interface ProxyResolutionResult {
    proxyUrl: string | null;
    source: 'disabled' | 'env_overwrite' | 'provider_direct' | 'env_proxy' | 'global_fallback';
    envVarUsed?: string;
    originalValue: any;
    globalProxy?: string;
    appEnv: string;
}

export function resolveProviderProxy(
    providerName: string,
    providerConfig: Record<string, any>,
    globalConfig: Record<string, any>,
    appEnv: string
): ProxyResolutionResult {
    const originalValue = providerConfig.proxy_url;
    const globalProxy = globalConfig?.network?.proxy_urls?.[appEnv] || null;

    // Base result
    const result: ProxyResolutionResult = {
        proxyUrl: null,
        source: 'disabled',
        originalValue,
        globalProxy,
        appEnv,
    };

    // 1. Check overwrite_from_env.proxy_url first
    const overwriteFromEnv = providerConfig.overwrite_from_env;
    if (overwriteFromEnv?.proxy_url) {
        const envVarNames = Array.isArray(overwriteFromEnv.proxy_url)
            ? overwriteFromEnv.proxy_url
            : [overwriteFromEnv.proxy_url];

        for (const envVarName of envVarNames) {
            const envValue = process.env[envVarName];
            if (envValue !== undefined && envValue !== '') {
                result.proxyUrl = envValue;
                result.source = 'env_overwrite';
                result.envVarUsed = envVarName;
                return result;
            }
        }
    }

    // 2. Resolve based on proxy_url value type
    if (originalValue === false) {
        // Explicitly disabled
        result.proxyUrl = null;
        result.source = 'disabled';
        return result;
    }

    if (originalValue === null || originalValue === undefined) {
        // Inherit from global
        result.proxyUrl = globalProxy;
        result.source = 'global_fallback';
        return result;
    }

    if (originalValue === true) {
        // Use standard env vars
        const httpsProxy = process.env.HTTPS_PROXY || process.env.https_proxy;
        const httpProxy = process.env.HTTP_PROXY || process.env.http_proxy;
        const envProxy = httpsProxy || httpProxy;

        result.proxyUrl = envProxy || null;
        result.source = 'env_proxy';
        result.envVarUsed = httpsProxy ? 'HTTPS_PROXY' : (httpProxy ? 'HTTP_PROXY' : undefined);
        return result;
    }

    if (typeof originalValue === 'string') {
        // Direct URL/IP value
        result.proxyUrl = originalValue;
        result.source = 'provider_direct';
        return result;
    }

    // Fallback: treat as null (inherit global)
    result.proxyUrl = globalProxy;
    result.source = 'global_fallback';
    return result;
}
