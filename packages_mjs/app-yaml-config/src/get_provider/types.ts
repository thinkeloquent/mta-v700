
export interface ProviderOptions {
    /** Apply global merge (default: true) */
    mergeGlobal?: boolean;
    /** Apply env overwrites (default: true) */
    applyEnvOverwrites?: boolean;
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
}
