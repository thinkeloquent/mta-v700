
import { AppYamlConfig } from '../core.js';
import { ResolutionSource } from '../domain.js';
import { StorageNotFoundError } from '../validators.js';
import { StorageOptions, StorageResult } from './types.js';

export class StorageConfig {
    private config: AppYamlConfig;

    constructor(config?: AppYamlConfig) {
        this.config = config || AppYamlConfig.getInstance();
    }

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

    private extractBaseProperty(metaKey: string): string | null {
        // Pattern: env_{property}_key or env_{property}_key_fallbacks
        const match = metaKey.match(/^env_(.+)_key(_fallbacks)?$/);
        return match ? match[1] : null;
    }

    private findEnvMetaKeys(config: Record<string, any>): Map<string, { primary?: string; fallbacks?: string[] }> {
        const result = new Map();

        for (const [key, value] of Object.entries(config)) {
            if (key.startsWith('env_') && key.endsWith('_key') && !key.endsWith('_key_fallbacks')) {
                const baseProp = this.extractBaseProperty(key);
                if (baseProp) {
                    if (!result.has(baseProp)) {
                        result.set(baseProp, {});
                    }
                    result.get(baseProp).primary = value;
                }
            } else if (key.endsWith('_key_fallbacks')) {
                const baseProp = this.extractBaseProperty(key);
                if (baseProp) {
                    if (!result.has(baseProp)) {
                        result.set(baseProp, {});
                    }
                    result.get(baseProp).fallbacks = value;
                }
            }
        }

        return result;
    }

    private deepCopy(obj: any): any {
        return JSON.parse(JSON.stringify(obj));
    }

    get(name: string, options: StorageOptions = {}): StorageResult {
        const { applyEnvOverwrites = true, applyFallbacks = true, removeMetaKeys = true } = options;
        const storages = this.config.get('storage') || {};
        const storageRaw = storages[name];

        if (!storageRaw) {
            throw new StorageNotFoundError(name);
        }

        const result: Record<string, any> = this.deepCopy(storageRaw);
        const envOverwrites: string[] = [];
        const resolutionSources: Record<string, ResolutionSource> = {};

        const envMetaKeys = this.findEnvMetaKeys(result);

        for (const [baseProp, envConfig] of envMetaKeys) {
            if (result[baseProp] !== null) {
                continue;
            }

            if (applyEnvOverwrites && envConfig.primary) {
                const { value, matchedVar } = this._tryEnvVars(envConfig.primary);
                if (value !== undefined) {
                    result[baseProp] = value;
                    if (matchedVar) {
                        envOverwrites.push(baseProp);
                        resolutionSources[baseProp] = { source: 'overwrite', envVar: matchedVar };
                    }
                    continue;
                }
            }

            if (applyFallbacks && envConfig.fallbacks) {
                const { value, matchedVar } = this._tryEnvVars(envConfig.fallbacks);
                if (value !== undefined) {
                    result[baseProp] = value;
                    if (matchedVar) {
                        envOverwrites.push(baseProp);
                        resolutionSources[baseProp] = { source: 'fallback', envVar: matchedVar };
                    }
                }
            }
        }

        if (removeMetaKeys) {
            for (const key of Object.keys(result)) {
                if (key.startsWith('env_') && (key.endsWith('_key') || key.endsWith('_key_fallbacks'))) {
                    delete result[key];
                }
            }
        }

        return {
            name,
            config: result,
            envOverwrites,
            resolutionSources
        };
    }

    listStorages(): string[] {
        const storages = this.config.get('storage') || {};
        return Object.keys(storages);
    }

    hasStorage(name: string): boolean {
        return this.listStorages().includes(name);
    }
}

export function getStorage(
    name: string,
    config?: AppYamlConfig,
    options?: StorageOptions
): StorageResult {
    const sc = new StorageConfig(config);
    return sc.get(name, options);
}
