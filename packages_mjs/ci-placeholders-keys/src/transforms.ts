import { UPPER_CASE, LOWER_CASE, SNAKE_CASE, KEBAB_CASE, type CaseType } from './constants.js';

/**
 * Convert string to uppercase, removing special characters (keeps alphanumeric and $)
 * @example upperCase('$catDog') => '$CAT DOG'
 */
export function upperCase(input: string): string {
    return input
        .replace(/[^a-zA-Z0-9$\s]/g, ' ')
        .replace(/([a-z])([A-Z])/g, '$1 $2')
        .toUpperCase()
        .replace(/\s+/g, ' ')
        .trim();
}

/**
 * Convert string to lowercase, removing special characters (keeps alphanumeric and $)
 * @example lowerCase('$catDog') => '$cat dog'
 */
export function lowerCase(input: string): string {
    return input
        .replace(/[^a-zA-Z0-9$\s]/g, ' ')
        .replace(/([a-z])([A-Z])/g, '$1 $2')
        .toLowerCase()
        .replace(/\s+/g, ' ')
        .trim();
}

/**
 * Normalize string to valid key name format
 * - Replaces special characters with underscore (or hyphen for KEBAB_CASE)
 * - Removes duplicate separators
 * - Applies case transformation
 *
 * @example getKeyName('Cat-Dog', LOWER_CASE) => 'cat_dog'
 * @example getKeyName('Cat--Dog', LOWER_CASE) => 'cat_dog'
 * @example getKeyName('API Key', UPPER_CASE) => 'API_KEY'
 */
export function getKeyName(input: string, caseType: CaseType = SNAKE_CASE): string {
    // Trim whitespace
    let result = input.trim();

    // Insert separator before uppercase letters in camelCase
    result = result.replace(/([a-z])([A-Z])/g, '$1_$2');

    // Replace special characters with underscore
    result = result.replace(/[^a-zA-Z0-9_]/g, '_');

    // Collapse multiple underscores
    result = result.replace(/_+/g, '_');

    // Remove leading/trailing underscores
    result = result.replace(/^_+|_+$/g, '');

    // Apply case transformation
    switch (caseType) {
        case UPPER_CASE:
            result = result.toUpperCase();
            break;
        case LOWER_CASE:
        case SNAKE_CASE:
            result = result.toLowerCase();
            break;
        case KEBAB_CASE:
            result = result.toLowerCase().replace(/_/g, '-');
            break;
    }

    return result;
}
