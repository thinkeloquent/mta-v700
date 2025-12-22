/**
 * Factory for creating proxy-configured HTTP clients.
 */
import { resolveProxyUrl, NetworkConfig, parseNetworkConfig } from "@internal/proxy-config";
import { FactoryConfigSchema, FactoryConfig, DispatcherResult, ProxyConfig } from "./types";
import { getAppEnv, isSslVerifyDisabledByEnv } from "./config";
import { getAdapter, BaseAdapter } from "./adapters";

export class ProxyDispatcherFactory {
    private config: FactoryConfig;
    private adapter: BaseAdapter;

    constructor(config?: FactoryConfig, adapterName: string = "undici") {
        this.config = config || {};
        this.adapter = getAdapter(adapterName);
    }

    getProxyDispatcher(options: {
        environment?: string;
        disableTls?: boolean;
        timeout?: number; // ms
    } = {}): DispatcherResult {
        // 1. Determine environment
        const targetEnv = options.environment || this.config.defaultEnvironment || getAppEnv();

        // 2. Resolve Proxy URL
        const networkConfig: NetworkConfig = {
            defaultEnvironment: this.config.defaultEnvironment || null,
            proxyUrls: this.config.proxyUrls || {},
            agentProxy: this.config.agentProxy,
            cert: this.config.cert,
            caBundle: this.config.caBundle,
            certVerify: this.config.certVerify ?? false
        };

        let proxyUrlOverride: string | false | null | undefined;
        if (this.config.proxyUrl === true) {
            proxyUrlOverride = null;
        } else {
            proxyUrlOverride = this.config.proxyUrl;
        }

        const proxyUrl = resolveProxyUrl(
            networkConfig,
            proxyUrlOverride
        );

        // 3. Determine SSL Settings
        let verifySsl = true;
        if (options.disableTls === true) {
            verifySsl = false;
        } else if (this.config.certVerify === false || this.config.certVerify === true) {
            verifySsl = this.config.certVerify;
        } else if (isSslVerifyDisabledByEnv()) {
            verifySsl = false;
        }

        // 4. Build ProxyConfig
        const proxyConfig: ProxyConfig = {
            proxyUrl,
            verifySsl,
            timeout: options.timeout || 30000,
            trustEnv: false,
            cert: this.config.cert,
            caBundle: this.config.caBundle
        };

        // 5. Create Client
        return this.adapter.createClient(proxyConfig);
    }

    getDispatcherForEnvironment(environment: string): DispatcherResult {
        return this.getProxyDispatcher({ environment });
    }

    getDispatcherOptions(options: { timeout?: number } = {}): Record<string, any> {
        const result = this.getProxyDispatcher({ timeout: options.timeout });
        return result.proxyDict;
    }
}
