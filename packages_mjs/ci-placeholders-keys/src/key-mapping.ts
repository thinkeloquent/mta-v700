import { randomUUID } from 'crypto';

/**
 * Pre-defined UUID keys for consistent key mapping across applications
 */
export const Key01 = randomUUID();
export const Key02 = randomUUID();
export const Key03 = randomUUID();
export const Key04 = randomUUID();

/**
 * Key mapping interface - maps UUID keys to string values
 */
export interface KeyMapping {
    [key: string]: string;
}

/**
 * Create a key mapping from entries
 * @example createKeyMapping([[Key01, 'user_name'], [Key02, 'password']])
 */
export function createKeyMapping(entries: [string, string][]): KeyMapping {
    const mapping: KeyMapping = {};
    for (const [key, value] of entries) {
        mapping[key] = value;
    }
    return mapping;
}

/**
 * Get value from key mapping (returns undefined if key not found)
 * Similar to lodash .get() behavior
 */
export function getKeyValue(mapping: KeyMapping, keyId: string): string | undefined {
    return mapping[keyId];
}

/**
 * Get value from key mapping with fallback
 * @param mapping The key mapping object
 * @param keyId The key ID to look up
 * @param fallback Default value if key not found (defaults to empty string)
 */
export function getMappedKey(mapping: KeyMapping, keyId: string, fallback: string = ''): string {
    return mapping[keyId] ?? fallback;
}

/**
 * Check if a key exists in the mapping
 */
export function hasKey(mapping: KeyMapping, keyId: string): boolean {
    return keyId in mapping;
}

/**
 * Get all keys from a mapping
 */
export function getKeys(mapping: KeyMapping): string[] {
    return Object.keys(mapping);
}

/**
 * Get all values from a mapping
 */
export function getValues(mapping: KeyMapping): string[] {
    return Object.values(mapping);
}
