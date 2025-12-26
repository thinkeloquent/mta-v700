import { PATTERNS } from './patterns.js';

export interface Placeholder {
    raw: string;
    path: string;
    default?: string;
    start: number;
    end: number;
    syntax: 'MUSTACHE' | 'DOT_PATH';
}

export function extractPlaceholders(template: string): Placeholder[] {
    const placeholders: Placeholder[] = [];

    // Reset lastIndex for global regex
    PATTERNS.MUSTACHE.lastIndex = 0;
    PATTERNS.DOT_PATH.lastIndex = 0;

    let match;
    while ((match = PATTERNS.MUSTACHE.exec(template)) !== null) {
        placeholders.push({
            raw: match[0],
            path: match[1]?.trim(),
            default: match[2],
            start: match.index,
            end: match.index + match[0].length,
            syntax: 'MUSTACHE'
        });
    }

    while ((match = PATTERNS.DOT_PATH.exec(template)) !== null) {
        placeholders.push({
            raw: match[0],
            path: match[1],
            default: undefined,
            start: match.index,
            end: match.index + match[0].length,
            syntax: 'DOT_PATH'
        });
    }

    return placeholders;
}
