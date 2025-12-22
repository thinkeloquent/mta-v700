
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
            type: 'per-property',
            regex: /^env_(.+)_key(_fallbacks)?$/
        };
    }

    protected createNotFoundError(name: string): Error {
        return new StorageNotFoundError(name);
    }

    protected getDefaultOptions(options?: StorageOptions): StorageOptions {
        return {
            applyEnvOverwrites: true,
            applyFallbacks: true,
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

    /**
     * Helper exposed via public method if needed by tests, 
     * but preferably tests use public API.
     * Original implementation had `extractBaseProperty`.
     * If tests rely on it, we might need it.
     */
    public _extractBaseProperty(metaKey: string): string | null {
        const match = this.metaKeyPattern.type === 'per-property'
            ? (this.metaKeyPattern as any).regex.exec(metaKey)
            : null;
        return match ? match[1] : null;
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
