import Redis from "ioredis";
import { RedisConfig } from "./config.mjs";
import { RedisConnectionError } from "./exceptions.mjs";

export function getRedisClient(config) {
  if (!(config instanceof RedisConfig)) {
    config = new RedisConfig(config);
  }

  const options = {
    host: config.host,
    port: config.port,
    db: config.db,
    connectTimeout: config.socketConnectTimeout,
    commandTimeout: config.socketTimeout, // ioredis uses commandTimeout
    retryStrategy: (times) => {
      if (config.retryOnTimeout) {
        return Math.min(times * 50, 2000);
      }
      return null; // Default ioredis retry logic is usually better than null, but sticking to spec intent
    },
  };

  if (config.username) options.username = config.username;
  if (config.password) options.password = config.password;

  const tlsConfig = config.getTlsConfig();
  if (tlsConfig) {
    options.tls = tlsConfig;
  }

  return new Redis(options);
}
