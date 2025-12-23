import { AuthConfig, AuthResolutionMeta } from './types/auth-config.js';
import { AuthType } from './types/auth-type.js';
import { TokenResolverType } from './types/token-resolver.js';
import { extractAuthSettings, extractEnvMappings } from './resolution/config-extractor.js';
import { resolveBearerAuth } from './resolvers/bearer.js';
import { resolveBasicAuth } from './resolvers/basic.js';
import { resolveCustomAuth } from './resolvers/custom.js';
import { InvalidAuthTypeError } from './errors.js';

export interface FetchAuthConfigOptions {
    providerName: string;
    providerConfig: Record<string, any>; // From app-yaml-config
}

export function fetchAuthConfig(
    options: FetchAuthConfigOptions
): AuthConfig {
    const { providerName, providerConfig } = options;

    // 1. Extract settings
    const authSettings = extractAuthSettings(providerConfig);

    const envMappings = extractEnvMappings(providerConfig);

    // 2. Route to resolver
    switch (authSettings.authType) {
        case AuthType.BEARER:
        case AuthType.BEARER_OAUTH:
        case AuthType.BEARER_JWT:
            return resolveBearerAuth(providerName, envMappings, authSettings.authType);

        case AuthType.BASIC:
        case AuthType.BASIC_EMAIL_TOKEN:
        case AuthType.BASIC_TOKEN:
        case AuthType.BASIC_EMAIL:
            return resolveBasicAuth(providerName, envMappings, authSettings.authType);

        case AuthType.X_API_KEY:
        case AuthType.CUSTOM:
        case AuthType.CUSTOM_HEADER:
            return resolveCustomAuth(providerName, envMappings, authSettings);

        case AuthType.NONE:
            return {
                type: AuthType.NONE,
                providerName,
                resolution: {
                    resolvedFrom: {},
                    tokenResolver: TokenResolverType.STATIC,
                    isPlaceholder: false
                }
            };

        default:
            throw new InvalidAuthTypeError(providerName, authSettings.authType);
    }
}
