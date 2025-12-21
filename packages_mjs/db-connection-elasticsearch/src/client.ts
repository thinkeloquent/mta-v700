import { Client as ElasticsearchClient, ClientOptions } from "@elastic/elasticsearch";
import { Client as OpenSearchClient } from "@opensearch-project/opensearch";
import { ElasticsearchConfig, ElasticsearchConfigOptions } from "./config";
import { VENDOR_ELASTIC_CLOUD, VENDOR_DIGITAL_OCEAN } from "./constants";

// Union type for both clients
type SearchClient = ElasticsearchClient | OpenSearchClient;

export class ElasticsearchConnectionError extends Error {
    constructor(message: string) {
        super(message);
        this.name = "ElasticsearchConnectionError";
    }
}

function _getOpenSearchOptions(cfg: ElasticsearchConfig): any {
    // Build options compatible with @opensearch-project/opensearch
    const opts: any = {
        node: cfg.getBaseUrl(),
        ssl: {
            rejectUnauthorized: cfg.options.verifyCerts || false,
        },
    };

    // Authentication - OpenSearch uses auth object with username/password
    if (cfg.options.username && cfg.options.password) {
        opts.auth = {
            username: cfg.options.username,
            password: cfg.options.password,
        };
    }

    return opts;
}

export async function getElasticsearchClient(
    config?: Partial<ElasticsearchConfigOptions> | ElasticsearchConfig
): Promise<SearchClient> {
    let cfg: ElasticsearchConfig;
    if (config instanceof ElasticsearchConfig) {
        cfg = config;
    } else {
        cfg = new ElasticsearchConfig(config);
    }

    const client = getSyncElasticsearchClient(cfg);

    if (cfg.options.verifyClusterConnection) {
        try {
            // Use any to handle both Elasticsearch and OpenSearch client types
            const ping = await (client as any).ping();
            if (!ping) {
                throw new Error("Ping returned false");
            }
        } catch (e: any) {
            throw new ElasticsearchConnectionError(`Failed to verify connection: ${e.message}`);
        }
    }

    return client;
}

export function getSyncElasticsearchClient(
    config?: Partial<ElasticsearchConfigOptions> | ElasticsearchConfig
): SearchClient {
    let cfg: ElasticsearchConfig;
    if (config instanceof ElasticsearchConfig) {
        cfg = config;
    } else {
        cfg = new ElasticsearchConfig(config);
    }

    // Use OpenSearch client for DigitalOcean
    if (cfg.options.vendorType === VENDOR_DIGITAL_OCEAN) {
        return _createOpenSearchClient(cfg);
    } else if (cfg.options.vendorType === VENDOR_ELASTIC_CLOUD) {
        return _createSyncCloudClient(cfg);
    } else {
        // ON_PREM and others use Elasticsearch client
        return _createSyncUrlClient(cfg);
    }
}

function _createOpenSearchClient(cfg: ElasticsearchConfig): OpenSearchClient {
    const opts = _getOpenSearchOptions(cfg);
    return new OpenSearchClient(opts);
}

function _createSyncCloudClient(cfg: ElasticsearchConfig): ElasticsearchClient {
    const opts = cfg.getConnectionOptions();
    return new ElasticsearchClient(opts);
}

function _createSyncUrlClient(cfg: ElasticsearchConfig): ElasticsearchClient {
    const opts = cfg.getConnectionOptions();
    // Ensure we passed node/hosts logic in config
    return new ElasticsearchClient(opts);
}

export async function checkConnection(
    config?: ElasticsearchConfig
): Promise<{ success: boolean; info?: any; error?: string }> {
    let client: SearchClient | null = null;
    try {
        client = await getElasticsearchClient(config);
        // Use any to handle both Elasticsearch and OpenSearch client types
        const info = await (client as any).info();
        return { success: true, info };
    } catch (e: any) {
        const host = config?.options?.host || "unknown";
        return {
            success: false,
            error: formatConnectionError(e, host),
        };
    } finally {
        if (client) {
            await (client as any).close();
        }
    }
}

export function formatConnectionError(err: Error, host: string): string {
    const msg = err.message || "";
    if (msg.includes("ECONNREFUSED")) {
        return `Connection refused to ${host}. Check if server is running.`;
    }
    if (msg.includes("certificate")) {
        return `SSL Error connecting to ${host}. Check certs.`;
    }
    return `Connection error to ${host}: ${msg}`;
}
