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
