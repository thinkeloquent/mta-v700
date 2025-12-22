/**
 * Proxy URL resolution logic.
 */
import { NetworkConfig } from "./types";

export function resolveProxyUrl(
    networkConfig?: NetworkConfig | null,
    proxyUrlOverride?: string | false | null
): string | null {
    // 1. Explicit disable
    if (proxyUrlOverride === false) {
        return null;
    }

    // 2. Explicit override
    if (typeof proxyUrlOverride === "string" && proxyUrlOverride) {
        return proxyUrlOverride;
    }

    // Check network config sources
    if (networkConfig) {
        // 3 & 4. Agent proxy config
        if (networkConfig.agentProxy) {
            if (networkConfig.agentProxy.httpsProxy) {
                return networkConfig.agentProxy.httpsProxy;
            }
            if (networkConfig.agentProxy.httpProxy) {
                return networkConfig.agentProxy.httpProxy;
            }
        }

        // 5. Environment-specific proxy URL
        if (networkConfig.defaultEnvironment && networkConfig.proxyUrls) {
            const envProxy = networkConfig.proxyUrls[networkConfig.defaultEnvironment];
            if (envProxy) {
                return envProxy;
            }
        }
    }

    // Env var fallback
    // 6. PROXY_URL
    if (process.env.PROXY_URL) {
        return process.env.PROXY_URL;
    }

    // 7. HTTPS_PROXY
    if (process.env.HTTPS_PROXY) {
        return process.env.HTTPS_PROXY;
    }

    // 8. HTTP_PROXY
    if (process.env.HTTP_PROXY) {
        return process.env.HTTP_PROXY;
    }

    return null;
}
