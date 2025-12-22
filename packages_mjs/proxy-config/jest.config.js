module.exports = {
    preset: "ts-jest",
    testEnvironment: "node",
    testMatch: ["**/test/**/*.test.ts"],
    collectCoverageFrom: ["src/**/*.ts"],
    coverageDirectory: "coverage",
    moduleFileExtensions: ["ts", "js", "json"],
    transform: {
        "^.+\\.ts$": "ts-jest",
    },
};
