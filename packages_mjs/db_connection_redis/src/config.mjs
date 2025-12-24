import fs from "fs";
import { URL } from "url";
import { RedisConfigSchema } from "./schemas.mjs";
import {
  DEFAULT_CONFIG,
  ENV_REDIS_HOST,
  ENV_REDIS_PORT,
  ENV_REDIS_USERNAME,
  ENV_REDIS_PASSWORD,
  ENV_REDIS_DB,
  ENV_REDIS_SSL,
  ENV_REDIS_SSL_CERT_REQS,
  ENV_REDIS_SSL_CA_CERTS,
  ENV_REDIS_SSL_CHECK_HOSTNAME,
  ENV_REDIS_SOCKET_TIMEOUT,
  ENV_REDIS_SOCKET_CONNECT_TIMEOUT,
  ENV_REDIS_MAX_CONNECTIONS,
  ENV_REDIS_MIN_CONNECTIONS,
} from "./constants.mjs";
import { RedisConfigError } from "./exceptions.mjs";
import {
  resolve,
  resolveBool,
  resolveInt,
  resolveFloat,
} from "@internal/env-resolve";

export class RedisConfig {
  constructor(options = {}) {
    this.host = resolve(
      options.host,
      ENV_REDIS_HOST,
      options,
      "host",
      DEFAULT_CONFIG.host
    );
    this.port = resolveInt(
      options.port,
      ENV_REDIS_PORT,
      options,
      "port",
      DEFAULT_CONFIG.port
    );
    this.username = resolve(
      options.username,
      ENV_REDIS_USERNAME,
      options,
      "username",
      DEFAULT_CONFIG.username
    );
    this.password = resolve(
      options.password,
      ENV_REDIS_PASSWORD,
      options,
      "password",
      DEFAULT_CONFIG.password
    );
    this.db = resolveInt(
      options.db,
      ENV_REDIS_DB,
      options,
      "db",
      DEFAULT_CONFIG.db
    );

    this.useTls = resolveBool(
      options.useTls,
      ENV_REDIS_SSL,
      options,
      "useTls",
      DEFAULT_CONFIG.useTls
    );
    this.sslCertReqs = resolve(
      options.sslCertReqs,
      ENV_REDIS_SSL_CERT_REQS,
      options,
      "sslCertReqs",
      DEFAULT_CONFIG.sslCertReqs
    );

    let caCerts = resolve(
      options.sslCaCerts,
      ENV_REDIS_SSL_CA_CERTS,
      options,
      "sslCaCerts",
      DEFAULT_CONFIG.sslCaCerts
    );
    if (caCerts && fs.existsSync(caCerts)) {
      try {
        caCerts = fs.readFileSync(caCerts, "utf8");
      } catch (e) {
        // ignore
      }
    }
    this.sslCaCerts = caCerts;

    this.sslCheckHostname = resolveBool(
      options.sslCheckHostname,
      ENV_REDIS_SSL_CHECK_HOSTNAME,
      options,
      "sslCheckHostname",
      DEFAULT_CONFIG.sslCheckHostname
    );

    // Socket timeout from env is in seconds, convert to milliseconds for ioredis
    let socketTimeoutRaw = resolveFloat(
      options.socketTimeout,
      ENV_REDIS_SOCKET_TIMEOUT,
      options,
      "socketTimeout",
      null
    );
    if (socketTimeoutRaw !== null && socketTimeoutRaw < 100) {
      // If value is small (< 100), assume it's in seconds and convert to ms
      this.socketTimeout = socketTimeoutRaw * 1000;
    } else {
      this.socketTimeout = socketTimeoutRaw || DEFAULT_CONFIG.socketTimeout;
    }

    let socketConnectTimeoutRaw = resolveFloat(
      options.socketConnectTimeout,
      ENV_REDIS_SOCKET_CONNECT_TIMEOUT,
      options,
      "socketConnectTimeout",
      null
    );
    if (socketConnectTimeoutRaw !== null && socketConnectTimeoutRaw < 100) {
      this.socketConnectTimeout = socketConnectTimeoutRaw * 1000;
    } else {
      this.socketConnectTimeout =
        socketConnectTimeoutRaw || DEFAULT_CONFIG.socketConnectTimeout;
    }
    this.retryOnTimeout = resolveBool(
      options.retryOnTimeout,
      [],
      options,
      "retryOnTimeout",
      DEFAULT_CONFIG.retryOnTimeout
    );

    this.maxConnections = resolveInt(
      options.maxConnections,
      ENV_REDIS_MAX_CONNECTIONS,
      options,
      "maxConnections",
      DEFAULT_CONFIG.maxConnections
    );
    this.minConnections = resolveInt(
      options.minConnections,
      ENV_REDIS_MIN_CONNECTIONS,
      options,
      "minConnections",
      DEFAULT_CONFIG.minConnections
    );
    this.healthCheckInterval = resolveFloat(
      options.healthCheckInterval,
      [],
      options,
      "healthCheckInterval",
      DEFAULT_CONFIG.healthCheckInterval
    );

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
      if (url.protocol === "rediss:") this.useTls = true;
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
    if (
      this.host.includes("cache.amazonaws.com") ||
      this.host.includes("redis-cloud.com") ||
      this.host.includes("upstash.io") ||
      (this.host.includes("db.ondigitalocean.com") && this.port === 25061)
    ) {
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
    if (this.useTls === undefined) return undefined;

    const ssl = {};

    if (process.env.NODE_TLS_REJECT_UNAUTHORIZED === "0") {
      ssl.rejectUnauthorized = false;
    }

    if (this.useTls === true) {
      ssl.rejectUnauthorized = true;
    }

    // Similar to PostgreSQL ssl_mode:
    // - 'none' or 'required': use TLS but don't verify certificate
    // - 'verify-ca' or 'verify-full': verify certificate
    if (
      this.sslCertReqs === "verify-ca" ||
      this.sslCertReqs === "verify-full"
    ) {
      ssl.rejectUnauthorized = true;
    }

    if (
      this.sslCertReqs === "none" ||
      this.sslCertReqs === "required" ||
      this.useTls === false
    ) {
      ssl.rejectUnauthorized = false;
    }

    if (this.sslCaCerts) {
      ssl.ca = [this.sslCaCerts];
    }

    if (!this.sslCheckHostname || this.sslCertReqs !== "verify-full") {
      ssl.checkServerIdentity = () => undefined;
    }

    return ssl;
  }
}
