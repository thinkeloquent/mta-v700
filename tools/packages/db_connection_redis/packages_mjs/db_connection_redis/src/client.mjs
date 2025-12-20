import Redis from 'ioredis';
import { RedisConfig } from './config.mjs';
import { RedisConnectionError } from './exceptions.mjs';

export function getRedisClient(config) {
    if (!(config instanceof RedisConfig)) {
        config = new RedisConfig(config);
    }

    const options = {
        host: config.host,
        port: config.port,
        username: config.username,
        password: config.password,
        db: config.db,
        connectTimeout: config.socketConnectTimeout,
        commandTimeout: config.socketTimeout, // ioredis uses commandTimeout
        retryStrategy: (times) => {
            if (config.retryOnTimeout) {
                return Math.min(times * 50, 2000);
            }
            return null; // Default ioredis retry logic is usually better than null, but sticking to spec intent
        }
    };

    const tlsConfig = config.getTlsConfig();
    if (tlsConfig) {
        options.tls = tlsConfig;
    }

    return new Redis(options);
}
