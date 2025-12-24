import { AuthConfig, AuthResolutionMeta } from '../types/auth-config.js';
import { AuthType } from '../types/auth-type.js';
import { TokenResolverType } from '../types/token-resolver.js';
import { MissingCredentialError } from '../errors.js';
import { ProviderEnvMappings, AuthSettings } from '../resolution/config-extractor.js';
import { resolveEnvVarChain } from '../resolution/env-resolver.js';

export function resolveCustomAuth(
    providerName: string,
    envMappings: ProviderEnvMappings,
    authSettings: AuthSettings
): AuthConfig {
    const tokenResult = resolveEnvVarChain(envMappings.apiKey);

    if (!tokenResult.value) {
        throw new MissingCredentialError(
            providerName,
            'token',
            tokenResult.tried
        );
    }

    let headerName = authSettings.customHeaderName;
    if (authSettings.authType === AuthType.X_API_KEY) {
        headerName = 'X-API-Key';
    }

    return {
        type: authSettings.authType,
        providerName,
        token: tokenResult.value,
        headerName,
        resolution: {
            resolvedFrom: { token: tokenResult.source! },
            tokenResolver: TokenResolverType.STATIC,
            isPlaceholder: false
        },
        resolverType: TokenResolverType.STATIC
    };
}
