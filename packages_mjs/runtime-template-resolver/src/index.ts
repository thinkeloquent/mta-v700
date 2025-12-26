import { PATTERNS } from './patterns.js';
import { resolvePath } from './resolver.js';
import { coerceToString } from './coercion.js';

export function resolve(template: string, context: Record<string, unknown>): string {
    if (!template) return "";

    let result = template;

    // Process mustache syntax {{path}}
    result = result.replace(PATTERNS.MUSTACHE, (match, path, defaultVal) => {
        const key = path.trim();
        const val = resolvePath(context, key);
        if (val === undefined) {
            return defaultVal !== undefined ? defaultVal : match;
        }
        return coerceToString(val);
    });

    // Process dot path syntax $.path
    result = result.replace(PATTERNS.DOT_PATH, (match, path) => {
        const val = resolvePath(context, path);
        if (val === undefined) {
            return match; // Keep literal
        }
        return coerceToString(val);
    });

    // Restore escaped placeholders
    result = result.replace(PATTERNS.ESCAPED_DOT, "$.");
    result = result.replace(PATTERNS.ESCAPED_MUSTACHE, "{{");

    return result;
}
