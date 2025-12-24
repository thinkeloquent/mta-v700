/**
 * Request builder helper.
 */
import { HttpMethod, RequestOptions } from '../types.js';

export class RequestBuilder {
    private options: RequestOptions;

    constructor(url: string = '', method: HttpMethod = 'GET') {
        this.options = {
            url,
            method,
            headers: {},
            query: {}
        };
    }

    url(url: string): this {
        this.options.url = url;
        return this;
    }

    method(method: HttpMethod): this {
        this.options.method = method;
        return this;
    }

    header(key: string, value: string): this {
        this.options.headers = this.options.headers || {};
        this.options.headers[key] = value;
        return this;
    }

    headers(headers: Record<string, string>): this {
        this.options.headers = { ...this.options.headers, ...headers };
        return this;
    }

    param(key: string, value: any): this {
        this.options.query = this.options.query || {};
        this.options.query[key] = value;
        return this;
    }

    params(params: Record<string, any>): this {
        this.options.query = { ...this.options.query, ...params };
        return this;
    }

    json(data: any): this {
        this.options.json = data;
        return this;
    }

    /**
     * Set raw body.
     */
    body(data: string | Buffer | Uint8Array | null): this {
        this.options.body = data;
        return this;
    }

    timeout(timeout: number): this {
        this.options.timeout = timeout;
        return this;
    }

    build(): RequestOptions {
        return this.options;
    }
}
