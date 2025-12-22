import { AppYamlConfig } from '../core';
import { ConfigResolver, MetaKeyPattern } from '../config_resolver';
import { ProviderOptions, ProviderResult } from './types';
import { ResolutionSource } from '../domain';
import { ProviderNotFoundError } from '../validators';
import merge from 'lodash.merge';

export class ProviderConfig extends ConfigResolver<ProviderOptions, ProviderResult> {

    protected get rootKey(): string {
        return 'providers';
    }

    protected get metaKeyPattern(): MetaKeyPattern {
        return {
            type: 'grouped',
            keys: { overwrite: 'overwrite_from_env', fallbacks: 'fallbacks_from_env' }
        };
    }

    protected createNotFoundError(name: string): Error {
        return new ProviderNotFoundError(name);
    }

    // Override default options
    protected getDefaultOptions(options?: ProviderOptions): ProviderOptions {
        return {
            mergeGlobal: true,
            applyEnvOverwrites: true,
            applyFallbacks: true,
            removeMetaKeys: true,
            ...options
        };
    }

    protected preProcess(config: Record<string, any>, options: ProviderOptions): Record<string, any> {
        // 1. Merge global if requested
        if (options.mergeGlobal) {
            const globalConfig = this.config.get('global') || {};
            // Deep merge: global (base) + config (override)
            // Note: lodash.merge mutates the first argument. We should copy globalConfig first.
            // But we already made a deep copy of config in ConfigResolver before calling preProcess.
            // So we want: merge(clone(global), config).
            // Actually, best to effectively return merge({}, global, config).
            return merge({}, globalConfig, config);
        }

        // 2. Inject runtime overwrites (Provider specific feature)
        if (options.overwriteFromEnv) {
            console.debug(`[ProviderConfig] Injecting runtime overwriteFromEnv for provider:`, options.overwriteFromEnv);
            config['overwrite_from_env'] = options.overwriteFromEnv;
        }
        if (options.fallbacksFromEnv) {
            console.debug(`[ProviderConfig] Injecting runtime fallbacksFromEnv for provider:`, options.fallbacksFromEnv);
            config['fallbacks_from_env'] = options.fallbacksFromEnv;
        }

        return config;
    }

    protected buildResult(
        name: string,
        config: Record<string, any>,
        envOverwrites: string[],
        resolutionSources: Record<string, ResolutionSource>,
        options: ProviderOptions
    ): ProviderResult {
        console.debug(`[ProviderConfig] Resolved provider config for ${name}. Env overwrites:`, envOverwrites);
        return {
            name,
            config,
            envOverwrites,
            resolutionSources,
            globalMerged: options.mergeGlobal !== false
        };
    }

    // Alias methods for backward compatibility
    public listProviders(): string[] {
        return this.list();
    }

    public hasProvider(name: string): boolean {
        return this.has(name);
    }
}

export function getProvider(
    name: string,
    config?: AppYamlConfig,
    options?: ProviderOptions
): ProviderResult {
    const pc = new ProviderConfig(config);
    return pc.get(name, options);
}
