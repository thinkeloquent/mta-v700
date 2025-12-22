/**
 * Vault File Logger
 * Provides standardized logging with multiple levels.
 */

export type LogLevel = 'silent' | 'error' | 'warn' | 'info' | 'debug' | 'trace';

export interface VaultFileLogger {
    error(message: string, ...args: any[]): void;
    warn(message: string, ...args: any[]): void;
    info(message: string, ...args: any[]): void;
    debug(message: string, ...args: any[]): void;
    trace(message: string, ...args: any[]): void;
}

const LOG_LEVELS: Record<LogLevel, number> = {
    silent: 0,
    error: 1,
    warn: 2,
    info: 3,
    debug: 4,
    trace: 5
};

let currentLevel: LogLevel = 'info';

// Detect initial log level from env
if (typeof process !== 'undefined' && process.env.VAULT_FILE_LOG_LEVEL) {
    const envLevel = process.env.VAULT_FILE_LOG_LEVEL.toLowerCase() as LogLevel;
    if (Object.keys(LOG_LEVELS).includes(envLevel)) {
        currentLevel = envLevel;
    }
}

const PREFIX = process.env.VAULT_FILE_LOG_PREFIX || '[vault-file]';

export function getLogLevel(): LogLevel {
    return currentLevel;
}

export function setLogLevel(level: LogLevel): void {
    if (Object.keys(LOG_LEVELS).includes(level)) {
        currentLevel = level;
    }
}

class ConsoleLogger implements VaultFileLogger {
    private shouldLog(level: LogLevel): boolean {
        return LOG_LEVELS[level] <= LOG_LEVELS[currentLevel];
    }

    private format(message: string): string {
        return `${PREFIX} ${message}`;
    }

    error(message: string, ...args: any[]): void {
        if (this.shouldLog('error')) {
            console.error(this.format(message), ...args);
        }
    }

    warn(message: string, ...args: any[]): void {
        if (this.shouldLog('warn')) {
            console.warn(this.format(message), ...args);
        }
    }

    info(message: string, ...args: any[]): void {
        if (this.shouldLog('info')) {
            console.info(this.format(message), ...args);
        }
    }

    debug(message: string, ...args: any[]): void {
        if (this.shouldLog('debug')) {
            // Using console.error/warn for debug info often helps visibility in some environments
            // but standard is console.debug or log
            console.debug(this.format(message), ...args);
        }
    }

    trace(message: string, ...args: any[]): void {
        if (this.shouldLog('trace')) {
            console.log(this.format(message), ...args);
        }
    }
}

const loggerInstance = new ConsoleLogger();

export function getLogger(): VaultFileLogger {
    return loggerInstance;
}
