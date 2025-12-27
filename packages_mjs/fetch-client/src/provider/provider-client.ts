
import { FetchClient } from '../client.js';
import { ClientConfig } from '../config.js';
import { FetchResponse, RequestOptions } from '../types.js';
import { FetchStatus, FetchStatusResult } from '../health/models.js';

export interface ComputeAllResult {
    config: Record<string, any>;
    authConfig?: any;
    proxyConfig?: any;
    networkConfig?: any;
    headers?: Record<string, string>;
    authError?: Error;
    configType?: string;
    configName?: string;
}

export interface ProviderClientOptions {
    timeoutSeconds?: number;
    endpointOverride?: string;
}

export interface ConfigUsedInfo {
    baseUrl: string;
    healthEndpoint: string;
    method: string;
    timeoutSeconds: number;
    authType: string | null;
    authResolved: boolean;
    authHeaderPresent: boolean;
    isPlaceholder: boolean | null;
    proxyUrl: string | null;
    proxyResolved: boolean;
    headersCount: number;
}

export interface FetchOptionUsedInfo {
    method: string;
    url: string;
    timeoutSeconds: number;
    headers: Record<string, string>;
    headersCount: number;
    followRedirects: boolean;
    proxy: string | null;
    verifySsl: boolean;
}

export class ProviderClient {
    private providerName: string;
    private runtimeConfig: ComputeAllResult;
    private timeoutSeconds: number;
    private endpointOverride?: string;
    private _client?: FetchClient;
    private _mergedHeaders: Record<string, string>;

    constructor(
        providerName: string,
        runtimeConfig: ComputeAllResult,
        options?: ProviderClientOptions
    ) {
        this.providerName = providerName;
        this.runtimeConfig = runtimeConfig;
        this.timeoutSeconds = options?.timeoutSeconds ?? 10.0;
        this.endpointOverride = options?.endpointOverride;

        // Validate config
        if (!this.runtimeConfig.config.base_url) {
            throw new Error(`base_url is required in provider config for '${this.providerName}'`);
        }

        // Pre-compute merged headers
        const preComputedHeaders = this.runtimeConfig.headers || {};
        const configHeaders = this.runtimeConfig.config.headers || {};
        this._mergedHeaders = { ...configHeaders, ...preComputedHeaders };
    }

    /**
     * Get the underlying FetchClient for custom requests.
     */
    public getClient(): FetchClient {
        if (!this._client) {
            this._client = this._createClient();
        }
        return this._client;
    }

    /**
     * Make a request using this provider's configuration.
     */
    public async request<T = any>(options: RequestOptions): Promise<FetchResponse<T>> {
        const client = this.getClient();
        return client.request<T>(options);
    }

    /**
     * Convenience GET request.
     */
    public async get<T = any>(
        url: string,
        options?: { query?: Record<string, any>; headers?: Record<string, string>; timeout?: number }
    ): Promise<FetchResponse<T>> {
        return this.request<T>({
            method: 'GET',
            url,
            ...options
        });
    }

    /**
     * Convenience POST request.
     */
    public async post<T = any>(
        url: string,
        body?: any,
        options?: { query?: Record<string, any>; headers?: Record<string, string>; timeout?: number }
    ): Promise<FetchResponse<T>> {
        return this.request<T>({
            method: 'POST',
            url,
            body,
            ...options
        });
    }

    // Add other convenience methods as needed (put, patch, delete) can be added later if required

    /**
     * Execute health check against the provider.
     */
    public async checkHealth(
        endpointOverride?: string,
        timeout?: number
    ): Promise<FetchStatusResult> {
        const timestamp = new Date().toISOString();
        const startTime = performance.now();

        // 1. Resolve endpoint
        let healthEndpoint: string;
        try {
            healthEndpoint = this._resolveHealthEndpoint(endpointOverride);
        } catch (e: any) {
            return this._configError(e.message, timestamp);
        }

        const baseUrl = this.runtimeConfig.config.base_url;
        // Basic url joining to look nice in status
        const fullUrl = `${baseUrl.replace(/\/$/, "")}/${healthEndpoint.replace(/^\//, "")}`;

        const method = this._resolveMethod();
        const timeoutSec = timeout ?? this.timeoutSeconds;

        const requestInfo = {
            method,
            url: fullUrl,
            timeout_seconds: timeoutSec,
        };

        const configUsed = this._buildConfigUsed(healthEndpoint, method);
        const fetchOptionUsed = this._buildFetchOptionUsed(method, fullUrl, this._mergedHeaders); // Note: using pre-computed merged headers

        try {
            const client = this.getClient();
            const response = await client.request({
                method: method as any,
                url: healthEndpoint,
                timeout: timeoutSec * 1000
            });

            const latencyMs = performance.now() - startTime;

            // Read body safely
            let bodyPreview = "";
            try {
                const text = response.data
                    ? typeof response.data === "string"
                        ? response.data
                        : JSON.stringify(response.data)
                    : "";
                bodyPreview = this._truncate(text);
            } catch (e) {
                bodyPreview = "[Unable to read body]";
            }

            return {
                provider_name: this.providerName,
                status: this._statusFromCode(response.status),
                latency_ms: Number(latencyMs.toFixed(2)),
                timestamp,
                request: requestInfo,
                response: {
                    status_code: response.status,
                    status_text: response.statusText,
                    content_type:
                        response.headers instanceof Map
                            ? response.headers.get("content-type")
                            : (response.headers as any)["content-type"],
                    body_preview: bodyPreview,
                },
                config_used: configUsed,
                fetch_option_used: fetchOptionUsed,
            };

        } catch (e: any) {
            const latencyMs = performance.now() - startTime;

            let status = FetchStatus.ERROR;
            let errorType = "Error";
            let errorMessage = String(e);

            // Handle specific error types if possible (undici errors)
            if (
                e.name === "ConnectTimeoutError" ||
                e.code === "UND_ERR_CONNECT_TIMEOUT"
            ) {
                status = FetchStatus.TIMEOUT;
                errorType = "TimeoutException";
            } else if (e.name === "SocketError" || e.code === "UND_ERR_SOCKET") {
                status = FetchStatus.CONNECTION_ERROR;
                errorType = "ConnectError";
            } else if (e.code === "UND_ERR_INVALID_ARG") {
                // Invalid URL or similar configuration error
                status = FetchStatus.CONFIG_ERROR;
                errorType = "ConfigError";
            }

            return {
                provider_name: this.providerName,
                status,
                latency_ms: Number(latencyMs.toFixed(2)),
                timestamp,
                request: requestInfo,
                config_used: configUsed,
                fetch_option_used: fetchOptionUsed,
                error: {
                    type: errorType,
                    message: errorMessage,
                    code: e.code,
                    name: e.name,
                },
            };
        }
    }

    /**
     * Get configuration info for diagnostics.
     */
    public getConfigUsed(): ConfigUsedInfo {
        // We reuse the internal builder but need to resolve endpoint/method momentarily
        // If this throws, we might return partial info or let it throw. 
        // For diagnostics, safe access is preferred.
        try {
            const healthEndpoint = this._resolveHealthEndpoint();
            const method = this._resolveMethod();
            return this._buildConfigUsed(healthEndpoint, method);
        } catch (e) {
            // Fallback if we can't fully resolve
            return this._buildConfigUsed("unknown", "GET");
        }
    }

    /**
     * Get fetch options with masked sensitive values.
     */
    public getFetchOptionUsed(method?: string, fullUrl?: string): FetchOptionUsedInfo {
        const m = method || this._resolveMethod();
        const u = fullUrl || this.runtimeConfig.config.base_url; // simplified
        return this._buildFetchOptionUsed(m, u, this._mergedHeaders);
    }

    /**
     * Close the client connection.
     */
    public async close(): Promise<void> {
        if (this._client && typeof (this._client as any).close === 'function') {
            await (this._client as any).close();
        }
    }

    // =========================================================================
    // Private Helpers
    // =========================================================================

    private _resolveHealthEndpoint(override?: string): string {
        if (override || this.endpointOverride) {
            return this._resolvePlaceholders(override || this.endpointOverride!);
        }

        const config = this.runtimeConfig.config;
        if (config.health_endpoint) {
            const healthConf = config.health_endpoint;
            let endpoint: string;

            if (typeof healthConf === "object" && healthConf !== null) {
                endpoint = healthConf.path || healthConf.endpoint;
                if (!endpoint) {
                    throw new Error(
                        `health_endpoint object missing 'path' in provider config for '${this.providerName}'`
                    );
                }
            } else {
                endpoint = String(healthConf);
            }
            // Replace placeholders like :username, :email with actual values from authConfig
            return this._resolvePlaceholders(endpoint);
        }

        throw new Error(
            `health_endpoint is required in provider config for '${this.providerName}'`
        );
    }

    private _resolvePlaceholders(endpoint: string): string {
        const auth = this.runtimeConfig.authConfig;
        const config = this.runtimeConfig.config;

        // Build replacement map from auth and config values
        const replacements: Record<string, string | undefined> = {
            ":username": auth?.username || config?.username,
            ":email": auth?.email || config?.email,
            ":user": auth?.username || config?.username,
        };

        let result = endpoint;
        for (const [placeholder, value] of Object.entries(replacements)) {
            if (value && result.includes(placeholder)) {
                result = result.replace(placeholder, encodeURIComponent(value));
            }
        }

        return result;
    }

    private _resolveMethod(): string {
        const config = this.runtimeConfig.config || {};

        // Check if health_endpoint is object with method
        const healthEndpointConfig = config.health_endpoint;
        if (
            typeof healthEndpointConfig === "object" &&
            healthEndpointConfig?.method
        ) {
            return String(healthEndpointConfig.method).toUpperCase();
        }

        // Fallback to top-level method
        if (config.method) {
            return String(config.method).toUpperCase();
        }

        return "GET";
    }

    private _createClient(): FetchClient {
        // Use pre-computed `_mergedHeaders` which includes properly
        // encoded Authorization header via encodeAuth
        const config: ClientConfig = {
            baseUrl: this.runtimeConfig.config.base_url,
            // Do NOT pass auth config - we're using pre-computed headers instead
            contentType: "application/json",
            headers: this._mergedHeaders,
            timeout: this.timeoutSeconds * 1000, // Client expects ms
        };

        return FetchClient.create(config);
    }

    private _buildConfigUsed(
        healthEndpoint: string,
        method: string
    ): ConfigUsedInfo {
        const auth = this.runtimeConfig.authConfig;
        const proxy = this.runtimeConfig.proxyConfig;
        const authTypeStr = auth?.type?.value || auth?.type;
        const hasAuthHeader = Boolean(
            this._mergedHeaders["Authorization"] || this._mergedHeaders["authorization"]
        );

        return {
            baseUrl: this.runtimeConfig.config.base_url,
            healthEndpoint: healthEndpoint,
            method,
            timeoutSeconds: this.timeoutSeconds,
            authType: authTypeStr || null,
            authResolved: Boolean(auth && auth.token),
            authHeaderPresent: hasAuthHeader,
            isPlaceholder: auth?.resolution?.isPlaceholder ?? null,
            proxyUrl: proxy?.proxyUrl ?? null,
            proxyResolved: Boolean(proxy && proxy.proxyUrl),
            headersCount: Object.keys(this._mergedHeaders).length,
        };
    }

    private _buildFetchOptionUsed(
        method: string,
        fullUrl: string,
        mergedHeaders: Record<string, string>
    ): FetchOptionUsedInfo {
        const config = this.runtimeConfig.config || {};
        const proxy = this.runtimeConfig.proxyConfig;

        // Mask sensitive headers
        const maskedHeaders: Record<string, string> = {};
        for (const [k, v] of Object.entries(mergedHeaders)) {
            maskedHeaders[k] = this._maskHeaderValue(k, String(v));
        }

        // Get proxy URL and mask credentials if present
        let proxyUrl: string | null = null;
        if (proxy?.proxyUrl) {
            try {
                const parsed = new URL(proxy.proxyUrl);
                if (parsed.password) {
                    proxyUrl = proxy.proxyUrl.replace(parsed.password, "****");
                } else {
                    proxyUrl = proxy.proxyUrl;
                }
            } catch {
                proxyUrl = proxy.proxyUrl;
            }
        }

        return {
            method,
            url: fullUrl,
            timeoutSeconds: this.timeoutSeconds,
            headers: maskedHeaders,
            headersCount: Object.keys(mergedHeaders).length,
            followRedirects: config.follow_redirects ?? true,
            proxy: proxyUrl,
            verifySsl: config.verify_ssl ?? true,
        };
    }

    private _maskHeaderValue(key: string, value: string): string {
        const sensitiveKeys = new Set([
            "authorization",
            "x-api-key",
            "api-key",
            "token",
            "secret",
        ]);
        if (sensitiveKeys.has(key.toLowerCase())) {
            if (value.length <= 20) {
                return "****";
            }
            return `${value.substring(0, 20)}...`;
        }
        return value;
    }

    private _statusFromCode(statusCode: number): FetchStatus {
        if (statusCode >= 200 && statusCode < 300) return FetchStatus.CONNECTED;
        if (statusCode === 401 || statusCode === 403)
            return FetchStatus.UNAUTHORIZED;
        if (statusCode >= 400 && statusCode < 500) return FetchStatus.CLIENT_ERROR;
        if (statusCode >= 500) return FetchStatus.SERVER_ERROR;
        return FetchStatus.ERROR;
    }

    private _configError(message: string, timestamp: string): FetchStatusResult {
        return {
            provider_name: this.providerName,
            status: FetchStatus.CONFIG_ERROR,
            latency_ms: 0,
            timestamp,
            // Provide placeholder request/config info for error response consistency
            request: { method: 'UNKNOWN', url: 'UNKNOWN', timeout_seconds: 0 },
            config_used: this._buildConfigUsed("ERROR", "ERROR"),
            fetch_option_used: this._buildFetchOptionUsed("ERROR", "ERROR", {}),
            error: { type: "ConfigError", message },
        };
    }

    private _truncate(text: string, maxLen: number = 500): string {
        if (text.length <= maxLen) return text;
        return text.substring(0, maxLen) + "... (truncated)";
    }
}
