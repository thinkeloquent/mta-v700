
import { ResolutionSource } from '../domain.js';

export { ResolutionSource };

export interface StorageOptions {
    /** Apply env overwrites (default: true) */
    applyEnvOverwrites?: boolean;
    /** Apply fallbacks from env (default: true) */
    applyFallbacks?: boolean;
    /** Remove env_*_key and env_*_key_fallbacks from result (default: true) */
    removeMetaKeys?: boolean;
}

export interface StorageResult {
    /** Storage name */
    name: string;
    /** Config dictionary with resolved values */
    config: Record<string, any>;
    /** List of keys that were overwritten/resolved from env */
    envOverwrites: string[];
    /** Details about where each key was resolved from */
    resolutionSources: Record<string, ResolutionSource>;
}
