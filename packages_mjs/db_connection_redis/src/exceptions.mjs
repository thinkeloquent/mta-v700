export class RedisConfigError extends Error {
    constructor(message) {
        super(message);
        this.name = 'RedisConfigError';
    }
}

export class RedisConnectionError extends Error {
    constructor(message, originalError = null) {
        super(message);
        this.name = 'RedisConnectionError';
        this.originalError = originalError;
    }
}

export class RedisImportError extends Error {
    constructor(message) {
        super(message);
        this.name = 'RedisImportError';
    }
}
