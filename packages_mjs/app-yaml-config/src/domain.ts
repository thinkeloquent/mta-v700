/**
 * Data models for AppYamlConfig.
 */

import { AppYamlConfig } from './core';

export interface LoadResult {
    filesLoaded: string[];
    errors: Array<{ file: string; error: string }>;
    appEnv: string | null;
    mergeOrder: string[];
}

export type ComputedDefinition = (config: AppYamlConfig) => any;
export type ComputedRegistry = Record<string, ComputedDefinition>;

export interface InitOptions {
    files: string[];
    configDir?: string;
    appEnv?: string;
    computedDefinitions?: ComputedRegistry;
}

export interface ResolutionSource {
    /** Source type: yaml, env */
    source: 'yaml' | 'env';
    /** Environment variable name that provided the value (if applicable) */
    envVar: string | null;
}

export interface BaseResolveOptions {
    applyEnvOverwrites?: boolean;
    removeMetaKeys?: boolean;
}

export interface BaseResult {
    name: string;
    config: Record<string, any>;
    envOverwrites: string[];
    resolutionSources: Record<string, ResolutionSource>;
}
