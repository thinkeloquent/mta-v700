/**
 * Fetch Status Checker Implementation.
 */
import { FetchClient } from "../client.js";
import { AuthConfig, ClientConfig } from "../config.js";
import { FetchStatus, FetchStatusResult } from "./models.js";

interface ComputeAllResult {
    config: Record<string, any>;
    auth_config?: any; // AppYamlConfig auth config structure
    proxy_config?: any;
    network_config?: any;
    headers?: Record<string, string>;
}

export class FetchStatusChecker {
    private static DEFAULT_ENDPOINTS: Record<string, string> = {
        gemini_openai: "/models",
        openai: "/models",
        anthropic: "/models",
        github: "/user",
        default: "/",
    };

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
        if (this.endpoint_override) return this.endpoint_override;
        if (this.runtime_config.config.health_endpoint) {
            return this.runtime_config.config.health_endpoint;
        }
        return FetchStatusChecker.DEFAULT_ENDPOINTS[this.provider_name] || FetchStatusChecker.DEFAULT_ENDPOINTS["default"];
    }

    private _createClient(): FetchClient {
        let authConfig: AuthConfig | undefined;
        if (this.runtime_config.auth_config) {
            authConfig = this._convertAuthConfig(this.runtime_config.auth_config);
        }

        const config: ClientConfig = {
            baseUrl: this.runtime_config.config.base_url,
            auth: authConfig,
            contentType: "application/json",
            headers: this.runtime_config.config.headers || {},
            timeout: this.timeout_seconds * 1000, // Client expects ms
        };

        return FetchClient.create(config);
    }

    private _convertAuthConfig(auth: any): AuthConfig {
        // Convert yaml_config/AppYamlConfig auth structure to FetchClient AuthConfig
        // Note: auth.type might be an Enum object or string depending on source
        const typeVal = auth.type?.value || auth.type;

        return {
            type: asAuthType(typeVal),
            rawApiKey: auth.token,
            username: auth.username,
            password: auth.password,
            email: auth.email,
            headerName: auth.header_name,
        };
    }

    private _buildConfigUsed(healthEndpoint: string): Record<string, any> {
        const auth = this.runtime_config.auth_config;
        const authTypeStr = auth?.type?.value || auth?.type;

        return {
            base_url: this.runtime_config.config.base_url,
            health_endpoint: healthEndpoint,
            auth_type: authTypeStr,
            auth_resolved: Boolean(auth && auth.token),
            is_placeholder: auth?.resolution?.is_placeholder,
            proxy_url: this.runtime_config.proxy_config?.proxy_url,
            headers_count: Object.keys(this.runtime_config.config.headers || {}).length,
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

// Helper to safely cast auth type string
import { AuthType } from "../types.js";
function asAuthType(val: string): AuthType {
    // In a real scenario we might validate, but for now we trust the upstream resolver or default to custom
    return val as AuthType;
}
