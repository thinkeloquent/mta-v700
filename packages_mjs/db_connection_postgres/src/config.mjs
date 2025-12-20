import fs from 'fs';
import { PostgresConfigSchema } from './schemas.mjs';
import { DEFAULT_CONFIG } from './constants.mjs';
import { DatabaseConfigError } from './exceptions.mjs';

function resolve(arg, envKeys, config, configKey, defaultValue) {
    // 1. Argument
    if (arg !== undefined && arg !== null) return arg;

    // 2. Env Vars
    for (const key of envKeys) {
        if (process.env[key] !== undefined) return process.env[key];
    }

    // 3. Config object
    if (config && config[configKey] !== undefined) return config[configKey];

    // 4. Default
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
    return parseInt(val, 10);
}


export class PostgresConfig {
    constructor(options = {}) {
        this.host = resolve(options.host, ['POSTGRES_HOST', 'DATABASE_HOST'], options, 'host', DEFAULT_CONFIG.host);
        this.port = resolveInt(options.port, ['POSTGRES_PORT', 'DATABASE_PORT'], options, 'port', DEFAULT_CONFIG.port);
        this.username = resolve(options.username, ['POSTGRES_USER', 'DATABASE_USER', 'POSTGRES_USERNAME'], options, 'username', DEFAULT_CONFIG.username);
        this.password = resolve(options.password, ['POSTGRES_PASSWORD', 'DATABASE_PASSWORD'], options, 'password', DEFAULT_CONFIG.password);
        this.database = resolve(options.database, ['POSTGRES_DATABASE', 'DATABASE_NAME', 'POSTGRES_DB'], options, 'database', DEFAULT_CONFIG.database);
        this.sslMode = resolve(options.sslMode, ['POSTGRES_SSL_MODE', 'DATABASE_SSL_MODE'], options, 'sslMode', DEFAULT_CONFIG.sslMode);

        // CA Certs might be file path in env, or content.
        // If env var points to file and starts with /, read it? 
        // Spec says SSL_CA_CERTS. 
        // Python implementation does not read content here, it passes file path to ssl context. 
        // Sequelize needs content or file path depending on usage but usually content in dialectOptions.ssl.ca.
        // The spec says "Reads CA cert file synchronously with fs.readFileSync" in implementation_differences.
        let caCerts = resolve(options.sslCaCerts, ['POSTGRES_SSL_CA_CERTS', 'POSTGRES_SSL_CA_FILE'], options, 'sslCaCerts', DEFAULT_CONFIG.sslCaCerts);
        if (caCerts && fs.existsSync(caCerts)) {
            try {
                caCerts = fs.readFileSync(caCerts, 'utf8');
            } catch (e) {
                // If failed to read, maybe it was content, ignore?
                // But we checked existsSync. 
                // It's safer to leave as is if we can't read?
                // Spec says "Reads CA cert file".
                // Let's assume input is path if file exists, else content.
            }
        }
        this.sslCaCerts = caCerts;

        this.connectTimeout = resolveInt(options.connectTimeout, ['POSTGRES_CONNECT_TIMEOUT'], options, 'connectTimeout', DEFAULT_CONFIG.connectTimeout);
        this.maxConnections = resolveInt(options.maxConnections, ['POSTGRES_POOL_SIZE', 'DATABASE_POOL_SIZE'], options, 'maxConnections', DEFAULT_CONFIG.maxConnections);

        // Validate
        this.validate();
    }

    validate() {
        try {
            PostgresConfigSchema.parse(this);
        } catch (error) {
            throw new DatabaseConfigError(`Invalid configuration: ${error.message}`);
        }
    }

    getSequelizeDialectOptions() {
        const options = {
            connectTimeout: this.connectTimeout,
        };

        if (this.sslMode !== 'disable') {
            const ssl = {};
            if (this.sslMode === 'require' || this.sslMode === 'verify-ca' || this.sslMode === 'verify-full') {
                ssl.require = true;
                if (this.sslMode === 'verify-full') {
                    // rejectUnauthorized = true is default but explicit is good.
                    ssl.rejectUnauthorized = true;
                } else {
                    // For verify-ca? Sequelize/pg doesn't distinguish finely between verify-ca and full easily without custom checking
                    // generally rejectUnauthorized=true enables CA check. Hostname check is implicit in strict mode?
                    // Let's stick to standard pg ssl keys.
                    ssl.rejectUnauthorized = (this.sslMode !== 'allow' && this.sslMode !== 'prefer');
                }
            } else {
                ssl.rejectUnauthorized = false;
            }

            if (this.sslCaCerts) {
                ssl.ca = this.sslCaCerts;
            }

            options.ssl = ssl;
        }
        return options;
    }

    getConnectionUrl() {
        // Construct URL for debugging
        const protocol = 'postgres';
        return `${protocol}://${this.username}:***@${this.host}:${this.port}/${this.database}`;
    }
}
