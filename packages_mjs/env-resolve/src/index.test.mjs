import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import { resolve, resolveBool, resolveInt, resolveFloat } from './index.mjs';

describe('env-resolve', () => {
    const originalEnv = process.env;

    beforeEach(() => {
        jest.resetModules();
        process.env = { ...originalEnv };
    });

    afterAll(() => {
        process.env = originalEnv;
    });

    describe('resolve', () => {
        it('should return argument if provided', () => {
            expect(resolve('arg', ['ENV'], {}, 'conf', 'default')).toBe('arg');
        });

        it('should return env var if argument missing', () => {
            process.env.TEST_ENV = 'env_val';
            expect(resolve(undefined, ['TEST_ENV'], {}, 'conf', 'default')).toBe('env_val');
        });

        it('should respect env var priority', () => {
            process.env.TEST_ENV_1 = 'val1';
            process.env.TEST_ENV_2 = 'val2';
            expect(resolve(undefined, ['TEST_ENV_1', 'TEST_ENV_2'], {}, 'conf', 'default')).toBe('val1');
        });

        it('should return config value if env var missing', () => {
            expect(resolve(undefined, ['MISSING'], { conf: 'conf_val' }, 'conf', 'default')).toBe('conf_val');
        });

        it('should return default if nothing else matches', () => {
            expect(resolve(undefined, ['MISSING'], {}, 'conf', 'default')).toBe('default');
        });
    });

    describe('resolveBool', () => {
        it('should correctly parsing boolean strings', () => {
            expect(resolveBool('true', [], {}, '', false)).toBe(true);
            expect(resolveBool('1', [], {}, '', false)).toBe(true);
            expect(resolveBool('yes', [], {}, '', false)).toBe(true);
            expect(resolveBool('on', [], {}, '', false)).toBe(true);

            expect(resolveBool('false', [], {}, '', true)).toBe(false);
            expect(resolveBool('0', [], {}, '', true)).toBe(false);
            expect(resolveBool('off', [], {}, '', true)).toBe(false);
        });
    });

    describe('resolveInt', () => {
        it('should parse integers', () => {
            expect(resolveInt('123', [], {}, '', 0)).toBe(123);
        });

        it('should return default on NaN', () => {
            expect(resolveInt('abc', [], {}, '', 10)).toBe(10);
        });
    });

    describe('resolveFloat', () => {
        it('should parse floats', () => {
            expect(resolveFloat('123.45', [], {}, '', 0)).toBe(123.45);
        });
    });
});
