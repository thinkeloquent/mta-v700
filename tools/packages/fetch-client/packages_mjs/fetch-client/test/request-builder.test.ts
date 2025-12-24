/**
 * Tests for RequestBuilder.
 */
import { RequestBuilder } from '../src/core/request.js';

describe('RequestBuilder', () => {
    test('builds options correctly', () => {
        const builder = new RequestBuilder('https://example.com/api', 'POST');
        const opts = builder
            .header('Authorization', 'Bearer token')
            .param('q', 'search')
            .json({ foo: 'bar' })
            .timeout(10000)
            .build();

        expect(opts.url).toBe('https://example.com/api');
        expect(opts.method).toBe('POST');
        expect(opts.headers?.['Authorization']).toBe('Bearer token');
        expect(opts.query?.['q']).toBe('search');
        expect(opts.json).toEqual({ foo: 'bar' });
        expect(opts.timeout).toBe(10000);
    });
});
