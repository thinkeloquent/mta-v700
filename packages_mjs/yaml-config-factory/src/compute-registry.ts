import { TemplateContext } from './context.js';

type ResolverFn = (context: TemplateContext, request?: any) => Promise<any> | any;

export class ContextComputeRegistry {
    private static startupResolvers: Map<string, ResolverFn> = new Map();
    private static requestResolvers: Map<string, ResolverFn> = new Map();

    static registerStartup(name: string, fn: ResolverFn) {
        this.startupResolvers.set(name, fn);
    }

    static registerRequest(name: string, fn: ResolverFn) {
        this.requestResolvers.set(name, fn);
    }

    static async resolve(name: string, context: TemplateContext, request?: any): Promise<any> {
        // Try request resolver first
        if (this.requestResolvers.has(name)) {
            const fn = this.requestResolvers.get(name)!;
            return await fn(context, request);
        }

        // Then startup resolver
        if (this.startupResolvers.has(name)) {
            const fn = this.startupResolvers.get(name)!;
            return await fn(context);
        }

        throw new Error(`No resolver registered for '${name}'`);
    }

    static hasResolver(name: string): boolean {
        return this.startupResolvers.has(name) || this.requestResolvers.has(name);
    }
}
