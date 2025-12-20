import { Sequelize } from 'sequelize';
import { PostgresConfig } from './config.mjs';
import { DatabaseConnectionError } from './exceptions.mjs';

export function getPostgresClient(config) {
    if (!(config instanceof PostgresConfig)) {
        config = new PostgresConfig(config);
    }

    const dialectOptions = config.getSequelizeDialectOptions();

    return new Sequelize({
        dialect: 'postgres',
        host: config.host,
        port: config.port,
        username: config.username,
        password: config.password,
        database: config.database,
        logging: false, // Or config logger
        pool: {
            max: config.maxConnections,
            min: 0,
            acquire: 30000,
            idle: 10000,
        },
        dialectOptions: dialectOptions,
    });
}

export async function checkConnection(client) {
    try {
        await client.authenticate();
        return true;
    } catch (error) {
        throw new DatabaseConnectionError(`Health check failed: ${error.message}`, error);
    }
}
