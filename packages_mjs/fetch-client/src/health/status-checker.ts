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

        const requestInfo = {
            method: "GET",
            url: fullUrl,
            timeout_seconds: this.timeout_seconds,
        };

        const configUsed = this._buildConfigUsed(healthEndpoint);

        let client: FetchClient | undefined;

        try {
            client = this._createClient();
            const response = await client.get(healthEndpoint);

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
            endpoint = this.runtime_config.config.health_endpoint;
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

    private _buildConfigUsed(healthEndpoint: string): Record<string, any> {
        const auth = this.runtime_config.authConfig;
        const authTypeStr = auth?.type?.value || auth?.type;
        const preComputedHeaders = this.runtime_config.headers || {};
        const hasAuthHeader = Boolean(preComputedHeaders['Authorization'] || preComputedHeaders['authorization']);

        return {
            base_url: this.runtime_config.config.base_url,
            health_endpoint: healthEndpoint,
            auth_type: authTypeStr,
            auth_resolved: Boolean(auth && auth.token),
            auth_header_present: hasAuthHeader,
            is_placeholder: auth?.resolution?.isPlaceholder, // YamlConfigFactory isPlaceholder
            proxy_url: this.runtime_config.proxyConfig?.proxyUrl, // YamlConfigFactory proxyUrl
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
}
