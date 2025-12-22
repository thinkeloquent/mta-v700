
import { AppYamlConfig } from '../core';
import { ConfigResolver, MetaKeyPattern } from '../config_resolver';
import { ServiceOptions, ServiceResult } from './types';
import { ResolutionSource } from '../domain';
import { ServiceNotFoundError } from '../validators';

// Or check if domain re-exports. Original validators.ts had the errors.

export class ServiceConfig extends ConfigResolver<ServiceOptions, ServiceResult> {

    protected get rootKey(): string {
        return 'services';
    }

    protected get metaKeyPattern(): MetaKeyPattern {
        return {
            type: 'grouped',
            keys: { overwrite: 'overwrite_from_env', fallbacks: 'fallbacks_from_env' }
        };
    }

    protected createNotFoundError(name: string): Error {
        return new ServiceNotFoundError(name);
    }

    protected getDefaultOptions(options?: ServiceOptions): ServiceOptions {
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
        options: ServiceOptions
    ): ServiceResult {
        // Log config keys to avoid dumping secrets potentially, just to show successful resolution
        console.debug(`[ServiceConfig] Resolved service config for ${name}. Config keys:`, Object.keys(config));
        return {
            name,
            config,
            envOverwrites,
            resolutionSources
        };
    }

    // Aliases
    public listServices(): string[] {
        return this.list();
    }

    public hasService(name: string): boolean {
        return this.has(name);
    }
}

export function getService(
    name: string,
    config?: AppYamlConfig,
    options?: ServiceOptions
): ServiceResult {
    const sc = new ServiceConfig(config);
    return sc.get(name, options);
}
