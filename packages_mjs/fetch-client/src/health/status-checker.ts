/**
 * Fetch Status Checker Implementation.
 */
import { FetchClient } from "../client.js";
import { ClientConfig } from "../config.js";
import { FetchStatus, FetchStatusResult } from "./models.js";

interface ComputeAllResult {
    config: Record<string, any>;
    authConfig?: any; // AppYamlConfig auth config structure (camelCase)
    proxyConfig?: any; // camelCase
    networkConfig?: any; // camelCase
    headers?: Record<string, string>;
}

export class FetchStatusChecker {
    constructor(
        private provider_name: string,
        private runtime_config: ComputeAllResult,
        private timeout_seconds: number = 10.0,
        private endpoint_override?: string
    ) { }

    public async check(): Promise<FetchStatusResult> {
        const timestamp = new Date().toISOString();
        const startTime = performance.now();

        // Validate config
        if (!this.runtime_config.config.base_url) {
            return this._configError("base_url is required", timestamp);
        }

        const healthEndpoint = this._resolveHealthEndpoint();
        const baseUrl = this.runtime_config.config.base_url;
        // Basic url joining to look nice in status
        const fullUrl = `${baseUrl.replace(/\/$/, "")}/${healthEndpoint.replace(/^\//, "")}`;

        const method = this._resolveMethod();
        const requestInfo = {
            method,
            url: fullUrl,
            timeout_seconds: this.timeout_seconds,
        };

        const configUsed = this._buildConfigUsed(healthEndpoint, method);

        // Build fetch_option_used before making request
        const preComputedHeaders = this.runtime_config.headers || {};
        const configHeaders = this.runtime_config.config.headers || {};
        const mergedHeaders = { ...configHeaders, ...preComputedHeaders };

        const fetchOptionUsed = this._buildFetchOptionUsed(
            method,
            fullUrl,
            mergedHeaders
        );

        let client: FetchClient | undefined;

        try {
            client = this._createClient();
            const response = await client.request({
                method: method as any,
                url: healthEndpoint
            });

            const latencyMs = performance.now() - startTime;

            // Read body safely
            let bodyPreview = "";
            try {
                const text = response.data ? (typeof response.data === 'string' ? response.data : JSON.stringify(response.data)) : "";
                bodyPreview = this._truncate(text);
            } catch (e) {
                bodyPreview = "[Unable to read body]";
            }

            return {
                provider_name: this.provider_name,
                status: this._statusFromCode(response.status),
                latency_ms: Number(latencyMs.toFixed(2)),
                timestamp,
                request: requestInfo,
                response: {
                    status_code: response.status,
                    status_text: response.statusText,
                    content_type: response.headers instanceof Map ? response.headers.get("content-type") : (response.headers as any)["content-type"],
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
            if (e.name === "ConnectTimeoutError" || e.code === "UND_ERR_CONNECT_TIMEOUT") {
                status = FetchStatus.TIMEOUT;
                errorType = "TimeoutException";
            } else if (e.name === "SocketError" || e.code === "UND_ERR_SOCKET") {
                status = FetchStatus.CONNECTION_ERROR;
                errorType = "ConnectError";
            }

            return {
                provider_name: this.provider_name,
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
                    name: e.name
                },
            };

        } finally {
            // BaseClient/undici dispatcher management is handled by the instance.
            // We should ideally close it if we created a dedicated one, but FetchClient
            // doesn't expose close() primarily because it shares the global dispatcher if not specified.
            // However, BaseClient DOES have a close() method if we want to be clean.
            // checking if we can cast or if we exposed it. BaseClient has close().
            if (client && typeof (client as any).close === 'function') {
                await (client as any).close();
            }
        }
    }

    private _resolveHealthEndpoint(): string {
        let endpoint: string;
        if (this.endpoint_override) {
            endpoint = this.endpoint_override;
        } else if (this.runtime_config.config.health_endpoint) {
            const healthConf = this.runtime_config.config.health_endpoint;
            if (typeof healthConf === 'object' && healthConf !== null) {
                endpoint = healthConf.path || healthConf.endpoint;
                if (!endpoint) {
                    throw new Error(`health_endpoint object missing 'path' in provider config for '${this.provider_name}'`);
                }
            } else {
                endpoint = String(healthConf);
            }
        } else {
            throw new Error(`health_endpoint is required in provider config for '${this.provider_name}'`);
        }

        // Replace placeholders like :username, :email with actual values from authConfig
        return this._resolvePlaceholders(endpoint);
    }

    private _resolvePlaceholders(endpoint: string): string {
        const auth = this.runtime_config.authConfig;
        const config = this.runtime_config.config;

        // Build replacement map from auth and config values
        const replacements: Record<string, string | undefined> = {
            ':username': auth?.username || config?.username,
            ':email': auth?.email || config?.email,
            ':user': auth?.username || config?.username,
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
        const config = this.runtime_config.config || {};

        // Check if health_endpoint is object with method
        const healthEndpointConfig = config.health_endpoint;
        if (typeof healthEndpointConfig === 'object' && healthEndpointConfig?.method) {
            return String(healthEndpointConfig.method).toUpperCase();
        }

        // Fallback to top-level method
        if (config.method) {
            return String(config.method).toUpperCase();
        }

        return "GET";
    }

    private _createClient(): FetchClient {
        // Use pre-computed headers from YamlConfigFactory which includes properly
        // encoded Authorization header via encodeAuth (handles basic, bearer, etc.)
        // This is the correct approach - YamlConfigFactory already handles all auth
        // types and encodes credentials properly.
        const preComputedHeaders = this.runtime_config.headers || {};
        const configHeaders = this.runtime_config.config.headers || {};

        // Merge: pre-computed auth headers take precedence
        const mergedHeaders = {
            ...configHeaders,
            ...preComputedHeaders,
        };

        const config: ClientConfig = {
            baseUrl: this.runtime_config.config.base_url,
            // Do NOT pass auth config - we're using pre-computed headers instead
            // This avoids double-encoding issues and ensures YamlConfigFactory's
            // encodeAuth logic (which handles all 15 auth types) is used.
            contentType: "application/json",
            headers: mergedHeaders,
            timeout: this.timeout_seconds * 1000, // Client expects ms
        };

        return FetchClient.create(config);
    }

    private _buildConfigUsed(healthEndpoint: string, method: string): Record<string, any> {
        const auth = this.runtime_config.authConfig;
        const proxy = this.runtime_config.proxyConfig;
        const authTypeStr = auth?.type?.value || auth?.type;
        const preComputedHeaders = this.runtime_config.headers || {};
        const hasAuthHeader = Boolean(preComputedHeaders['Authorization'] || preComputedHeaders['authorization']);

        return {
            base_url: this.runtime_config.config.base_url,
            health_endpoint: healthEndpoint,
            method,
            timeout_seconds: this.timeout_seconds,
            auth_type: authTypeStr,
            auth_resolved: Boolean(auth && auth.token),
            auth_header_present: hasAuthHeader,
            is_placeholder: auth?.resolution?.isPlaceholder, // YamlConfigFactory isPlaceholder
            proxy_url: proxy?.proxyUrl, // YamlConfigFactory proxyUrl
            proxy_resolved: Boolean(proxy && proxy.proxyUrl),
            headers_count: Object.keys(preComputedHeaders).length,
        };
    }

    private _statusFromCode(statusCode: number): FetchStatus {
        if (statusCode >= 200 && statusCode < 300) return FetchStatus.CONNECTED;
        if (statusCode === 401 || statusCode === 403) return FetchStatus.UNAUTHORIZED;
        if (statusCode >= 400 && statusCode < 500) return FetchStatus.CLIENT_ERROR;
        if (statusCode >= 500) return FetchStatus.SERVER_ERROR;
        return FetchStatus.ERROR;
    }

    private _configError(message: string, timestamp: string): FetchStatusResult {
        return {
            provider_name: this.provider_name,
            status: FetchStatus.CONFIG_ERROR,
            latency_ms: 0,
            timestamp,
            error: { type: "ConfigError", message },
        };
    }

    private _truncate(text: string, maxLen: number = 500): string {
        if (text.length <= maxLen) return text;
        return text.substring(0, maxLen) + "... (truncated)";
    }

    private _maskHeaderValue(key: string, value: string): string {
        const sensitiveKeys = new Set(['authorization', 'x-api-key', 'api-key', 'token', 'secret']);
        if (sensitiveKeys.has(key.toLowerCase())) {
            if (value.length <= 20) {
                return "****";
            }
            return `${value.substring(0, 20)}...`;
        }
        return value;
    }

    private _buildFetchOptionUsed(
        method: string,
        fullUrl: string,
        mergedHeaders: Record<string, string>,
    ): Record<string, any> {
        const config = this.runtime_config.config || {};
        const proxy = this.runtime_config.proxyConfig;

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
            timeout_seconds: this.timeout_seconds,
            headers: maskedHeaders,
            headers_count: Object.keys(mergedHeaders).length,
            follow_redirects: config.follow_redirects ?? true,
            proxy: proxyUrl,
            verify_ssl: config.verify_ssl ?? true,
        };
    }
}
