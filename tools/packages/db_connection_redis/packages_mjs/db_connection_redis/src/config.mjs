import fs from 'fs';
import { URL } from 'url';
import { RedisConfigSchema } from './schemas.mjs';
import { DEFAULT_CONFIG } from './constants.mjs';
import { RedisConfigError } from './exceptions.mjs';

function resolve(arg, envKeys, config, configKey, defaultValue) {
    if (arg !== undefined && arg !== null) return arg;
    for (const key of envKeys) {
        if (process.env[key] !== undefined) return process.env[key];
    }
    if (config && config[configKey] !== undefined) return config[configKey];
    return defaultValue;
}

function resolveBool(arg, envKeys, config, configKey, defaultValue) {
    const val = resolve(arg, envKeys, config, configKey, defaultValue);
    if (typeof val === 'boolean') return val;
    if (typeof val === 'string') return ['true', '1', 'yes', 'on'].includes(val.toLowerCase());
    return Boolean(val);
}

function resolveInt(arg, envKeys, config, configKey, defaultValue) {
    const val = resolve(arg, envKeys, config, configKey, defaultValue);
    return val ? parseInt(val, 10) : val;
}

function resolveFloat(arg, envKeys, config, configKey, defaultValue) {
    const val = resolve(arg, envKeys, config, configKey, defaultValue);
    return val ? parseFloat(val) : val;
}

export class RedisConfig {
    constructor(options = {}) {
        this.host = resolve(options.host, ['REDIS_HOST', 'REDIS_HOSTNAME'], options, 'host', DEFAULT_CONFIG.host);
        this.port = resolveInt(options.port, ['REDIS_PORT'], options, 'port', DEFAULT_CONFIG.port);
        this.username = resolve(options.username, ['REDIS_USERNAME', 'REDIS_USER'], options, 'username', DEFAULT_CONFIG.username);
        this.password = resolve(options.password, ['REDIS_PASSWORD', 'REDIS_AUTH'], options, 'password', DEFAULT_CONFIG.password);
        this.db = resolveInt(options.db, ['REDIS_DB', 'REDIS_DATABASE'], options, 'db', DEFAULT_CONFIG.db);

        this.useTls = resolveBool(options.useTls, ['REDIS_SSL', 'REDIS_USE_TLS', 'REDIS_TLS'], options, 'useTls', DEFAULT_CONFIG.useTls);
        this.sslCertReqs = resolve(options.sslCertReqs, ['REDIS_SSL_CERT_REQS'], options, 'sslCertReqs', DEFAULT_CONFIG.sslCertReqs);

        let caCerts = resolve(options.sslCaCerts, ['REDIS_SSL_CA_CERTS'], options, 'sslCaCerts', DEFAULT_CONFIG.sslCaCerts);
        if (caCerts && fs.existsSync(caCerts)) {
            try {
                caCerts = fs.readFileSync(caCerts, 'utf8');
            } catch (e) {
                // ignore
            }
        }
        this.sslCaCerts = caCerts;

        this.sslCheckHostname = resolveBool(options.sslCheckHostname, ['REDIS_SSL_CHECK_HOSTNAME'], options, 'sslCheckHostname', DEFAULT_CONFIG.sslCheckHostname);

        this.socketTimeout = resolveFloat(options.socketTimeout, ['REDIS_SOCKET_TIMEOUT'], options, 'socketTimeout', DEFAULT_CONFIG.socketTimeout);
        this.socketConnectTimeout = resolveFloat(options.socketConnectTimeout, [], options, 'socketConnectTimeout', DEFAULT_CONFIG.socketConnectTimeout);
        this.retryOnTimeout = resolveBool(options.retryOnTimeout, [], options, 'retryOnTimeout', DEFAULT_CONFIG.retryOnTimeout);

        this.maxConnections = resolveInt(options.maxConnections, ['REDIS_MAX_CONNECTIONS'], options, 'maxConnections', DEFAULT_CONFIG.maxConnections);
        this.minConnections = resolveInt(options.minConnections, ['REDIS_MIN_CONNECTIONS'], options, 'minConnections', DEFAULT_CONFIG.minConnections);
        this.healthCheckInterval = resolveFloat(options.healthCheckInterval, [], options, 'healthCheckInterval', DEFAULT_CONFIG.healthCheckInterval);

        // URL override
        if (process.env.REDIS_URL) {
            this._parseUrl(process.env.REDIS_URL);
        }

        // Vendor detection
        this._detectVendor();

        this.validate();
    }

    _parseUrl(urlString) {
        try {
            const url = new URL(urlString);
            if (url.protocol === 'rediss:') this.useTls = true;
            this.host = url.hostname || this.host;
            this.port = url.port ? parseInt(url.port) : this.port;
            this.username = url.username || this.username;
            this.password = url.password || this.password;
            if (url.pathname && url.pathname.length > 1) {
                this.db = parseInt(url.pathname.substring(1));
            }
        } catch (e) {
            // ignore invalid url in env?
        }
    }

    _detectVendor() {
        if (this.host.includes('cache.amazonaws.com') ||
            this.host.includes('redis-cloud.com') ||
            this.host.includes('upstash.io') ||
            (this.host.includes('db.ondigitalocean.com') && this.port === 25061)) {

            if (!this.useTls) {
                this.useTls = true;
            }
        }
    }

    validate() {
        try {
            RedisConfigSchema.parse(this);
        } catch (error) {
            throw new RedisConfigError(`Invalid configuration: ${error.message}`);
        }
    }

    getTlsConfig() {
        if (!this.useTls) return undefined;

        const ssl = {};
        // Similar to PostgreSQL ssl_mode:
        // - 'none' or 'required': use TLS but don't verify certificate
        // - 'verify-ca' or 'verify-full': verify certificate
        if (this.sslCertReqs === 'verify-ca' || this.sslCertReqs === 'verify-full') {
            ssl.rejectUnauthorized = true;
        } else {
            // 'none', 'required', or other - don't verify cert (just encrypt)
            ssl.rejectUnauthorized = false;
        }

        if (this.sslCaCerts) {
            ssl.ca = [this.sslCaCerts];
        }

        if (!this.sslCheckHostname || this.sslCertReqs !== 'verify-full') {
            ssl.checkServerIdentity = () => undefined;
        }

        return ssl;
    }
}
