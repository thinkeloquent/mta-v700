import { z } from "zod";
import {
    VENDOR_ON_PREM,
    VENDOR_ELASTIC_CLOUD,
    VENDOR_ELASTIC_TRANSPORT,
    VENDOR_DIGITAL_OCEAN,
    VALID_VENDORS,
    ENV_ELASTIC_VENDOR_TYPE,
    ENV_ELASTIC_HOST,
    ENV_ELASTIC_PORT,
    ENV_ELASTIC_SCHEME,
    ENV_ELASTIC_CLOUD_ID,
    ENV_ELASTIC_API_KEY,
    ENV_ELASTIC_USERNAME,
    ENV_ELASTIC_PASSWORD,
    ENV_ELASTIC_ACCESS_KEY,
    ENV_ELASTIC_API_AUTH_TYPE,
    ENV_ELASTIC_USE_TLS,
    ENV_ELASTIC_VERIFY_CERTS,
    ENV_ELASTIC_SSL_SHOW_WARN,
    ENV_ELASTIC_CA_CERTS,
    ENV_ELASTIC_CLIENT_CERT,
    ENV_ELASTIC_CLIENT_KEY,
    ENV_ELASTIC_INDEX,
    ENV_ELASTIC_VERIFY_CLUSTER,
    ENV_ELASTIC_REQUEST_TIMEOUT,
    ENV_ELASTIC_CONNECT_TIMEOUT,
    ENV_ELASTIC_MAX_RETRIES,
    ENV_ELASTIC_RETRY_ON_TIMEOUT,
} from "./constants";
import { resolve, resolveBool, resolveInt, resolveFloat } from "@internal/env-resolve";

export const ElasticsearchConfigSchema = z.object({
    vendorType: z.string().optional().default(VENDOR_ON_PREM),
    host: z.string().optional().default("localhost"),
    port: z.number().int().min(1).max(65535).optional().default(9200),
    scheme: z.string().optional().default("https"),
    cloudId: z.string().nullable().optional(),
    apiKey: z.string().nullable().optional(),
    username: z.string().nullable().optional(),
    password: z.string().nullable().optional(),
    apiAuthType: z.string().nullable().optional(),
    useTls: z.boolean().optional().default(false),
    verifyCerts: z.boolean().optional().default(false),
    sslShowWarn: z.boolean().optional().default(false),
    caCerts: z.string().nullable().optional(),
    clientCert: z.string().nullable().optional(),
    clientKey: z.string().nullable().optional(),
    index: z.string().nullable().optional(),
    verifyClusterConnection: z.boolean().optional().default(false),
    requestTimeout: z.number().optional().default(30000), // ms in JS usually
    connectTimeout: z.number().optional().default(10000), // ms
    maxRetries: z.number().optional().default(3),
    retryOnTimeout: z.boolean().optional().default(true),
});

export type ElasticsearchConfigOptions = z.input<typeof ElasticsearchConfigSchema>;
export type ElasticsearchConfigResolved = z.infer<typeof ElasticsearchConfigSchema>;

export class ElasticsearchConfigError extends Error {
    constructor(message: string) {
        super(message);
        this.name = "ElasticsearchConfigError";
    }
}

export class ElasticsearchConfig {
    public options: ElasticsearchConfigResolved;


    constructor(
        options: Partial<ElasticsearchConfigOptions> = {},
        configDict: Record<string, any> = {}
    ) {
        // Resolution Logic: Args > Env > ConfigDict > Default

        const merged: any = {
            vendorType: resolve(options.vendorType, ENV_ELASTIC_VENDOR_TYPE, configDict, "vendorType", VENDOR_ON_PREM),
            host: resolve(options.host, ENV_ELASTIC_HOST, configDict, "host", "localhost"),
            port: resolveInt(options.port, ENV_ELASTIC_PORT, configDict, "port", 9200),
            scheme: resolve(options.scheme, ENV_ELASTIC_SCHEME, configDict, "scheme", "https"),
            cloudId: resolve(options.cloudId, ENV_ELASTIC_CLOUD_ID, configDict, "cloudId", null),
            apiKey: resolve(options.apiKey, ENV_ELASTIC_API_KEY, configDict, "apiKey", null),
            username: resolve(options.username, ENV_ELASTIC_USERNAME, configDict, "username", null),
            password: resolve(options.password, ENV_ELASTIC_PASSWORD, configDict, "password", null) || resolve(null, ENV_ELASTIC_ACCESS_KEY, null, null, null),
            apiAuthType: resolve(options.apiAuthType, ENV_ELASTIC_API_AUTH_TYPE, configDict, "apiAuthType", null),
            useTls: resolveBool(options.useTls, ENV_ELASTIC_USE_TLS, configDict, "useTls", false),
            verifyCerts: resolveBool(options.verifyCerts, ENV_ELASTIC_VERIFY_CERTS, configDict, "verifyCerts", false),
            sslShowWarn: resolveBool(options.sslShowWarn, ENV_ELASTIC_SSL_SHOW_WARN, configDict, "sslShowWarn", false),
            caCerts: resolve(options.caCerts, ENV_ELASTIC_CA_CERTS, configDict, "caCerts", null),
            clientCert: resolve(options.clientCert, ENV_ELASTIC_CLIENT_CERT, configDict, "clientCert", null),
            clientKey: resolve(options.clientKey, ENV_ELASTIC_CLIENT_KEY, configDict, "clientKey", null),
            index: resolve(options.index, ENV_ELASTIC_INDEX, configDict, "index", null),
            verifyClusterConnection: resolveBool(options.verifyClusterConnection, ENV_ELASTIC_VERIFY_CLUSTER, configDict, "verifyClusterConnection", false),
            requestTimeout: resolveFloat(options.requestTimeout, ENV_ELASTIC_REQUEST_TIMEOUT, configDict, "requestTimeout", 30000),
            connectTimeout: resolveFloat(options.connectTimeout, ENV_ELASTIC_CONNECT_TIMEOUT, configDict, "connectTimeout", 10000),
            maxRetries: resolveInt(options.maxRetries, ENV_ELASTIC_MAX_RETRIES, configDict, "maxRetries", 3),
            retryOnTimeout: resolveBool(options.retryOnTimeout, ENV_ELASTIC_RETRY_ON_TIMEOUT, configDict, "retryOnTimeout", true),
        };

        const parsed = ElasticsearchConfigSchema.safeParse(merged);

        if (!parsed.success) {
            throw new ElasticsearchConfigError(`Invalid config: ${parsed.error.message}`);
        }

        this.options = parsed.data;

        // Auto-detect vendor
        this._detectVendor();

        // Validation
        if (!VALID_VENDORS.has(this.options.vendorType!)) {
            // Should be caught by Zod if we used enum, but we used string default.
            // Let's enforce it.
        }
    }

    private _detectVendor() {
        if (this.options.cloudId) {
            this.options.vendorType = VENDOR_ELASTIC_CLOUD;
        } else if (this.options.host && (this.options.host.includes("digitaloceanspaces") || this.options.port === 25060)) {
            this.options.vendorType = VENDOR_DIGITAL_OCEAN;
        }
    }

    public parseCloudId(): { esHost: string; kibanaHost: string | null } {
        const cloudId = this.options.cloudId;
        if (!cloudId) {
            throw new ElasticsearchConfigError("cloudId is not set");
        }

        try {
            const parts = cloudId.split(":");
            const b64 = parts.length > 1 ? parts[1] : parts[0];
            const decoded = Buffer.from(b64, "base64").toString("utf8");
            const segments = decoded.split("$");

            if (segments.length < 2) {
                throw new Error("Invalid format");
            }

            const domainPort = segments[0];
            let domain = domainPort;
            if (domainPort.includes(":")) {
                domain = domainPort.split(":")[0];
            }

            const esUuid = segments[1];
            const esHost = `${esUuid}.${domain}`;

            let kibanaHost: string | null = null;
            if (segments.length > 2 && segments[2]) {
                kibanaHost = `${segments[2]}.${domain}`;
            }

            return { esHost, kibanaHost };
        } catch (e: any) {
            throw new ElasticsearchConfigError(`Failed to parse cloudId: ${e.message}`);
        }
    }

    public getBaseUrl(): string {
        if (this.options.vendorType === VENDOR_ELASTIC_CLOUD && this.options.cloudId) {
            const { esHost } = this.parseCloudId();
            return `https://${esHost}:443`;
        }
        const host = this.options.host || "localhost";
        return `${this.options.scheme}://${host}:${this.options.port}`;
    }

    public getUrlWithIndex(): string {
        const base = this.getBaseUrl();
        if (this.options.index) {
            return `${base}/${this.options.index}`;
        }
        return base;
    }

    public getTlsConfig(): any {
        const tls: any = {};
        if (this.options.useTls || this.options.scheme === "https") {
            if (this.options.caCerts) tls.ca = this.options.caCerts;
            if (this.options.clientCert) tls.cert = this.options.clientCert;
            if (this.options.clientKey) tls.key = this.options.clientKey;
            if (this.options.verifyCerts === false) tls.rejectUnauthorized = false;
        }
        return tls;
    }

    public getApiKey(): string | null {
        return this.options.apiKey || null;
    }

    // GAP-CLOSURE: getTransportKwargs
    public getTransportKwargs(): any {
        // Should return options compatible with elastic-transport
        return this.getConnectionOptions();
    }

    public getConnectionOptions(): any {
        const opts: any = {
            requestTimeout: this.options.requestTimeout,
            maxRetries: this.options.maxRetries,
        };

        // Auth - DigitalOcean uses basic auth, not API keys
        if (this.options.vendorType === VENDOR_DIGITAL_OCEAN) {
            if (this.options.username && this.options.password) {
                opts.auth = { username: this.options.username, password: this.options.password };
            }
        } else if (this.options.apiKey) {
            opts.auth = { apiKey: this.options.apiKey };
        } else if (this.options.username && this.options.password) {
            opts.auth = { username: this.options.username, password: this.options.password };
        } else if (this.options.cloudId) {
            // client supports cloud: { id: ... }
            opts.cloud = { id: this.options.cloudId };
        }

        // SSL
        opts.tls = this.getTlsConfig();

        // Hosts (if not cloud)
        if (!opts.cloud) {
            opts.node = this.getBaseUrl();
        }

        return opts;
    }
}
