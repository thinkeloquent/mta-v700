import { AuthType } from '../types/auth-type.js';
import { TokenResolverType } from '../types/token-resolver.js';
import { EnvVarChainConfig } from './env-resolver.js';

export interface ProviderEnvMappings {
    apiKey: EnvVarChainConfig;
    email: EnvVarChainConfig;
    username: EnvVarChainConfig;
    password: EnvVarChainConfig;
    clientToken: EnvVarChainConfig;
    clientSecret: EnvVarChainConfig;
    accessToken: EnvVarChainConfig;
}

export interface AuthSettings {
    authType: AuthType;
    customHeaderName?: string;
    tokenResolver: TokenResolverType;
}

export function extractEnvMappings(
    providerConfig: Record<string, any>
): ProviderEnvMappings {
    const overwrites = providerConfig.overwrite_from_env || {};

    function getChain(key: string, primaryKey: string): EnvVarChainConfig {
        return {
            primary: providerConfig[primaryKey],
            overwrite: overwrites[key]
        };
    }

    return {
        apiKey: getChain('endpoint_api_key', 'endpoint_api_key'),
        email: getChain('email', 'env_email'),
        username: getChain('username', 'env_username'),
        password: getChain('password', 'env_password'),
        clientToken: getChain('client_token', 'env_client_token'),
        clientSecret: getChain('client_secret', 'env_client_secret'),
        accessToken: getChain('access_token', 'env_access_token')
    };
}

export function extractAuthSettings(
    providerConfig: Record<string, any>
): AuthSettings {
    return {
        authType: (providerConfig.api_auth_type || 'bearer') as AuthType,
        customHeaderName: providerConfig.api_auth_header_name,
        tokenResolver: (providerConfig.token_resolver || 'static') as TokenResolverType
    };
}
