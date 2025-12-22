
import { ResolutionSource } from '../domain.js';

export interface ServiceOptions {
    /** Apply env overwrites (default: true) */
    applyEnvOverwrites?: boolean;
    /** Apply fallbacks from env (default: true) */
    applyFallbacks?: boolean;
}

export interface ServiceResult {
    /** Service name */
    name: string;
    /** Service configuration */
    config: Record<string, any>;
    /** Keys that were overwritten from env */
    envOverwrites: string[];
    /** Resolution source for each resolved key */
    resolutionSources: Record<string, ResolutionSource>;
}
