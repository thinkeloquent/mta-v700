import type { AppYamlConfig } from '@internal/app-yaml-config';
import { fetchAuthConfig, AuthConfig } from '@internal/fetch-auth-config';
import { encodeAuth, AuthCredentials } from '@internal/fetch-auth-encoding';

export type ConfigPath = 'providers' | 'services' | 'storages';

export interface ComputedAuthConfig {
    authConfig: AuthConfig;
    headers?: Record<string, string>;
}

export class YamlConfigFactory {
    constructor(
        private config: AppYamlConfig,
        private fetchAuthConfigFn = fetchAuthConfig,
        private encodeAuthFn = encodeAuth
    ) { }

    compute(
        path: string,  // e.g., 'providers.anthropic'
        options?: { includeHeaders?: boolean }
    ): ComputedAuthConfig {
        // 1. Parse Path
        const parts = path.split('.');
        if (parts.length !== 2) {
            throw new Error(`Invalid path format '${path}'. Expected 'type.name' (e.g. providers.anthropic)`);
        }

        const configType = parts[0] as ConfigPath;
        const configName = parts[1];

        if (!['providers', 'services', 'storages'].includes(configType)) {
            throw new Error(`Invalid config type '${configType}'. Must be providers, services, or storages.`);
        }

        // 2. Retrieve Raw Config
        // Access raw config using getNested or direct access if public
        // casting to any to access internal config store or using public getter
        // AppYamlConfig in TS might expose specific getters.
        // We'll trust getNested exists or equivalent unique getter.
        // If getNested doesn't exist on public interface, we might need to cast or use 'get'.
        const rawConfig = (this.config as any).getNested
            ? (this.config as any).getNested(configType, configName)
            : (this.config as any).get(configType)?.[configName]; // Fallback if simple structure

        if (!rawConfig) {
            throw new Error(`Configuration not found for '${path}'`);
        }

        // 3. Resolve Auth
        const authConfig: AuthConfig = this.fetchAuthConfigFn({
            providerName: configName,
            providerConfig: rawConfig
        });

        const result: ComputedAuthConfig = {
            authConfig
        };

        // 4. Encode Headers
        if (options?.includeHeaders) {
            const creds: AuthCredentials = {};
            if (authConfig.username) creds.username = authConfig.username;
            if (authConfig.password) creds.password = authConfig.password;
            if (authConfig.email) creds.email = authConfig.email;
            if (authConfig.token) creds.token = authConfig.token;
            if (authConfig.headerName) creds.headerKey = authConfig.headerName;
            if (authConfig.headerValue) creds.headerValue = authConfig.headerValue;

            const headers = this.encodeAuthFn(authConfig.type, creds);
            result.headers = headers;
        }

        return result;
    }
}
