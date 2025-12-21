
import { AppYamlConfig } from '../core.js';
import { ProviderNotFoundError } from '../validators.js';
import { ProviderOptions, ProviderResult } from './types.js';

export class ProviderConfig {
    private config: AppYamlConfig;

    constructor(config?: AppYamlConfig) {
        this.config = config ?? AppYamlConfig.getInstance();
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

        // Step 1: Merge global as base (deep copy)
        if (mergeGlobal) {
            const global = this.config.get('global') || {};
            result = this.deepCopy(global);
        }

        // Step 2: Deep merge provider config (provider wins)
        // Accessing protected static or using helper if possible.
        // Assuming we need to implement deepCopy/deepMerge or assume they are available.
        // Since types/validation is loose here for now, implementing simple helpers or using AppYamlConfig's if static public.
        // Checking core.ts... deepMerge is not static public usually.
        // I made a note in plan to "Reuse from core". Let's check if exportable.
        // If not easily exportable, I will re-implement simple versions here to avoid breaking core encapsulation
        // or assume I can use a util.

        // Actually, AppYamlConfig has deepMerge logic internally.
        // Let's implement local helpers for safety and independence.
        result = this.deepMerge(result, this.deepCopy(providerRaw));

        // Step 3: Apply env overwrites
        if (applyEnvOverwrites && result.overwrite_from_env) {
            const overwrites = result.overwrite_from_env as Record<string, string>;

            for (const [key, envVarName] of Object.entries(overwrites)) {
                // Only overwrite if current value is null
                if (result[key] === null) {
                    const envValue = process.env[envVarName];
                    if (envValue !== undefined) {
                        result[key] = envValue;
                        envOverwrites.push(key);
                    }
                    // If env not defined, leave as null
                }
            }

            // Remove overwrite_from_env from result (internal meta)
            delete result.overwrite_from_env;
        }

        return {
            name,
            config: result,
            envOverwrites,
            globalMerged: mergeGlobal
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
