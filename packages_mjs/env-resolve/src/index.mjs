/**
 * Resolve configuration value from multiple sources.
 * Priority:
 * 1. Direct argument (if not undefined/null)
 * 2. Environment variables (first match)
 * 3. Config object property
 * 4. Default value
 * 
 * @param arg - Direct argument value (highest priority)
 * @param envKeys - Array of environment variable names to check
 * @param config - Configuration object (optional)
 * @param configKey - Key to check in config object
 * @param defaultValue - Fallback value
 * @returns Resolved value
 */
export function resolve(arg, envKeys, config, configKey, defaultValue) {
    // 1. Argument
    if (arg !== undefined && arg !== null) {
        return arg;
    }

    // 2. Env Vars
    if (envKeys && Array.isArray(envKeys)) {
        for (const key of envKeys) {
            if (process.env[key] !== undefined) {
                return process.env[key];
            }
        }
    } else if (typeof envKeys === 'string') {
        if (process.env[envKeys] !== undefined) {
            return process.env[envKeys];
        }
    }

    // 3. Config object
    if (config && configKey && config[configKey] !== undefined) {
        return config[configKey];
    }

    // 4. Default
    return defaultValue;
}

/**
 * Resolve configuration to a boolean.
 * Handles string variations: 'true', '1', 'yes', 'on' -> true
 */
export function resolveBool(arg, envKeys, config, configKey, defaultValue) {
    const val = resolve(arg, envKeys, config, configKey, defaultValue);

    if (typeof val === 'boolean') return val;

    if (typeof val === 'string') {
        return ['true', '1', 'yes', 'on'].includes(val.toLowerCase());
    }

    if (typeof val === 'number') {
        return Boolean(val);
    }

    return Boolean(val);
}

/**
 * Resolve configuration to an integer.
 */
export function resolveInt(arg, envKeys, config, configKey, defaultValue) {
    const val = resolve(arg, envKeys, config, configKey, defaultValue);
    const parsed = parseInt(val, 10);
    if (isNaN(parsed)) return defaultValue;
    return parsed;
}

/**
 * Resolve configuration to a float.
 */
export function resolveFloat(arg, envKeys, config, configKey, defaultValue) {
    const val = resolve(arg, envKeys, config, configKey, defaultValue);
    const parsed = parseFloat(val);
    if (isNaN(parsed)) return defaultValue;
    return parsed;
}
