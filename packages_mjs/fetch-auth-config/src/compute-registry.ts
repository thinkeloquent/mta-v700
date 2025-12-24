import { ComputeFunctionNotFoundError, ComputeFunctionError } from './errors.js';

export type StartupComputeFn = (server: any) => string | Promise<string>;
export type RequestComputeFn = (request: any) => string | Promise<string>;

export class ComputeRegistry {
    private static startupResolvers: Map<string, StartupComputeFn> = new Map();
    private static requestResolvers: Map<string, RequestComputeFn> = new Map();

    static registerStartup(providerName: string, fn: StartupComputeFn) {
        this.startupResolvers.set(providerName, fn);
    }

    static registerRequest(providerName: string, fn: RequestComputeFn) {
        this.requestResolvers.set(providerName, fn);
    }

    static async resolveStartup(providerName: string, server: any): Promise<string> {
        const fn = this.startupResolvers.get(providerName);
        if (!fn) {
            throw new ComputeFunctionNotFoundError(providerName, 'startup');
        }

        try {
            const result = await fn(server);
            return result;
        } catch (error: any) {
            if (error instanceof ComputeFunctionNotFoundError) throw error;
            throw new ComputeFunctionError(providerName, error);
        }
    }

    static async resolveRequest(providerName: string, request: any): Promise<string> {
        const fn = this.requestResolvers.get(providerName);
        if (!fn) {
            throw new ComputeFunctionNotFoundError(providerName, 'request');
        }

        try {
            return await fn(request);
        } catch (error: any) {
            if (error instanceof ComputeFunctionNotFoundError) throw error;
            throw new ComputeFunctionError(providerName, error);
        }
    }
}
