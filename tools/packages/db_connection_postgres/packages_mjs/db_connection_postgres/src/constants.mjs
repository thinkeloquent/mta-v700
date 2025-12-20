export const DEFAULT_CONFIG = {
    host: 'localhost',
    port: 5432,
    username: 'postgres',
    password: null,
    database: 'postgres',
    sslMode: 'prefer',
    sslCaCerts: null,
    connectTimeout: 30000,
    maxConnections: 5,
};

export const SSL_MODES = [
    'disable',
    'allow',
    'prefer',
    'require',
    'verify-ca',
    'verify-full',
];
