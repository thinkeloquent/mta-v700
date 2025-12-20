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
    maxConnections: null,
    minConnections: null,
    healthCheckInterval: 0,
};

export const VALID_VENDORS = [
    'aws-elasticache',
    'redis-cloud',
    'upstash',
    'digital-ocean',
    'on-prem',
];
