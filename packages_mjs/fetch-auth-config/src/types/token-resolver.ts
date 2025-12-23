export enum TokenResolverType {
    /** Resolve at module import time */
    STATIC = 'static',
    /** Resolve at application startup */
    STARTUP = 'startup',
    /** Resolve per HTTP request */
    REQUEST = 'request'
}
