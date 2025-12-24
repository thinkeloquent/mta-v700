/**
 * Configuration models and validation for fetch-client.
 */

import { z } from 'zod';
import { AuthType, RequestContext, Serializer } from './types.js';

// Constants
export const DEFAULT_TIMEOUT_CONNECT = 5000;
export const DEFAULT_TIMEOUT_READ = 30000;
export const DEFAULT_TIMEOUT_WRITE = 10000;
export const DEFAULT_CONTENT_TYPE = 'application/json';

// Schemas

export const TimeoutConfigSchema = z.object({
    connect: z.number().default(DEFAULT_TIMEOUT_CONNECT),
    read: z.number().default(DEFAULT_TIMEOUT_READ),
    write: z.number().default(DEFAULT_TIMEOUT_WRITE),
    pool: z.number().optional()
});

export type TimeoutConfig = z.infer<typeof TimeoutConfigSchema>;

export const AuthConfigSchema = z.object({
    type: z.custom<AuthType>(),
    rawApiKey: z.string().optional(),
    username: z.string().optional(),
    password: z.string().optional(),
    email: z.string().optional(),
    headerName: z.string().optional(),

    // Note: Functions cannot be strictly validated by Zod in the same way as data
    getApiKeyForRequest: z.function().optional()
}).superRefine((val, ctx) => {
    const t = val.type;
    const hasUser = !!val.username;
    const hasPass = !!val.password;
    const hasEmail = !!val.email;
    const hasKey = !!val.rawApiKey;

    if (t === 'basic' && (!hasUser || !hasPass)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Basic auth requires 'username' and 'password'" });
    }
    if (t === 'basic_email_token' && (!hasEmail || !hasKey)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "basic_email_token requires 'email' and 'rawApiKey'" });
    }
    if (t === 'basic_token' && (!hasUser || !hasKey)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "basic_token requires 'username' and 'rawApiKey'" });
    }
    if (t === 'basic_email' && (!hasEmail || !hasPass)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "basic_email requires 'email' and 'password'" });
    }
    if (['bearer', 'bearer_oauth', 'bearer_jwt', 'x-api-key'].includes(t) && !hasKey) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: `${t} requires 'rawApiKey'` });
    }
    if (t === 'bearer_username_token' && (!hasUser || !hasKey)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "bearer_username_token requires 'username' and 'rawApiKey'" });
    }
    if (t === 'bearer_username_password' && (!hasUser || !hasPass)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "bearer_username_password requires 'username' and 'password'" });
    }
    if (t === 'bearer_email_token' && (!hasEmail || !hasKey)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "bearer_email_token requires 'email' and 'rawApiKey'" });
    }
    if (t === 'bearer_email_password' && (!hasEmail || !hasPass)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "bearer_email_password requires 'email' and 'password'" });
    }
    if (['custom', 'custom_header'].includes(t) && (!val.headerName || !hasKey)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: `${t} requires 'headerName' and 'rawApiKey'` });
    }
    if (t === 'hmac') {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "HMAC auth not yet implemented" });
    }
});

export type AuthConfig = z.infer<typeof AuthConfigSchema> & {
    getApiKeyForRequest?: (context: RequestContext) => string | undefined;
};

// Utilities for AuthConfig

export function formatAuthHeaderValue(config: AuthConfig): string {
    const t = config.type;

    const b64 = (s: string) => Buffer.from(s).toString('base64');

    if (t === 'basic' && config.username && config.password) {
        return b64(`${config.username}:${config.password}`);
    }
    if (t === 'basic_email_token' && config.email && config.rawApiKey) {
        return b64(`${config.email}:${config.rawApiKey}`);
    }
    if (t === 'basic_token' && config.username && config.rawApiKey) {
        return b64(`${config.username}:${config.rawApiKey}`);
    }
    if (t === 'basic_email' && config.email && config.password) {
        return b64(`${config.email}:${config.password}`);
    }

    if (t === 'bearer_username_token' && config.username && config.rawApiKey) {
        return b64(`${config.username}:${config.rawApiKey}`);
    }
    if (t === 'bearer_username_password' && config.username && config.password) {
        return b64(`${config.username}:${config.password}`);
    }
    if (t === 'bearer_email_token' && config.email && config.rawApiKey) {
        return b64(`${config.email}:${config.rawApiKey}`);
    }
    if (t === 'bearer_email_password' && config.email && config.password) {
        return b64(`${config.email}:${config.password}`);
    }

    return config.rawApiKey || '';
}

export function getComputedApiKey(config: AuthConfig): string {
    return formatAuthHeaderValue(config);
}

export function getAuthHeaderName(config: AuthConfig): string {
    if (config.type === 'x-api-key') return 'x-api-key';
    if (['custom', 'custom_header'].includes(config.type)) return config.headerName || 'Authorization';
    return 'Authorization';
}

// Client Config

export const ClientConfigSchema = z.object({
    baseUrl: z.string().url().transform(url => url.endsWith('/') ? url.slice(0, -1) : url),
    auth: AuthConfigSchema.optional(),
    timeout: z.union([z.number(), TimeoutConfigSchema]).optional(),
    headers: z.record(z.string()).default({}),
    contentType: z.string().default(DEFAULT_CONTENT_TYPE),
    dispatcher: z.any().optional(), // Undici dispatcher
    serializer: z.any().optional(), // Serializer
});

export type ClientConfig = z.infer<typeof ClientConfigSchema> & {
    serializer?: Serializer;
    dispatcher?: any; // undici.Dispatcher
};

export class DefaultSerializer implements Serializer {
    serialize(data: any): string {
        return JSON.stringify(data);
    }
    deserialize(data: string): any {
        return JSON.parse(data);
    }
}

export interface ResolvedConfig {
    baseUrl: string;
    auth?: AuthConfig;
    timeout: TimeoutConfig;
    headers: Record<string, string>;
    contentType: string;
    serializer: Serializer;
}

export function normalizeTimeout(timeout?: number | TimeoutConfig): TimeoutConfig {
    if (timeout === undefined || timeout === null) {
        return {
            connect: DEFAULT_TIMEOUT_CONNECT,
            read: DEFAULT_TIMEOUT_READ,
            write: DEFAULT_TIMEOUT_WRITE
        };
    }
    if (typeof timeout === 'number') {
        return {
            connect: timeout,
            read: timeout,
            write: timeout
        };
    }
    return timeout;
}

export function resolveConfig(config: ClientConfig): ResolvedConfig {
    // Validate first
    const validated = ClientConfigSchema.parse(config) as ClientConfig;
    return {
        baseUrl: validated.baseUrl,
        auth: validated.auth as AuthConfig | undefined,
        timeout: normalizeTimeout(validated.timeout),
        headers: validated.headers,
        contentType: validated.contentType,
        serializer: config.serializer || new DefaultSerializer()
    };
}
