export default {
    preset: 'ts-jest/presets/default-esm',
    testEnvironment: 'node',
    testMatch: ['**/test/**/*.test.ts'],
    extensionsToTreatAsEsm: ['.ts'],
    moduleNameMapper: {
        '^(\\.{1,2}/.*)\\.js$': '$1',
        '^@internal/fetch-auth-config$': '<rootDir>/../fetch-auth-config/src/index.ts',
        '^@internal/fetch-auth-encoding$': '<rootDir>/../fetch-auth-encoding/src/index.ts',
        '^@internal/app-yaml-config$': '<rootDir>/../app-yaml-config/src/index.ts'
    },
    transform: {
        '^.+\\.tsx?$': [
            'ts-jest',
            {
                useESM: true,
            },
        ],
    },
};
