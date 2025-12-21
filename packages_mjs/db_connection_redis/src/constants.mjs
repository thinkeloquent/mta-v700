// Environment Variable Keys
export const ENV_REDIS_HOST = ['REDIS_HOST', 'REDIS_HOSTNAME'];
export const ENV_REDIS_PORT = ['REDIS_PORT'];
export const ENV_REDIS_USERNAME = ['REDIS_USERNAME', 'REDIS_USER'];
export const ENV_REDIS_PASSWORD = ['REDIS_PASSWORD', 'REDIS_AUTH'];
export const ENV_REDIS_DB = ['REDIS_DB', 'REDIS_DATABASE'];
export const ENV_REDIS_SSL = ['REDIS_SSL', 'REDIS_USE_TLS', 'REDIS_TLS'];
export const ENV_REDIS_SSL_CERT_REQS = ['REDIS_SSL_CERT_REQS'];
export const ENV_REDIS_SSL_CA_CERTS = ['REDIS_SSL_CA_CERTS'];
export const ENV_REDIS_SSL_CHECK_HOSTNAME = ['REDIS_SSL_CHECK_HOSTNAME'];
export const ENV_REDIS_SOCKET_TIMEOUT = ['REDIS_SOCKET_TIMEOUT'];
export const ENV_REDIS_SOCKET_CONNECT_TIMEOUT = ['REDIS_SOCKET_CONNECT_TIMEOUT'];
export const ENV_REDIS_MAX_CONNECTIONS = ['REDIS_MAX_CONNECTIONS'];
export const ENV_REDIS_MIN_CONNECTIONS = ['REDIS_MIN_CONNECTIONS'];

export const DEFAULT_CONFIG = {
    host: 'localhost',
    port: 6379,
    username: null,
    password: null,
    db: 0,
    useTls: false,
    sslCertReqs: 'none',
    sslCaCerts: null,
    sslCheckHostname: false,
    socketTimeout: 5000,
    socketConnectTimeout: 5000,
    retryOnTimeout: false,
    maxConnections: 10,
    minConnections: 0,
    healthCheckInterval: 0,
};

export const VALID_VENDORS = [
    'aws-elasticache',
    'redis-cloud',
    'upstash',
    'digital-ocean',
    'on-prem',
];
