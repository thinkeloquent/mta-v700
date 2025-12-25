import { AuthConfig, AuthResolutionMeta } from '../types/auth-config.js';
import { AuthType } from '../types/auth-type.js';
import { TokenResolverType } from '../types/token-resolver.js';
import { MissingCredentialError } from '../errors.js';
import { ProviderEnvMappings } from '../resolution/config-extractor.js';
import { resolveEnvVarChain } from '../resolution/env-resolver.js';

export function resolveBasicAuth(
    providerName: string,
    envMappings: ProviderEnvMappings,
    authType: AuthType
): AuthConfig {
    const resolvedFrom: Record<string, string> = {};

    let username: string | undefined;
    let email: string | undefined;
    let password: string | undefined;
    let token: string | undefined;

    // Username/Email
    if ([AuthType.BASIC_EMAIL, AuthType.BASIC_EMAIL_TOKEN].includes(authType)) {
        const res = resolveEnvVarChain(envMappings.email);
        if (!res.value) throw new MissingCredentialError(providerName, 'email', res.tried);
        email = res.value;
        resolvedFrom['email'] = res.source!;
    } else {
        const res = resolveEnvVarChain(envMappings.username);
        if (!res.value) throw new MissingCredentialError(providerName, 'username', res.tried);
        username = res.value;
        resolvedFrom['username'] = res.source!;
    }

    // Password/Token
    if ([AuthType.BASIC, AuthType.BASIC_EMAIL].includes(authType)) {
        let res = resolveEnvVarChain(envMappings.password);
        if (!res.value) {
            // Fallback: try using apiKey as password (common pattern where endpoint_api_key is used for password)
            const tokenRes = resolveEnvVarChain(envMappings.apiKey);
            if (tokenRes.value) {
                res = tokenRes;
            } else {
                throw new MissingCredentialError(providerName, 'password', res.tried);
            }
        }
        password = res.value ?? undefined;
        resolvedFrom['password'] = res.source!;
    } else {
        const res = resolveEnvVarChain(envMappings.apiKey);
        if (!res.value) throw new MissingCredentialError(providerName, 'token', res.tried);
        token = res.value;
        resolvedFrom['token'] = res.source!;
    }

    return {
        type: authType,
        providerName,
        username,
        email,
        password,
        token,
        headerName: 'Authorization',
        resolution: {
            resolvedFrom,
            tokenResolver: TokenResolverType.STATIC,
            isPlaceholder: false
        },
        resolverType: TokenResolverType.STATIC
    };
}
