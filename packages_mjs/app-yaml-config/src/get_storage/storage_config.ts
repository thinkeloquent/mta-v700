
import { AppYamlConfig } from '../core';
import { ConfigResolver, MetaKeyPattern } from '../config_resolver';
import { StorageOptions, StorageResult } from './types';
import { ResolutionSource } from '../domain';
import { StorageNotFoundError } from '../validators';

export class StorageConfig extends ConfigResolver<StorageOptions, StorageResult> {

    protected get rootKey(): string {
        return 'storage';
    }

    protected get metaKeyPattern(): MetaKeyPattern {
        return {
            type: 'single',
            key: 'overwrite_from_env'
        };
    }

    protected createNotFoundError(name: string): Error {
        return new StorageNotFoundError(name);
    }

    protected getDefaultOptions(options?: StorageOptions): StorageOptions {
        return {
            applyEnvOverwrites: true,
            removeMetaKeys: true,
            ...options
        };
    }

    protected buildResult(
        name: string,
        config: Record<string, any>,
        envOverwrites: string[],
        resolutionSources: Record<string, ResolutionSource>,
        options: StorageOptions
    ): StorageResult {
        console.debug(`[StorageConfig] Resolved storage config for ${name}. Env overwrites:`, envOverwrites);
        return {
            name,
            config,
            envOverwrites,
            resolutionSources
        };
    }

    // Aliases
    public listStorages(): string[] {
        return this.list();
    }

    public hasStorage(name: string): boolean {
        return this.has(name);
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
