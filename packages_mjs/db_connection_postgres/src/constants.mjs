// Environment Variable Keys
export const ENV_POSTGRES_HOST = [
  "POSTGRES_HOST",
  "POSTGRES_HOSTNAME",
  "DATABASE_HOST",
];
export const ENV_POSTGRES_PORT = ["POSTGRES_PORT", "DATABASE_PORT"];
export const ENV_POSTGRES_USER = [
  "POSTGRES_USER",
  "DATABASE_USER",
  "POSTGRES_USERNAME",
];
export const ENV_POSTGRES_PASSWORD = ["POSTGRES_PASSWORD", "DATABASE_PASSWORD"];
export const ENV_POSTGRES_DB = [
  "POSTGRES_DB",
  "POSTGRES_DATABASE",
  "DATABASE_NAME",
];
export const ENV_POSTGRES_SCHEMA = ["POSTGRES_SCHEMA", "DATABASE_SCHEMA"];
export const ENV_POSTGRES_SSL_MODE = ["POSTGRES_SSL_MODE", "DATABASE_SSL_MODE"];
export const ENV_POSTGRES_SSL_CA_FILE = [
  "POSTGRES_SSL_CA_CERTS",
  "POSTGRES_SSL_CA_FILE",
];
export const ENV_POSTGRES_CONNECT_TIMEOUT = ["POSTGRES_CONNECT_TIMEOUT"];
export const ENV_POSTGRES_MAX_CONNECTIONS = [
  "POSTGRES_POOL_SIZE",
  "DATABASE_POOL_SIZE",
];

export const DEFAULT_CONFIG = {
  host: "localhost",
  port: 5432,
  username: "postgres",
  password: "",
  database: "postgres",
  sslMode: "prefer",
  sslCaCerts: null,
  connectTimeout: 30000,
  maxConnections: 10,
};

export const SSL_MODES = [
  "disable",
  "allow",
  "prefer",
  "require",
  "verify-ca",
  "verify-full",
];
