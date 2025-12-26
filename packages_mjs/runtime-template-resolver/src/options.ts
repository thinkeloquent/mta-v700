import { MissingStrategy } from './types';

export interface ResolveOptions {
    missingStrategy?: MissingStrategy;
    throwOnError?: boolean;
}
