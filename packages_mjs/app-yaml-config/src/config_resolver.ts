
import { AppYamlConfig } from './core';
import { BaseResolveOptions, BaseResult, ResolutionSource } from './domain';

// Type describing the meta key pattern
export type MetaKeyPattern =
    | { type: 'grouped'; keys: { overwrite: string; fallbacks: string } }
    | { type: 'single'; key: string }
    | { type: 'per-property'; regex: RegExp };

export abstract class ConfigResolver<TOptions extends BaseResolveOptions, TResult extends BaseResult> {
    protected config: AppYamlConfig;

    constructor(config?: AppYamlConfig) {
        this.config = config || AppYamlConfig.getInstance();
    }

    // ========== Abstract Properties ==========

    protected abstract get rootKey(): string;

    protected abstract get metaKeyPattern(): MetaKeyPattern;

    protected abstract createNotFoundError(name: string): Error;

    protected abstract buildResult(
        name: string,
        config: Record<string, any>,
        envOverwrites: string[],
        resolutionSources: Record<string, ResolutionSource>,
        options: TOptions
    ): TResult;

    // ========== Public API ==========

    public get(name: string, options?: TOptions): TResult {
        const opts = this.getDefaultOptions(options);
        const items = this.config.get(this.rootKey) || {};
        const itemRaw = items[name];

        if (!itemRaw) {
            throw this.createNotFoundError(name);
        }

        // Deep copy (naive JSON approach sufficient for simple config, or explicit copy)
        // Using JSON for now as it handles primitives well, assuming JSON-safe config
        let result = JSON.parse(JSON.stringify(itemRaw));

        // Hook for subclass preprocessing
        result = this.preProcess(result, opts);

        // Extract env meta
        const envMeta = this.extractEnvMeta(result);

        // Apply env resolution
        const { envOverwrites, resolutionSources } = this.applyEnvResolution(result, envMeta, opts);

        // Remove meta keys if configured
        if (opts.removeMetaKeys !== false) {
            this.removeMetaKeys(result);
        }

        return this.buildResult(name, result, envOverwrites, resolutionSources, opts);
    }

    public list(): string[] {
        const items = this.config.get(this.rootKey) || {};
        return Object.keys(items);
    }

    public has(name: string): boolean {
        return this.list().includes(name);
    }

    // ========== Protected Hooks ==========

    protected getDefaultOptions(options?: TOptions): TOptions {
        return (options || {}) as TOptions;
    }

    protected preProcess(config: Record<string, any>, options: TOptions): Record<string, any> {
        return config;
    }

    // ========== Shared Implementation ==========

    protected tryEnvVars(envVars: string | string[]): { value: string | null; envVar: string | null } {
        const varsList = Array.isArray(envVars) ? envVars : [envVars];

        for (const envVar of varsList) {
            const val = process.env[envVar];
            if (val !== undefined && val !== null) {
                return { value: val, envVar };
            }
        }
        return { value: null, envVar: null };
    }

    protected extractEnvMeta(config: Record<string, any>): Record<string, { primary?: string | string[]; fallbacks?: string | string[] }> {
        const pattern = this.metaKeyPattern;
        const result: Record<string, { primary?: any; fallbacks?: any }> = {};

        if (pattern.type === 'single') {
            const overwrites = config[pattern.key] || {};
            for (const [prop, envSpec] of Object.entries(overwrites)) {
                if (!result[prop]) result[prop] = {};
                result[prop].primary = envSpec;
            }
        } else if (pattern.type === 'grouped') {
            const overwrites = config[pattern.keys.overwrite] || {};
            const fallbacks = config[pattern.keys.fallbacks] || {};

            for (const [prop, envSpec] of Object.entries(overwrites)) {
                if (!result[prop]) result[prop] = {};
                result[prop].primary = envSpec;
            }

            for (const [prop, envSpec] of Object.entries(fallbacks)) {
                if (!result[prop]) result[prop] = {};
                result[prop].fallbacks = envSpec;
            }

        } else if (pattern.type === 'per-property') {
            const regex = pattern.regex;
            for (const [key, value] of Object.entries(config)) {
                const match = regex.exec(key);
                if (match) {
                    const baseProp = match[1];
                    const isFallback = match[2] === '_fallbacks';

                    if (baseProp) {
                        if (!result[baseProp]) result[baseProp] = {};
                        if (isFallback) {
                            result[baseProp].fallbacks = value;
                        } else {
                            result[baseProp].primary = value;
                        }
                    }
                }
            }
        }

        return result;
    }

    protected applyEnvResolution(
        result: Record<string, any>,
        envMeta: Record<string, { primary?: any; fallbacks?: any }>,
        options: TOptions
    ) {
        const envOverwrites: string[] = [];
        const resolutionSources: Record<string, ResolutionSource> = {};

        const applyOverwrites = options.applyEnvOverwrites !== false;

        for (const [prop, meta] of Object.entries(envMeta)) {
            // Only process if property is explicitly null/undefined/empty? 
            // Requirement: "if current value is null/None"
            if (result[prop] !== null && result[prop] !== undefined) {
                continue;
            }

            // Step 1: Try primary overwrite
            if (applyOverwrites && meta.primary) {
                const { value, envVar } = this.tryEnvVars(meta.primary);
                if (value !== null) {
                    result[prop] = value;
                    envOverwrites.push(prop);
                    resolutionSources[prop] = { source: 'env', envVar };
                    continue;
                }
            }
        }

        return { envOverwrites, resolutionSources };
    }

    protected removeMetaKeys(result: Record<string, any>): void {
        const pattern = this.metaKeyPattern;

        if (pattern.type === 'single') {
            delete result[pattern.key];
        } else if (pattern.type === 'grouped') {
            delete result[pattern.keys.overwrite];
            delete result[pattern.keys.fallbacks];
        } else if (pattern.type === 'per-property') {
            const regex = pattern.regex;
            const keysToRemove = Object.keys(result).filter(k => regex.test(k));
            keysToRemove.forEach(k => delete result[k]);
        }
    }
}
