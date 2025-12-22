
import { BaseResolveOptions, BaseResult } from '../domain';

export interface ProviderOptions extends BaseResolveOptions {
    mergeGlobal?: boolean;
    /** Runtime override for env overwrites */
    overwriteFromEnv?: Record<string, string | string[]>;
    /** Runtime override for fallbacks */
    fallbacksFromEnv?: Record<string, string | string[]>;
}

export interface ProviderResult extends BaseResult {
    globalMerged: boolean;
}
