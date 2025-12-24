import { AuthConfig, AuthResolutionMeta } from '../types/auth-config.js';
import { AuthType } from '../types/auth-type.js';
import { TokenResolverType } from '../types/token-resolver.js';
import { MissingCredentialError } from '../errors.js';
import { ProviderEnvMappings } from '../resolution/config-extractor.js';
import { resolveEnvVarChain } from '../resolution/env-resolver.js';

export function resolveBearerAuth(
    providerName: string,
    envMappings: ProviderEnvMappings,
    authType: AuthType
): AuthConfig {
    const tokenResult = resolveEnvVarChain(envMappings.apiKey);

    if (!tokenResult.value) {
        throw new MissingCredentialError(
            providerName,
            'token',
            tokenResult.tried
        );
    }

    return {
        type: authType,
        providerName,
        token: tokenResult.value,
        headerName: 'Authorization',
        resolution: {
            resolvedFrom: { token: tokenResult.source! },
            tokenResolver: TokenResolverType.STATIC,
            isPlaceholder: false
        },
        resolverType: TokenResolverType.STATIC
    };
}
