
import { AppYamlConfig } from '../core.js';
import { ResolutionSource } from '../domain.js';
import { ServiceNotFoundError } from '../validators.js';
import { ServiceOptions, ServiceResult } from './types.js';

export class ServiceConfig {
    private config: AppYamlConfig;

    constructor(config?: AppYamlConfig) {
        this.config = config ?? AppYamlConfig.getInstance();
    }

    /**
     * Try a list of environment variables and return the first one found.
     */
    private _tryEnvVars(envVars: string | string[]): { value: string | undefined, matchedVar: string | undefined } {
        const vars = Array.isArray(envVars) ? envVars : [envVars];

        for (const varName of vars) {
            const val = process.env[varName];
            if (val !== undefined) {
                return { value: val, matchedVar: varName };
            }
        }
        return { value: undefined, matchedVar: undefined };
    }

    /**
     * Get a service configuration by name.
     * Applies env overwrites and fallbacks.
     */
    get(name: string, options: ServiceOptions = {}): ServiceResult {
        const { applyEnvOverwrites = true, applyFallbacks = true } = options;

        const services = this.config.get('services') || {};
        const serviceRaw = services[name];

        if (!serviceRaw) {
            throw new ServiceNotFoundError(name);
        }

        // Deep copy to avoid mutation
        const result: Record<string, any> = this.deepCopy(serviceRaw);
        const envOverwrites: string[] = [];
        const resolutionSources: Record<string, ResolutionSource> = {};

        // Extract meta keys
        const overwriteFromEnv = (result.overwrite_from_env || {}) as Record<string, string | string[]>;
        const fallbacksFromEnv = (result.fallbacks_from_env || {}) as Record<string, string[]>;

        // Step 1: Apply overwrite_from_env
        if (applyEnvOverwrites) {
            for (const [key, envSpec] of Object.entries(overwriteFromEnv)) {
                if (result[key] === null) {
                    const { value, matchedVar } = this._tryEnvVars(envSpec);
                    if (value !== undefined) {
                        result[key] = value;
                        if (matchedVar) {
                            envOverwrites.push(key);
                            resolutionSources[key] = { source: 'overwrite', envVar: matchedVar };
                        }
                    }
                }
            }
        }

        // Step 2: Apply fallbacks_from_env
        if (applyFallbacks) {
            for (const [key, envSpec] of Object.entries(fallbacksFromEnv)) {
                if (result[key] === null) {
                    const { value, matchedVar } = this._tryEnvVars(envSpec);
                    if (value !== undefined) {
                        result[key] = value;
                        if (matchedVar) {
                            envOverwrites.push(key);
                            resolutionSources[key] = { source: 'fallback', envVar: matchedVar };
                        }
                    }
                }
            }
        }

        // Remove meta keys from result
        delete result.overwrite_from_env;
        delete result.fallbacks_from_env;

        return {
            name,
            config: result,
            envOverwrites,
            resolutionSources
        };
    }

    // Helper to deep copy
    private deepCopy<T>(obj: T): T {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }
        if (Array.isArray(obj)) {
            return obj.map(item => this.deepCopy(item)) as unknown as T;
        }
        const copy = {} as Record<string, any>;
        for (const key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                copy[key] = this.deepCopy((obj as Record<string, any>)[key]);
            }
        }
        return copy as T;
    }

    /**
     * List all available service names.
     */
    listServices(): string[] {
        const services = this.config.get('services') || {};
        return Object.keys(services);
    }

    /**
     * Check if a service exists.
     */
    hasService(name: string): boolean {
        return this.listServices().includes(name);
    }
}

// Convenience function
export function getService(
    name: string,
    config?: AppYamlConfig,
    options?: ServiceOptions
): ServiceResult {
    const sc = new ServiceConfig(config);
    return sc.get(name, options);
}
