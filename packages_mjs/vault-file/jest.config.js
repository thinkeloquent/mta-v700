/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
    preset: 'ts-jest',
    testEnvironment: 'node',
    moduleIsomorphic: {
        '/src/domain.js': '<rootDir>/src/domain.ts',
        '/src/validators.js': '<rootDir>/src/validators.ts',
        '/src/core.js': '<rootDir>/src/core.ts',
        '/src/env-store.js': '<rootDir>/src/env-store.ts',
    },
    moduleNameMapper: {
        '^(\\.{1,2}/.*)\\.js$': '$1',
    },
};
