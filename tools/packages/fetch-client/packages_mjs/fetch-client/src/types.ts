/**
 * Core type definitions for fetch-client.
 */

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS';

export type AuthType =
    | 'basic'
    | 'basic_email_token'
    | 'basic_token'
    | 'basic_email'
    | 'bearer'
    | 'bearer_oauth'
    | 'bearer_jwt'
    | 'bearer_username_token'
    | 'bearer_username_password'
    | 'bearer_email_token'
    | 'bearer_email_password'
    | 'x-api-key'
    | 'custom'
    | 'custom_header'
    | 'hmac';

export interface FetchResponse<T = any> {
    status: number;
    statusText: string;
    headers: Record<string, string>;
    url: string;
    data: T;
    ok: boolean;
}

export interface RequestOptions {
    method?: HttpMethod;
    url?: string; // Relative path or full URL
    headers?: Record<string, string>;
    query?: Record<string, any>; // Query parameters
    json?: any;
    body?: string | Buffer | Uint8Array | ReadableStream | null;
    timeout?: number;
}

export interface StreamOptions extends RequestOptions {
    onEvent?: (event: any) => void;
}

export interface SSEEvent {
    data: string;
    id?: string;
    event?: string;
    retry?: number;
}

export interface DiagnosticsEvent {
    name: 'request:start' | 'request:end' | 'request:error';
    timestamp: number;
    method: string;
    url: string;
    headers?: Record<string, string>;
    status?: number;
    duration?: number;
    error?: Error;
}

export interface RequestContext {
    method: string;
    url: string; // Full URL or path
    headers: Record<string, string>;
    body: any;
}

export interface Serializer {
    serialize(data: any): string;
    deserialize(data: string): any;
}
