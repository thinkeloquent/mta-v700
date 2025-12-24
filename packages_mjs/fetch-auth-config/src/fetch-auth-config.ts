import { AuthConfig, AuthResolutionMeta } from './types/auth-config.js';
import { AuthType } from './types/auth-type.js';
import { TokenResolverType } from './types/token-resolver.js';
import { extractAuthSettings, extractEnvMappings } from './resolution/config-extractor.js';
import { resolveBearerAuth } from './resolvers/bearer.js';
import { resolveBasicAuth } from './resolvers/basic.js';
import { resolveCustomAuth } from './resolvers/custom.js';
import { InvalidAuthTypeError } from './errors.js';
import { ComputeRegistry } from './compute-registry.js';

export interface FetchAuthConfigOptions {
    providerName: string;
    providerConfig: Record<string, any>; // From app-yaml-config
    request?: any; // Optional request context
}

export async function fetchAuthConfig(
    options: FetchAuthConfigOptions
): Promise<AuthConfig> {
    const { providerName, providerConfig, request } = options;

    // 1. Extract settings
    const authSettings = extractAuthSettings(providerConfig);
    const envMappings = extractEnvMappings(providerConfig);

    // 2. Dynamic Resolution
    if (authSettings.tokenResolver === TokenResolverType.STARTUP || authSettings.tokenResolver === TokenResolverType.REQUEST) {
        let tokenValue: string;

        if (authSettings.tokenResolver === TokenResolverType.STARTUP) {
            const server = request ? request.server : null;
            tokenValue = await ComputeRegistry.resolveStartup(providerName, server);
        } else {
            if (!request) {
                throw new Error(`Request context required for provider '${providerName}' with REQUEST token resolver`);
            }
            tokenValue = await ComputeRegistry.resolveRequest(providerName, request);
        }

        const ac: AuthConfig = {
            type: authSettings.authType,
            providerName,
            token: tokenValue,
            headerName: authSettings.customHeaderName,
            resolution: {
                resolvedFrom: { token: 'dynamic' },
                tokenResolver: authSettings.tokenResolver,
                isPlaceholder: false
            },
            resolverType: authSettings.tokenResolver
        };

        // Basic auth password mapping
        if ([AuthType.BASIC, AuthType.BASIC_EMAIL].includes(authSettings.authType)) {
            ac.password = tokenValue;
        }

        // Default header
        if (!ac.headerName) {
            const standardTypes = [
                AuthType.BEARER, AuthType.BEARER_OAUTH, AuthType.BEARER_JWT,
                AuthType.BASIC, AuthType.BASIC_EMAIL_TOKEN, AuthType.BASIC_TOKEN, AuthType.BASIC_EMAIL
            ];
            if (standardTypes.includes(authSettings.authType)) {
                ac.headerName = 'Authorization';
            }
        }

        return ac;
    }

    // 3. Static Resolution
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
                },
                resolverType: TokenResolverType.STATIC
            };

        default:
            throw new InvalidAuthTypeError(providerName, authSettings.authType);
    }
}
