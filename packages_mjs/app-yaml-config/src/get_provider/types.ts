
export interface ResolutionSource {
    source: 'yaml' | 'overwrite' | 'fallback';
    envVar: string | null;
}

export interface ProviderOptions {
    /** Apply global merge (default: true) */
    mergeGlobal?: boolean;
    /** Apply env overwrites (default: true) */
    applyEnvOverwrites?: boolean;
    /** Runtime env overwrites */
    overwriteFromEnv?: Record<string, string | string[]>;
    /** Runtime env fallbacks */
    fallbacksFromEnv?: Record<string, string[]>;
}

export interface ProviderResult {
    /** Provider name */
    name: string;
    /** Merged configuration */
    config: Record<string, any>;
    /** Keys that were overwritten from env */
    envOverwrites: string[];
    /** Whether global was merged */
    globalMerged: boolean;
    /** Metadata about resolution sources */
    resolutionSources: Record<string, ResolutionSource>;
}
