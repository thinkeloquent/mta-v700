import fs from 'fs';
import { PostgresConfigSchema } from './schemas.mjs';
import {
    DEFAULT_CONFIG,
    ENV_POSTGRES_HOST,
    ENV_POSTGRES_PORT,
    ENV_POSTGRES_USER,
    ENV_POSTGRES_PASSWORD,
    ENV_POSTGRES_DB,
    ENV_POSTGRES_SCHEMA,
    ENV_POSTGRES_SSL_MODE,
    ENV_POSTGRES_SSL_CA_FILE,
    ENV_POSTGRES_CONNECT_TIMEOUT,
    ENV_POSTGRES_MAX_CONNECTIONS
} from './constants.mjs';
import { DatabaseConfigError } from './exceptions.mjs';
import { resolve, resolveInt } from '@internal/env-resolve';



export class PostgresConfig {
    constructor(options = {}) {
        this.host = resolve(options.host, ENV_POSTGRES_HOST, options, 'host', DEFAULT_CONFIG.host);
        this.port = resolveInt(options.port, ENV_POSTGRES_PORT, options, 'port', DEFAULT_CONFIG.port);
        this.username = resolve(options.username, ENV_POSTGRES_USER, options, 'username', DEFAULT_CONFIG.username);
        this.password = resolve(options.password, ENV_POSTGRES_PASSWORD, options, 'password', DEFAULT_CONFIG.password);
        this.database = resolve(options.database, ENV_POSTGRES_DB, options, 'database', DEFAULT_CONFIG.database);
        this.sslMode = resolve(options.sslMode, ENV_POSTGRES_SSL_MODE, options, 'sslMode', DEFAULT_CONFIG.sslMode);

        // CA Certs might be file path in env, or content.
        let caCerts = resolve(options.sslCaCerts, ENV_POSTGRES_SSL_CA_FILE, options, 'sslCaCerts', DEFAULT_CONFIG.sslCaCerts);
        if (caCerts && fs.existsSync(caCerts)) {
            try {
                caCerts = fs.readFileSync(caCerts, 'utf8');
            } catch (e) {
                // If failed to read, keep as is
            }
        }
        this.sslCaCerts = caCerts;

        this.connectTimeout = resolveInt(options.connectTimeout, ENV_POSTGRES_CONNECT_TIMEOUT, options, 'connectTimeout', DEFAULT_CONFIG.connectTimeout);
        this.maxConnections = resolveInt(options.maxConnections, ENV_POSTGRES_MAX_CONNECTIONS, options, 'maxConnections', DEFAULT_CONFIG.maxConnections);

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

    getConnectionConfig() {
        const config = {
            host: this.host,
            port: this.port,
            user: this.username,
            password: this.password,
            database: this.database,
            max: this.maxConnections,
            connectionTimeoutMillis: this.connectTimeout,
        };

        if (this.sslMode === 'disable') {
            config.ssl = false;
        } else {
            const dialectOptions = this.getSequelizeDialectOptions();
            if (dialectOptions.ssl) {
                config.ssl = dialectOptions.ssl;
            }
        }

        return config;
    }
}
