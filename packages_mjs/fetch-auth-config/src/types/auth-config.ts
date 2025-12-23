import { AuthType } from './auth-type.js';
import { TokenResolverType } from './token-resolver.js';

export interface AuthResolutionMeta {
    /** Which env vars were used */
    resolvedFrom: Record<string, string>;
    /** Token resolver type used */
    tokenResolver: TokenResolverType;
    /** Whether placeholder values were used */
    isPlaceholder: boolean;
}

export interface AuthConfig {
    /** Authentication type */
    type: AuthType;

    /** Provider name from YAML */
    providerName: string;

    /** Resolution metadata */
    resolution: AuthResolutionMeta;

    /** Token/API key (for bearer, x-api-key) */
    token?: string;

    /** Username (for basic auth) */
    username?: string;

    /** Password (for basic auth) */
    password?: string;

    /** Email (for basic_email_token) */
    email?: string;

    /** Custom header name (for custom auth) */
    headerName?: string;

    /** Custom header value */
    headerValue?: string;

    // EdgeGrid Specifics
    clientToken?: string;
    clientSecret?: string;
    accessToken?: string;
    baseUrl?: string;
    headersToSign?: string[];
}
