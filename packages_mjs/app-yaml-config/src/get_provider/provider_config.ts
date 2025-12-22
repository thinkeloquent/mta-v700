
import { AppYamlConfig } from '../core.js';
import { ProviderNotFoundError } from '../validators.js';
import { ProviderOptions, ProviderResult, ResolutionSource } from './types.js';

export class ProviderConfig {
    private config: AppYamlConfig;

    constructor(config?: AppYamlConfig) {
        this.config = config ?? AppYamlConfig.getInstance();
    }

    /**
     * Try a list of environment variables and return the first one found.
     */
    private _tryEnvVars(envVars: string[]): { value: string | undefined, matchedVar: string | undefined } {
        for (const varName of envVars) {
            const val = process.env[varName];
            if (val !== undefined) {
                return { value: val, matchedVar: varName };
            }
        }
        return { value: undefined, matchedVar: undefined };
    }

    /**
     * Get a provider configuration by name.
     * Merges global config as base, applies env overwrites.
     */
    get(name: string, options: ProviderOptions = {}): ProviderResult {
        const { mergeGlobal = true, applyEnvOverwrites = true } = options;

        const providers = this.config.get('providers') || {};
        const providerRaw = providers[name];

        if (!providerRaw) {
            throw new ProviderNotFoundError(name);
        }

        let result: Record<string, any> = {};
        const envOverwrites: string[] = [];
        const resolutionSources: Record<string, ResolutionSource> = {};

        // Step 1: Merge global as base (deep copy)
        if (mergeGlobal) {
            const global = this.config.get('global') || {};
            result = this.deepCopy(global);
        }

        // Step 2: Deep merge provider config (provider wins)
        result = this.deepMerge(result, this.deepCopy(providerRaw));

        // Step 3: Apply env overwrites and fallbacks
        if (applyEnvOverwrites) {
            const yamlOverwrite = (result.overwrite_from_env || {}) as Record<string, string | string[]>;
            const yamlFallbacks = (result.fallbacks_from_env || {}) as Record<string, string[]>;

            // Runtime options override YAML options
            const overwriteMap = options.overwriteFromEnv !== undefined ? options.overwriteFromEnv : yamlOverwrite;
            const fallbacksMap = options.fallbacksFromEnv !== undefined ? options.fallbacksFromEnv : yamlFallbacks;

            // 3a. Process Overwrites
            if (overwriteMap) {
                for (const [key, envSpec] of Object.entries(overwriteMap)) {
                    // Only overwrite if current value is null
                    if (result[key] === null) {
                        const envVars = Array.isArray(envSpec) ? envSpec : [envSpec];
                        const { value, matchedVar } = this._tryEnvVars(envVars as string[]); // Cast as safely string[]

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

            // 3b. Process Fallbacks
            if (fallbacksMap) {
                for (const [key, envSpec] of Object.entries(fallbacksMap)) {
                    // Only fallback if value is still null
                    if (result[key] === null) {
                        const envVars = Array.isArray(envSpec) ? envSpec : [envSpec];
                        const { value, matchedVar } = this._tryEnvVars(envVars as string[]);

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

            // Cleanup metadata
            delete result.overwrite_from_env;
            delete result.fallbacks_from_env;
        }

        return {
            name,
            config: result,
            envOverwrites,
            globalMerged: mergeGlobal,
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

    // Helper to deep merge
    private deepMerge(target: Record<string, any>, source: Record<string, any>): Record<string, any> {
        const output = { ...target };
        if (this.isObject(target) && this.isObject(source)) {
            Object.keys(source).forEach(key => {
                if (this.isObject(source[key])) {
                    if (!(key in target)) {
                        Object.assign(output, { [key]: source[key] });
                    } else {
                        output[key] = this.deepMerge(target[key], source[key]);
                    }
                } else {
                    Object.assign(output, { [key]: source[key] });
                }
            });
        }
        return output;
    }

    private isObject(item: any): boolean {
        return (item && typeof item === 'object' && !Array.isArray(item));
    }

    /**
     * List all available provider names.
     */
    listProviders(): string[] {
        const providers = this.config.get('providers') || {};
        return Object.keys(providers);
    }

    /**
     * Check if a provider exists.
     */
    hasProvider(name: string): boolean {
        return this.listProviders().includes(name);
    }
}

// Convenience function
export function getProvider(
    name: string,
    config?: AppYamlConfig,
    options?: ProviderOptions
): ProviderResult {
    const pc = new ProviderConfig(config);
    return pc.get(name, options);
}
