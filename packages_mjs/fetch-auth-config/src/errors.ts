export class AuthConfigError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'AuthConfigError';
    }
}

export class MissingCredentialError extends AuthConfigError {
    constructor(
        public providerName: string,
        public credentialName: string,
        public envVarsTried: string[]
    ) {
        super(
            `Missing credential '${credentialName}' for provider '${providerName}'. ` +
            `Tried env vars: ${envVarsTried.join(', ')}`
        );
        this.name = 'MissingCredentialError';
    }
}

export class InvalidAuthTypeError extends AuthConfigError {
    constructor(
        public providerName: string,
        public authType: string
    ) {
        super(`Invalid auth type '${authType}' for provider '${providerName}'`);
        this.name = 'InvalidAuthTypeError';
    }
}

export class ProviderNotFoundError extends AuthConfigError {
    constructor(message: string) {
        super(message);
        this.name = 'ProviderNotFoundError';
    }
}

export class ComputeFunctionNotFoundError extends AuthConfigError {
    constructor(
        public providerName: string,
        public resolverType: string
    ) {
        super(`No ${resolverType} compute function registered for provider '${providerName}'`);
        this.name = 'ComputeFunctionNotFoundError';
    }
}

export class ComputeFunctionError extends AuthConfigError {
    constructor(
        public providerName: string,
        public cause: Error
    ) {
        super(`Compute function failed for provider '${providerName}': ${cause.message}`);
        this.name = 'ComputeFunctionError';
    }
}
