/**
 * High-level FetchClient implementation.
 */
import { BaseClient } from './core/base-client.js';
import { RequestBuilder } from './core/request.js';
import { ClientConfig } from './config.js';
import { FetchResponse, RequestOptions, SSEEvent } from './types.js';

export class FetchClient extends BaseClient {

    static create(config: ClientConfig): FetchClient {
        return new FetchClient(config);
    }

    async get<T = any>(
        url: string,
        options?: {
            query?: Record<string, any>;
            headers?: Record<string, string>;
            timeout?: number;
        }
    ): Promise<FetchResponse<T>> {
        const builder = new RequestBuilder(url, 'GET');
        if (options?.query) builder.params(options.query);
        if (options?.headers) builder.headers(options.headers);
        if (options?.timeout) builder.timeout(options.timeout);
        return this.request<T>(builder.build());
    }

    async post<T = any>(
        url: string,
        body?: any,
        options?: {
            query?: Record<string, any>;
            headers?: Record<string, string>;
            timeout?: number;
        }
    ): Promise<FetchResponse<T>> {
        const builder = new RequestBuilder(url, 'POST');
        if (body !== undefined) builder.json(body);
        if (options?.query) builder.params(options.query);
        if (options?.headers) builder.headers(options.headers);
        if (options?.timeout) builder.timeout(options.timeout);
        return this.request<T>(builder.build());
    }

    async put<T = any>(
        url: string,
        body?: any,
        options?: {
            query?: Record<string, any>;
            headers?: Record<string, string>;
            timeout?: number;
        }
    ): Promise<FetchResponse<T>> {
        const builder = new RequestBuilder(url, 'PUT');
        if (body !== undefined) builder.json(body);
        if (options?.query) builder.params(options.query);
        if (options?.headers) builder.headers(options.headers);
        if (options?.timeout) builder.timeout(options.timeout);
        return this.request<T>(builder.build());
    }

    async patch<T = any>(
        url: string,
        body?: any,
        options?: {
            query?: Record<string, any>;
            headers?: Record<string, string>;
            timeout?: number;
        }
    ): Promise<FetchResponse<T>> {
        const builder = new RequestBuilder(url, 'PATCH');
        if (body !== undefined) builder.json(body);
        if (options?.query) builder.params(options.query);
        if (options?.headers) builder.headers(options.headers);
        if (options?.timeout) builder.timeout(options.timeout);
        return this.request<T>(builder.build());
    }

    async delete<T = any>(
        url: string,
        options?: {
            query?: Record<string, any>;
            headers?: Record<string, string>;
            timeout?: number;
        }
    ): Promise<FetchResponse<T>> {
        const builder = new RequestBuilder(url, 'DELETE');
        if (options?.query) builder.params(options.query);
        if (options?.headers) builder.headers(options.headers);
        if (options?.timeout) builder.timeout(options.timeout);
        return this.request<T>(builder.build());
    }

    // Streaming support
    // Implementing basic SSE stream by reusing request logic or custom?
    // Undici stream() is useful.

    // For now, partial implementation matching Python's simple assumption
    async *stream(
        url: string,
        options?: {
            method?: string;
            body?: any;
            query?: Record<string, any>;
            headers?: Record<string, string>;
            timeout?: number;
        }
    ): AsyncGenerator<SSEEvent, void, unknown> {
        const builder = new RequestBuilder(url, (options?.method as any) || 'GET');
        if (options?.body !== undefined) builder.json(options.body); // Assume JSON body if provided? Or raw? 
        // Python generic stream accepts json/data. Here we just take body.
        // Let's assume json for now or improve signature.

        if (options?.query) builder.params(options.query);
        if (options?.headers) builder.headers(options.headers);
        if (options?.timeout) builder.timeout(options.timeout);

        // Force Accept header
        builder.header('Accept', 'text/event-stream');

        const requestOptions = builder.build();
        const response = await this.rawStream(requestOptions);

        if (!response.ok) {
            // Throw error or yield error event? 
            // Python raises for status.
            throw new Error(`Request failed with status ${response.status}`);
        }

        const body = response.data as any; // Async Iterable

        // Simple SSE Parser
        let buffer = '';
        for await (const chunk of body) {
            buffer += chunk.toString();

            let parts = buffer.split(/\n\n/);
            // Keep the last part in buffer as it might be incomplete
            // unless buffer ends with \n\n
            if (!buffer.endsWith('\n\n')) {
                buffer = parts.pop() || '';
            } else {
                buffer = '';
            }

            for (const part of parts) {
                if (!part.trim()) continue;

                const event: SSEEvent = { data: '' };
                const lines = part.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        event.data = line.slice(6);
                    } else if (line.startsWith('event: ')) {
                        event.event = line.slice(7);
                    } else if (line.startsWith('id: ')) {
                        event.id = line.slice(4);
                    } else if (line.startsWith('retry: ')) {
                        event.retry = parseInt(line.slice(7), 10);
                    }
                }

                if (event.data) {
                    yield event;
                }
            }
        }
    }
}
