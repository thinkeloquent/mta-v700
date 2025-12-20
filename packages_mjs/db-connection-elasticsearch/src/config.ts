import { z } from "zod";
import {
    VENDOR_ON_PREM,
    VENDOR_ELASTIC_CLOUD,
    VENDOR_ELASTIC_TRANSPORT,
    VENDOR_DIGITAL_OCEAN,
    VALID_VENDORS,
} from "./constants";

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
        // We can merge sources into one object and let Zod parse it.

        // 1. Env Vars
        const envConfig = {
            vendorType: process.env.ELASTIC_DB_VENDOR_TYPE,
            host: process.env.ELASTIC_DB_HOST,
            port: process.env.ELASTIC_DB_PORT ? parseInt(process.env.ELASTIC_DB_PORT) : undefined,
            scheme: process.env.ELASTIC_DB_SCHEME,
            cloudId: process.env.ELASTIC_DB_CLOUD_ID,
            apiKey: process.env.ELASTIC_DB_API_KEY,
            username: process.env.ELASTIC_DB_USERNAME,
            password: process.env.ELASTIC_DB_PASSWORD,
            apiAuthType: process.env.ELASTIC_DB_API_AUTH_TYPE,
            useTls: process.env.ELASTIC_DB_USE_TLS === "true",
            verifyCerts: process.env.ELASTIC_DB_VERIFY_CERTS === "true",
            sslShowWarn: process.env.ELASTIC_DB_SSL_SHOW_WARN === "true",
            caCerts: process.env.ELASTIC_DB_CA_CERTS,
            clientCert: process.env.ELASTIC_DB_CLIENT_CERT,
            clientKey: process.env.ELASTIC_DB_CLIENT_KEY,
            index: process.env.ELASTIC_DB_INDEX,
            verifyClusterConnection: process.env.ELASTIC_DB_VERIFY_CLUSTER_CONNECTION === "true",
            requestTimeout: process.env.ELASTIC_DB_REQUEST_TIMEOUT ? parseFloat(process.env.ELASTIC_DB_REQUEST_TIMEOUT) : undefined,
            connectTimeout: process.env.ELASTIC_DB_CONNECT_TIMEOUT ? parseFloat(process.env.ELASTIC_DB_CONNECT_TIMEOUT) : undefined,
            maxRetries: process.env.ELASTIC_DB_MAX_RETRIES ? parseInt(process.env.ELASTIC_DB_MAX_RETRIES) : undefined,
            retryOnTimeout: process.env.ELASTIC_DB_RETRY_ON_TIMEOUT ? process.env.ELASTIC_DB_RETRY_ON_TIMEOUT === "true" : undefined,
        };

        // Remove undefined env keys
        Object.keys(envConfig).forEach(key => (envConfig as any)[key] === undefined && delete (envConfig as any)[key]);

        // 2. Config Dict (snake_case needs mapping to camelCase?)
        // Assuming configDict might be passed with camelCase or snake_case keys. Pydantic accepts kwargs.
        // Let's assume configDict uses camelCase or we map it. 
        // Spec naming convention mapping tells us fields.
        // Let's rely on options being passed correctly.

        // Merge: Defaults (handled by Zod) < ConfigDict < Env < Options
        // Wait, typical priority: Args (options) > Env > Config

        const merged = {
            ...configDict,
            ...envConfig,
            ...options
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

        // Auth
        if (this.options.apiKey) {
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
