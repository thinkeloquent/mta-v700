import type { AppYamlConfig, LoadResult } from '@internal/app-yaml-config';

export interface TemplateContext {
    env: Record<string, string>;
    request: Record<string, any>;
    app: {
        name: string;
        version: string;
        description: string;
        environment: string;
    };
    config: Record<string, any>;
}

export class ContextBuilder {
    static buildStartupContext(config: AppYamlConfig): TemplateContext {
        const loadResult = config.getLoadResult();
        // Use public API to access app config (was incorrectly using _config which doesn't exist)
        const rawAppConfig = config.get<Record<string, any>>('app') || {};

        const appEnv = loadResult?.appEnv || 'dev';

        return {
            env: { ...process.env } as Record<string, string>,
            app: {
                name: rawAppConfig.name || 'unknown',
                version: rawAppConfig.version || '0.0.0',
                description: rawAppConfig.description || '',
                environment: appEnv
            },
            request: {},
            config: config.getAll()
        };
    }

    static buildRequestContext(request: any): Record<string, unknown> {
        if (!request) {
            return { headers: {}, query: {}, path: {} };
        }

        // Handle Fastify/Express Request
        return {
            headers: request.headers ? { ...request.headers } : {},
            query: request.query ? { ...request.query } : {},
            params: request.params ? { ...request.params } : {}
        };
    }

    static mergeContexts(startup: TemplateContext, requestCtx: Record<string, unknown>): TemplateContext {
        return {
            ...startup,
            request: requestCtx
        };
    }
}
