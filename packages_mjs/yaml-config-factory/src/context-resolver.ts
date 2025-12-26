import { resolve } from '@internal/runtime-template-resolver';
import { ContextComputeRegistry } from './compute-registry.js';
import { TemplateContext } from './context.js';

const TEMPLATE_PATTERN = /\{\{[^}]+\}\}|\$\.[a-zA-Z_]/;
const FUNCTION_PATTERN = /^\{\{fn:([a-zA-Z_][a-zA-Z0-9_]*)\}\}$/;

function hasTemplate(value: string): boolean {
    if (!value) return false;
    return TEMPLATE_PATTERN.test(value);
}

function isFunctionRef(value: string): [boolean, string] {
    if (!value) return [false, ""];
    const match = value.trim().match(FUNCTION_PATTERN);
    if (match) {
        return [true, match[1]];
    }
    return [false, ""];
}

async function resolveValue(value: string, context: TemplateContext, request?: any): Promise<any> {
    const [isFn, resolverName] = isFunctionRef(value);

    if (isFn) {
        return await ContextComputeRegistry.resolve(resolverName, context, request);
    } else if (hasTemplate(value)) {
        return resolve(value, context as unknown as Record<string, unknown>);
    }
    return value;
}

export async function resolveDeep(
    obj: any,
    context: TemplateContext,
    request?: any,
    visited: Set<any> = new Set()
): Promise<any> {
    if (obj === null || obj === undefined) return obj;
    if (visited.has(obj)) return obj;

    if (typeof obj === 'string') {
        return await resolveValue(obj, context, request);
    }

    if (Array.isArray(obj)) {
        visited.add(obj);
        const result = await Promise.all(obj.map(item => resolveDeep(item, context, request, visited)));
        return result;
    }

    if (typeof obj === 'object') {
        visited.add(obj);
        const result: Record<string, any> = {};
        for (const [key, value] of Object.entries(obj)) {
            result[key] = await resolveDeep(value, context, request, visited);
        }
        return result;
    }

    return obj;
}

export function deepMerge(base: Record<string, any>, overlay: Record<string, any>): Record<string, any> {
    const result = { ...base };

    for (const [key, value] of Object.entries(overlay)) {
        if (
            key in result &&
            result[key] &&
            typeof result[key] === 'object' &&
            !Array.isArray(result[key]) &&
            value &&
            typeof value === 'object' &&
            !Array.isArray(value)
        ) {
            result[key] = deepMerge(result[key], value);
        } else {
            result[key] = value;
        }
    }
    return result;
}

export class ContextResolver {
    constructor(private context: TemplateContext, private request?: any) { }

    async applyContextOverwrite(
        config: Record<string, any>,
        contextMeta: Record<string, any>
    ): Promise<Record<string, any>> {
        if (!contextMeta) return config;

        // Resolve all templates and functions in the context_meta
        const resolvedOverlay = await resolveDeep(contextMeta, this.context, this.request);

        // Deep merge resolved values into config
        return deepMerge(config, resolvedOverlay);
    }
}
