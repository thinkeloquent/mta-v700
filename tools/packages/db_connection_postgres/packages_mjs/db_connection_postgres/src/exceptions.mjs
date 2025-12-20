export class DatabaseConfigError extends Error {
    constructor(message) {
        super(message);
        this.name = 'DatabaseConfigError';
    }
}

export class DatabaseConnectionError extends Error {
    constructor(message, originalError = null) {
        super(message);
        this.name = 'DatabaseConnectionError';
        this.originalError = originalError;
    }
}

export class DatabaseImportError extends Error {
    constructor(message) {
        super(message);
        this.name = 'DatabaseImportError';
    }
}
