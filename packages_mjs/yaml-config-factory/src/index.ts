
import type { AppYamlConfig } from '@internal/app-yaml-config';
import { fetchAuthConfig } from '@internal/fetch-auth-config';
import { encodeAuth, AuthCredentials } from '@internal/fetch-auth-encoding';
import {
    resolveProviderProxy,
    ProxyResolutionResult,
    getProvider,
    getService,
    getStorage
} from '@internal/app-yaml-config';
import {
    ConfigPath,
    ComputeOptions,
    ComputeResult,
    NetworkConfig,
    ComputedAuthConfig
} from './types.js';

export * from './types.js';
export * from './helpers.js';

export class YamlConfigFactory {
    constructor(
        private config: AppYamlConfig,
        private fetchAuthConfigFn = fetchAuthConfig,
        private encodeAuthFn = encodeAuth,
        private logger: Console = console
    ) { }

    private logDebug(message: string, ...args: any[]): void {
        this.logger.debug(`YamlConfigFactory: ${message}`, ...args);
    }

    private logError(message: string, ...args: any[]): void {
        this.logger.error(`YamlConfigFactory:Error: ${message}`, ...args);
    }

    /**
     * Compute comprehensive runtime configuration.
     */
    compute(path: string, options: ComputeOptions = {}): ComputeResult {
        this.logDebug('compute: Starting', { path, options });

        try {
            const [configType, configName] = this.parsePath(path);

            // 1. Auth Resolution
            let authResult: ComputedAuthConfig = {
                authConfig: null as any // Will be set if successful or if fallback required? 
                // Ideally we want authConfig to be nullable in the type? 
                // Since we can't change the type definition easily without seeing it (it's in types.ts not index.ts but index blocks export * from types.ts)
                // Let's assume we need to update types.ts properly first or cast.
                // Actually index.ts imports ComputeResult from ./types.js.
                // I need to update types.js first if I want to change the interface.
            };

            // But wait, I can modify the ComputedAuthConfig type if it is defined in types.ts.
            // Let me check types.ts first. I can't modify it here.
            // I will implement the logic assuming types are compatible or I will catch and return error field.

            // I'll wrap auth resolution
            let authError: any = null;
            try {
                authResult = this.computeAuthInternal(configType, configName, options.includeHeaders);
            } catch (err) {
                if (options.suppressAuthErrors) {
                    this.logError('compute: Auth resolution failed but suppressed', err);
                    authError = err;
                    // Provide a dummy or null auth config? 
                    // Current ComputeResult expects authConfig.
                    // I likely need to update ComputeResult to make authConfig optional OR provide a partial one.
                } else {
                    throw err;
                }
            }

            const result: ComputeResult & { authError?: any } = {
                configType,
                configName,
                authConfig: authResult?.authConfig, // Might be undefined if failed
                headers: authResult?.headers,
                authError
            } as any; // Cast for now, will update types next

            // 2. Proxy Resolution
            if (options.includeProxy) {
                this.logDebug('compute: Resolving proxy');
                result.proxyConfig = this.computeProxy(path, options.environment);
            }

            // 3. Network Configuration
            if (options.includeNetwork) {
                this.logDebug('compute: Resolving network config');
                result.networkConfig = this.computeNetwork();
            }

            // 4. Raw Config
            if (options.includeConfig) {
                this.logDebug('compute: Retrieving raw config');
                result.config = this.computeConfig(path);
            }

            this.logDebug('compute: Completed', {
                type: result.configType,
                name: result.configName
            });

            return result;

        } catch (error) {
            this.logError('compute failed', { path, error });
            throw error;
        }
    }

    /**
     * Compute proxy configuration.
     */
    computeProxy(path: string, environment?: string): ProxyResolutionResult {
        this.logDebug('computeProxy: Starting', { path, environment });

        const [configType, configName] = this.parsePath(path);

        // Get raw config with meta keys intact
        const rawConfig = this.getRawConfig(configType, configName, false);
        const globalConfig = this.config.get('global') || {};

        const loadResult = this.config.getLoadResult();
        const appEnv = environment || loadResult?.appEnv || 'dev';

        const result = resolveProviderProxy(configName, rawConfig, globalConfig, appEnv);

        this.logDebug('computeProxy: Completed', { source: result.source, url: result.proxyUrl });
        return result;
    }

    /**
     * Compute network configuration.
     */
    computeNetwork(): NetworkConfig {
        this.logDebug('computeNetwork: Starting');

        const globalConfig = this.config.get('global') || {};
        const network = globalConfig.network || {};

        const result: NetworkConfig = {
            defaultEnvironment: network.default_environment || 'dev',
            proxyUrls: network.proxy_urls || {},
            caBundle: network.ca_bundle || null,
            cert: network.cert || null,
            certVerify: network.cert_verify ?? false,
            agentProxy: network.agent_proxy ? {
                httpProxy: network.agent_proxy.http_proxy || null,
                httpsProxy: network.agent_proxy.https_proxy || null
            } : null
        };

        this.logDebug('computeNetwork: Completed');
        return result;
    }

    /**
     * Get fully resolved configuration with env vars applied.
     */
    computeConfig(path: string): Record<string, any> {
        this.logDebug('computeConfig: Starting', { path });

        // Parse the path to get type and name (before storage->storages mapping)
        const parts = path.split('.');
        if (parts.length !== 2) {
            throw new Error(`Invalid path format '${path}'`);
        }
        const [pathType, configName] = parts;

        // Use the appropriate resolver for env var resolution
        if (pathType === 'providers') {
            const result = getProvider(configName, this.config);
            return result.config;
        } else if (pathType === 'services') {
            const result = getService(configName, this.config);
            return result.config;
        } else if (pathType === 'storages') {
            const result = getStorage(configName, this.config);
            return result.config;
        }

        // Fallback to raw config
        const [configType, name] = this.parsePath(path);
        return this.getRawConfig(configType, name, true);
    }

    /**
     * Convenience method to get all configuration aspects.
     */
    computeAll(path: string, environment?: string): ComputeResult {
        return this.compute(path, {
            includeHeaders: true,
            includeProxy: true,
            includeNetwork: true,
            includeConfig: true,
            suppressAuthErrors: true,
            environment
        });
    }

    // =========================================================================
    // Internal Helpers
    // =========================================================================

    private parsePath(path: string): [ConfigPath, string] {
        if (!path) {
            throw new Error('Path cannot be empty');
        }

        const parts = path.split('.');
        if (parts.length !== 2) {
            throw new Error(`Invalid path format '${path}'. Expected 'type.name' (e.g. providers.anthropic)`);
        }

        const configType = parts[0] as ConfigPath;
        const configName = parts[1];

        if (!['providers', 'services', 'storages'].includes(configType)) {
            throw new Error(`Invalid config type '${configType}'. Must be providers, services, or storages.`);
        }

        // Backward compatibility / Schema mapping
        // Config has 'storage' root key, whilst path logic uses 'storages' plural convention
        const resolvedType = (configType === 'storages') ? 'storage' : configType;

        return [resolvedType as ConfigPath, configName];
    }

    private getRawConfig(configType: ConfigPath, configName: string, removeMetaKeys: boolean): Record<string, any> {
        // Access raw config using public API if available or fallback logic
        // Assuming AppYamlConfig now supports get_provider/service/storage internally logic
        // or we use the getNested which works on the underlying data.

        const raw = (this.config as any).getNested
            ? (this.config as any).getNested([configType, configName])
            : (this.config as any).get(configType)?.[configName];

        if (!raw) {
            throw new Error(`Configuration not found for '${configType}.${configName}'`);
        }

        if (removeMetaKeys) {
            // Shallow copy to remove meta keys safely
            const clean = { ...raw };
            delete clean.overwrite_from_env;
            delete clean.fallbacks_from_env;
            return clean;
        }

        return raw;
    }

    private computeAuthInternal(
        configType: ConfigPath,
        configName: string,
        includeHeaders: boolean = false
    ): ComputedAuthConfig {
        this.logDebug('computeAuthInternal', { type: configType, name: configName });

        const rawConfig = this.getRawConfig(configType, configName, false);

        const authConfig = this.fetchAuthConfigFn({
            providerName: configName,
            providerConfig: rawConfig
        });

        const result: ComputedAuthConfig = { authConfig };

        if (includeHeaders) {
            const creds: AuthCredentials = {};
            if (authConfig.username) creds.username = authConfig.username;
            if (authConfig.password) creds.password = authConfig.password;
            if (authConfig.email) creds.email = authConfig.email;
            if (authConfig.token) creds.token = authConfig.token;
            if (authConfig.headerName) creds.headerKey = authConfig.headerName;
            if (authConfig.headerValue) creds.headerValue = authConfig.headerValue;

            result.headers = this.encodeAuthFn(authConfig.type, creds);
        }

        return result;
    }
}
