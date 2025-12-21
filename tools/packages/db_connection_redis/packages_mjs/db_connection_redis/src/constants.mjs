export const DEFAULT_CONFIG = {
    host: 'localhost',
    port: 6379,
    username: null,
    password: null,
    db: 0,
    useTls: true,
    sslCertReqs: null,
    sslCaCerts: null,
    sslCheckHostname: false,
    socketTimeout: 5000,
    socketConnectTimeout: 5000,
    retryOnTimeout: false,
    maxConnections: 1,
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
