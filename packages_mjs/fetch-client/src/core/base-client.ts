/**
 * Core HTTP client implementation based on undici.
 */
import { Client, Dispatcher, Pool, request } from 'undici';
import { AuthHandler, createAuthHandler } from '../auth/auth-handler.js';
import { ClientConfig, ResolvedConfig, resolveConfig } from '../config.js';
import { FetchResponse, RequestContext, RequestOptions } from '../types.js';

const LOG_PREFIX = '[FetchClient]';

/**
 * Format body for logging safeguards against binary data.
 * FIX GAP-2.2: Implement safe body logging parity with Python.
 */
function _formatBody(body: any): string {
    if (body === undefined || body === null) {
        return '<empty>';
    }

    // Binary checks
    if (body instanceof Buffer || body instanceof Uint8Array || body instanceof ArrayBuffer) {
        return `<binary data: ${body.byteLength || (body as Buffer).length} bytes>`;
    }

    // String checks
    if (typeof body === 'string') {
        try {
            if (body.trim().startsWith('{') || body.trim().startsWith('[')) {
                return JSON.stringify(JSON.parse(body), null, 2);
            }
        } catch {
            // Not JSON
        }

        if (body.length > 5000) {
            return body.slice(0, 5000) + '... (truncated)';
        }
        return body;
    }

    // Object/Array
    if (typeof body === 'object') {
        try {
            return JSON.stringify(body, null, 2);
        } catch (e) {
            return '[Circular or Unserializable Object]';
        }
    }

    return String(body);
}

export class BaseClient {
    private config: ResolvedConfig;
    private dispatcher?: Dispatcher;
    private authHandler?: AuthHandler;
    private ownDispatcher: boolean = false;
    private origin: string;
    private basePath: string;

    constructor(config: ClientConfig) {
        this.config = resolveConfig(config);

        // Parse Origin and BasePath to safely support baseUrls with paths (e.g. https://api.com/v1)
        // undici.Pool only accepts origin, so we must manually prepend basePath to requests.
        try {
            const url = new URL(this.config.baseUrl);
            this.origin = url.origin;
            this.basePath = url.pathname;
            // Normalize basePath: remove trailing slash unless it's just root
            if (this.basePath.endsWith('/') && this.basePath.length > 1) {
                this.basePath = this.basePath.slice(0, -1);
            }
            if (this.basePath === '/') {
                this.basePath = '';
            }
        } catch (e) {
            // Fallback (e.g. relative URLs? mostly unlikely in this context)
            this.origin = this.config.baseUrl;
            this.basePath = '';
        }

        // Setup Auth
        if (this.config.auth) {
            this.authHandler = createAuthHandler(this.config.auth);
        }

        // Setup Dispatcher if provided
        // casting because undici types might mismatch strictly with 'any'
        this.dispatcher = config.dispatcher;
        this.ownDispatcher = !this.dispatcher;
    }

    /**
     * Initialize dispatcher if needed.
     */
    private ensureDispatcher() {
        if (this.dispatcher) return;

        // Create default client/pool
        // Undici Client is for single origin, Pool is for single origin? 
        // Agent is for multiple? Undici 'request' uses global dispatcher usually.
        // If baseUrl is set, we can use a Client optimized for that origin.

        // Using a Pool for the base URL is efficient for repeated requests.
        this.dispatcher = new Pool(this.origin, {
            connect: {
                timeout: this.config.timeout.connect
            },
            headersTimeout: this.config.timeout.read,
            bodyTimeout: this.config.timeout.read,
            // Disable keep-alive timeouts or set appropriately?
        });
        this.ownDispatcher = true;
    }

    async close(): Promise<void> {
        if (this.ownDispatcher && this.dispatcher) {
            await this.dispatcher.close();
            this.dispatcher = undefined;
        }
    }

    async request<T = any>(options: RequestOptions): Promise<FetchResponse<T>> {
        const { response, path } = await this.dispatchRequest(options);

        // Response parsing
        let data: any;
        const contentType = response.headers['content-type'] || '';
        const text = await response.body.text();

        try {
            if (contentType.includes('application/json')) {
                // Handle empty body for JSON content type
                data = text ? JSON.parse(text) : {};
            } else {
                data = text;
            }
        } catch {
            data = text;
        }

        return {
            status: response.statusCode,
            statusText: '',
            headers: response.headers as Record<string, string>,
            url: `${this.config.baseUrl}${path}`,
            data,
            ok: response.statusCode >= 200 && response.statusCode < 300
        };
    }

    /**
     * Allows streaming response consumption without buffering the entire body.
     */
    async rawStream(options: RequestOptions): Promise<FetchResponse<ReadableStream>> {
        const { response, path } = await this.dispatchRequest(options);

        return {
            status: response.statusCode,
            statusText: '',
            headers: response.headers as Record<string, string>,
            url: `${this.config.baseUrl}${path}`,
            data: response.body, // Return the raw ReadableStream
            ok: response.statusCode >= 200 && response.statusCode < 300
        };
    }

    /**
     * Internal dispatch helper to reuse logic for request/stream.
     */
    protected async dispatchRequest(options: RequestOptions): Promise<{ response: any, path: string }> {
        this.ensureDispatcher();

        const method = options.method || 'GET';
        // URL handling: passed url is relative path usually, but undici Pool expects path.
        // If baseUrl was used to create Pool, we just pass path.
        const reqPath = options.url || '/';

        // Headers
        const headers: Record<string, string> = {
            ...this.config.headers,
            ...(options.headers || {})
        };

        // Content Type
        if (options.json && !headers['content-type']) {
            headers['content-type'] = 'application/json';
        }

        // Body
        let body: any = options.body;
        if (options.json) {
            body = JSON.stringify(options.json);
        }

        // Auth
        if (this.authHandler) {
            const context: RequestContext = {
                method,
                url: `${this.config.baseUrl}${reqPath.startsWith('/') ? '' : '/'}${reqPath}`,
                headers,
                body: options.json || body
            };
            const authHeaders = this.authHandler.getHeader(context);
            if (authHeaders) {
                Object.assign(headers, authHeaders);
            }
        }

        // Logging
        // console.debug(`${LOG_PREFIX} Request: ${method} ${path}`);

        try {
            // If we are using a Pool (bound to baseUrl), we pass just the path.
            // But if dispatcher is Agent (or MockAgent), we typically need full URL for it to route correctly.
            // Undici MockAgent intercepts based on origin + path.

            // Check for Pool OR MockPool (which behaves like Pool regarding path)
            const isPool = this.dispatcher instanceof Pool || this.dispatcher?.constructor.name === 'MockPool';

            // Calculate effective path including params from baseUrl if any (e.g. /api/v1)
            // If isPool (bound to origin), we must supply full path /api/v1/users
            // If !isPool (Agent), we supply full URL https://host/api/v1/users

            const effectivePath = this.basePath
                ? `${this.basePath}${reqPath.startsWith('/') ? '' : '/'}${reqPath}`
                : reqPath;

            const targetUrl = isPool ? effectivePath : `${this.origin}${effectivePath.startsWith('/') ? '' : '/'}${effectivePath}`;

            // console.log('Requesting:', targetUrl, 'isPool:', isPool);

            const response = await this.dispatcher!.request({
                method,
                path: targetUrl,
                query: options.query,
                headers,
                body,
                headersTimeout: options.timeout || this.config.timeout.read
            });

            return { response, path: reqPath };

        } catch (e) {
            // console.error(`${LOG_PREFIX} Request failed:`, e);
            throw e;
        }
    }
}
