/**
 * Validation schemas and custom errors.
 */

export class ValidationError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'ValidationError';
    }
}

export class ConfigNotInitializedError extends Error {
    constructor(message: string = "AppYamlConfig not initialized. Call initialize() first.") {
        super(message);
        this.name = 'ConfigNotInitializedError';
    }
}

export class ConfigAlreadyInitializedError extends Error {
    constructor(message: string = "AppYamlConfig already initialized.") {
        super(message);
        this.name = 'ConfigAlreadyInitializedError';
    }
}

export class ComputedKeyNotFoundError extends Error {
    constructor(key: string) {
        super(`Computed value '${key}' not defined`);
        this.name = 'ComputedKeyNotFoundError';
    }
}

export class CircularDependencyError extends Error {
    constructor(key: string, stack: string[]) {
        super(`Circular dependency detected for '${key}': ${stack.join(' -> ')}`);
        this.name = 'CircularDependencyError';
    }
}
