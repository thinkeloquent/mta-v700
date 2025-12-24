/**
 * Credential key name constants
 */
export const USER_NAME = 'username';
export const PASS_WORD = 'password';
export const PASS_KEY = 'password';
export const SECRET_KEY = 'secretkey';

/**
 * Case transformation type constants
 */
export const UPPER_CASE = Symbol('UPPER_CASE');
export const LOWER_CASE = Symbol('LOWER_CASE');
export const SNAKE_CASE = Symbol('SNAKE_CASE');
export const KEBAB_CASE = Symbol('KEBAB_CASE');

export type CaseType = typeof UPPER_CASE | typeof LOWER_CASE | typeof SNAKE_CASE | typeof KEBAB_CASE;
