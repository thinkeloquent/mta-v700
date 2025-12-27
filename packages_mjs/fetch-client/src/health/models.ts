/**
 * Models for Fetch Status Health Check.
 */

export enum FetchStatus {
    CONNECTED = "connected",
    UNAUTHORIZED = "unauthorized",
    SERVER_ERROR = "server_error",
    CLIENT_ERROR = "client_error",
    TIMEOUT = "timeout",
    CONNECTION_ERROR = "connection_error",
    CONFIG_ERROR = "config_error",
    ERROR = "error",
}

export interface FetchStatusResult {
    provider_name: string;
    status: FetchStatus;
    latency_ms: number;
    timestamp: string;
    request?: Record<string, any>;
    response?: Record<string, any>;
    config_used?: Record<string, any>;
    fetch_option_used?: Record<string, any>;
    error?: Record<string, any>;
}
