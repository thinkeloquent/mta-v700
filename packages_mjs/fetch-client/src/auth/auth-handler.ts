/**
 * Auth handler utilities for @internal/fetch-client
 */
import { RequestContext } from '../types.js';
import { AuthConfig, getComputedApiKey, formatAuthHeaderValue } from '../config.js';

// Get current file path for logging
const LOG_PREFIX = `[AUTH:auth-handler.ts]`;

/**
 * Mask sensitive value for logging, showing first 15 chars.
 */
function maskValue(val: string | undefined): string {
    if (!val) return '<empty>';
    if (val.length <= 10) return '*'.repeat(val.length);
    return val.slice(0, 10) + '*'.repeat(val.length - 10);
}

/**
 * Auth handler interface
 */
export interface AuthHandler {
    getHeader(context: RequestContext): Record<string, string> | null;
}

/**
 * Bearer token auth handler
 */
export class BearerAuthHandler implements AuthHandler {
    constructor(
        private api_key?: string,
        private get_api_key_for_request?: (context: RequestContext) => string | undefined
    ) { }

    getHeader(context: RequestContext): Record<string, string> | null {
        const key = this.get_api_key_for_request?.(context) || this.api_key;
        if (!key) return null;
        const header = { Authorization: `Bearer ${key}` };
        // console.log(
        //   `${LOG_PREFIX} BearerAuthHandler.getHeader: api_key=${maskValue(key)} -> Authorization=${maskValue(header.Authorization)}`
        // );
        return header;
    }
}

/**
 * X-API-Key auth handler
 */
export class XApiKeyAuthHandler implements AuthHandler {
    constructor(
        private api_key?: string,
        private get_api_key_for_request?: (context: RequestContext) => string | undefined
    ) { }

    getHeader(context: RequestContext): Record<string, string> | null {
        const key = this.get_api_key_for_request?.(context) || this.api_key;
        if (!key) return null;
        // console.log(`${LOG_PREFIX} XApiKeyAuthHandler.getHeader: api_key=${maskValue(key)}`);
        return { 'x-api-key': key };
    }
}

/**
 * Custom header auth handler
 */
export class CustomAuthHandler implements AuthHandler {
    constructor(
        private headerName: string,
        private api_key?: string,
        private get_api_key_for_request?: (context: RequestContext) => string | undefined
    ) { }

    getHeader(context: RequestContext): Record<string, string> | null {
        const key = this.get_api_key_for_request?.(context) || this.api_key;
        if (!key) return null;
        // console.log(
        //   `${LOG_PREFIX} CustomAuthHandler.getHeader: headerName=${this.headerName}, api_key=${maskValue(key)}`
        // );
        return { [this.headerName]: key };
    }
}

/**
 * Create auth handler from config
 */
export function createAuthHandler(config: AuthConfig): AuthHandler {
    // Get the computed/formatted auth value based on the auth type
    // getComputedApiKey returns the base64 encoded PART only, not the scheme "Basic "
    // Wait, let's double check config.ts behavior
    // Yes, formatAuthHeaderValue returns just base64(user:pass)
    const computedApiKey = getComputedApiKey(config); // Just the value

    // console.log(
    //   `${LOG_PREFIX} createAuthHandler: type=${config.type}, rawApiKey=${maskValue(config.rawApiKey)}`
    // );

    switch (config.type) {
        case 'bearer':
        case 'bearer_oauth':
        case 'bearer_jwt':
            // Simple token case
            return new BearerAuthHandler(config.rawApiKey, config.getApiKeyForRequest);

        case 'bearer_username_token':
        case 'bearer_username_password':
        case 'bearer_email_token':
        case 'bearer_email_password':
            // Complex Bearer types - return full computed value ("Bearer <base64>")
            return new CustomAuthHandler(
                'Authorization',
                `Bearer ${computedApiKey}`,
                config.getApiKeyForRequest // Note: this callback normally returns just the key, handling full header string in callback is tricky
                // If dynamic token used for complex type, we might need different logic.
                // For now, assuming static complex credentials, or simple dynamic token.
            );

        case 'x-api-key':
            return new XApiKeyAuthHandler(config.rawApiKey, config.getApiKeyForRequest);

        case 'basic':
        case 'basic_email_token':
        case 'basic_token':
        case 'basic_email':
            // Basic auth - return full computed value ("Basic <base64>")
            return new CustomAuthHandler(
                'Authorization',
                `Basic ${computedApiKey}`,
                config.getApiKeyForRequest
            );

        case 'custom':
        case 'custom_header':
            return new CustomAuthHandler(
                config.headerName || 'Authorization',
                config.rawApiKey,
                config.getApiKeyForRequest
            );

        default:
            // Default to bearer with rawApiKey
            return new BearerAuthHandler(config.rawApiKey, config.getApiKeyForRequest);
    }
}
