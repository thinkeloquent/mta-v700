export interface EnvVarChainConfig {
    /** Primary env var name (from env_api_key, etc.) */
    primary?: string;
    /** Overwrite env var (from overwrite_from_env) */
    overwrite?: string | string[];
}

export interface EnvVarResolveResult {
    value: string | null;
    source: string | null;
    tried: string[];
}

export function resolveEnvVar(
    envVarName: string
): { value: string | null; source: string | null } {
    const value = process.env[envVarName];
    return {
        value: value ?? null,
        source: value !== undefined ? envVarName : null
    };
}

export function resolveEnvVarChain(
    config: EnvVarChainConfig
): EnvVarResolveResult {
    const tried: string[] = [];

    // 1. Try overwrite first (highest priority)
    if (config.overwrite) {
        const overwrites = Array.isArray(config.overwrite)
            ? config.overwrite
            : [config.overwrite];
        for (const envVar of overwrites) {
            tried.push(envVar);
            const result = resolveEnvVar(envVar);
            if (result.value !== null) return { ...result, tried };
        }
    }

    // 2. Try primary
    if (config.primary) {
        tried.push(config.primary);
        const result = resolveEnvVar(config.primary);
        if (result.value !== null) return { ...result, tried };
    }

    return { value: null, source: null, tried };
}
