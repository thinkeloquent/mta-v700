import { parsePath } from './path-parser.js';

export class SecurityError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'SecurityError';
    }
}

export function resolvePath(obj: unknown, path: string): unknown {
    const segments = parsePath(path);
    let current: any = obj;

    for (const segment of segments) {
        if (current === null || current === undefined) {
            return undefined;
        }

        // Prevent prototype pollution / unsafe access
        if (segment === '__proto__' || segment === 'constructor' || segment === 'prototype') {
            throw new SecurityError(`Unsafe path segment: ${segment}`);
        }

        if (typeof current !== 'object') {
            return undefined;
        }

        current = current[segment];
    }

    return current;
}
