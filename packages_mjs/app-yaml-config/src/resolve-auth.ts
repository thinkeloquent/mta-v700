
import { fetchAuthConfig, AuthConfig, AuthConfigError } from '@internal/fetch-auth-config';
import { encodeAuth } from '@internal/fetch-auth-encoding';

export interface AuthResolutionResult {
    authConfig: AuthConfig;
    headers: Record<string, string>;
    providerName: string;
    source: 'provider_config' | 'env_overwrite' | 'default';
}

export interface ResolveAuthOptions {
    includeHeaders?: boolean;
}

/**
 * Resolve authentication configuration for a provider.
 * Thin wrapper around fetch-auth-config that mirrors resolve-proxy pattern.
 */
export async function resolveProviderAuth(
    providerName: string,
    providerConfig: Record<string, any>,
    options: ResolveAuthOptions = {}
): Promise<AuthResolutionResult> {
    const { includeHeaders = true } = options;

    // Use fetch-auth-config for credential resolution
    const authConfig = await fetchAuthConfig({
        providerName,
        providerConfig,
    });

    // Build headers if requested
    let headers: Record<string, string> = {};
    if (includeHeaders) {
        const creds = buildCredentials(authConfig);
        headers = encodeAuth(authConfig.type, creds);
    }

    // Determine source based on resolution metadata
    let source: AuthResolutionResult['source'] = 'provider_config';
    // Use optional chaining safely
    if (authConfig.resolution?.resolvedFrom) {
        const resolvedKeys = Object.keys(authConfig.resolution.resolvedFrom);
        if (resolvedKeys.length > 0) {
            source = 'env_overwrite';
        }
    }

    return {
        authConfig,
        headers,
        providerName,
        source,
    };
}

function buildCredentials(authConfig: AuthConfig): Record<string, any> {
    const creds: Record<string, any> = {};
    if (authConfig.token) creds.token = authConfig.token;
    if (authConfig.username) creds.username = authConfig.username;
    if (authConfig.password) creds.password = authConfig.password;
    if (authConfig.email) creds.email = authConfig.email;
    if (authConfig.headerName) creds.headerKey = authConfig.headerName;
    if (authConfig.headerValue) creds.headerValue = authConfig.headerValue;
    return creds;
}

// Re-export types from fetch-auth-config for convenience
export { AuthConfig, AuthType, AuthConfigError } from '@internal/fetch-auth-config';
