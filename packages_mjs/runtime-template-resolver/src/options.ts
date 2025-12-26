import { MissingStrategy } from './types.js';

export interface ResolveOptions {
    missingStrategy?: MissingStrategy;
    throwOnError?: boolean;
}
