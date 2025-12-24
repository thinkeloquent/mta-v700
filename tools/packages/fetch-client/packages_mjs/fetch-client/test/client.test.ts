/**
 * Tests for FetchClient.
 */
import { FetchClient } from '../src/client.js';
import { ClientConfig } from '../src/config.js';
import { MockAgent } from 'undici';

describe('FetchClient', () => {
    let mockAgent: MockAgent;

    beforeEach(() => {
        mockAgent = new MockAgent();
        mockAgent.disableNetConnect();
    });

    test('get request', async () => {
        const mockPool = mockAgent.get('https://example.com');
        mockPool.intercept({ path: '/test?q=foo' }).reply(200, { a: 1 }, { headers: { 'content-type': 'application/json' } });

        const config: ClientConfig = {
            baseUrl: 'https://example.com',
            dispatcher: mockPool as any,
            headers: {},
            contentType: 'application/json'
        };
        const client = FetchClient.create(config);

        const res = await client.get('/test', { query: { q: 'foo' } });
        expect(res.status).toBe(200);
        expect(res.data).toEqual({ a: 1 });
    });

    test('post request', async () => {
        const mockPool = mockAgent.get('https://example.com');
        mockPool.intercept({
            path: '/items',
            method: 'POST'
        }).reply(201, { id: 123 }, { headers: { 'content-type': 'application/json' } });

        const config: ClientConfig = {
            baseUrl: 'https://example.com',
            dispatcher: mockPool as any,
            headers: {},
            contentType: 'application/json'
        };
        const client = FetchClient.create(config);

        const res = await client.post('/items', { name: 'item1' });
        expect(res.status).toBe(201);
        expect(res.data).toEqual({ id: 123 });
    });

    test('stream generic sse', async () => {
        const mockPool = mockAgent.get('https://example.com');
        mockPool.intercept({
            path: '/stream',
            headers: { 'Accept': 'text/event-stream' }
        }).reply(200, 'data: hello\n\ndata: world\n\n');

        const config: ClientConfig = {
            baseUrl: 'https://example.com',
            dispatcher: mockPool as any,
            headers: {},
            contentType: 'application/json'
        };
        const client = FetchClient.create(config);

        const events: any[] = [];
        for await (const event of client.stream('/stream')) {
            events.push(event);
        }

        expect(events).toHaveLength(2);
        expect(events[0].data).toBe('hello');
        expect(events[1].data).toBe('world');
    });
});
