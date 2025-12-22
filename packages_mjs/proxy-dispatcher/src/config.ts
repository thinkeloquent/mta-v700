/**
 * Environment detection functions.
 */

export function getAppEnv(defaultValue = "dev"): string {
    return process.env.APP_ENV || defaultValue;
}

export function isDev(): boolean {
    return getAppEnv().toLowerCase() === "dev";
}

export function isProd(): boolean {
    return getAppEnv().toLowerCase() === "prod";
}

export function isSslVerifyDisabledByEnv(): boolean {
    if (process.env.NODE_TLS_REJECT_UNAUTHORIZED === "0") {
        return true;
    }
    if (process.env.SSL_CERT_VERIFY === "0") {
        return true;
    }
    return false;
}
