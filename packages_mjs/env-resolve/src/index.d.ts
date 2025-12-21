/**
 * Resolve configuration value from multiple sources.
 * @param arg - Direct argument value (highest priority)
 * @param envKeys - Array of environment variable names to check or single string
 * @param config - Configuration object (optional)
 * @param configKey - Key to check in config object
 * @param defaultValue - Fallback value
 * @returns Resolved value
 */
export function resolve(
    arg: any,
    envKeys: string[] | string | undefined | null,
    config: Record<string, any> | undefined | null,
    configKey: string | undefined | null,
    defaultValue: any
): any;

/**
 * Resolve configuration to a boolean.
 */
export function resolveBool(
    arg: any,
    envKeys: string[] | string | undefined | null,
    config: Record<string, any> | undefined | null,
    configKey: string | undefined | null,
    defaultValue: boolean
): boolean;

/**
 * Resolve configuration to an integer.
 */
export function resolveInt(
    arg: any,
    envKeys: string[] | string | undefined | null,
    config: Record<string, any> | undefined | null,
    configKey: string | undefined | null,
    defaultValue: number
): number;

/**
 * Resolve configuration to a float.
 */
export function resolveFloat(
    arg: any,
    envKeys: string[] | string | undefined | null,
    config: Record<string, any> | undefined | null,
    configKey: string | undefined | null,
    defaultValue: number
): number;
