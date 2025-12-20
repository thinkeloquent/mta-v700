import { Client, ClientOptions } from "@elastic/elasticsearch";
import { ElasticsearchConfig, ElasticsearchConfigOptions } from "./config";
import { VENDOR_ELASTIC_CLOUD } from "./constants";

export class ElasticsearchConnectionError extends Error {
    constructor(message: string) {
        super(message);
        this.name = "ElasticsearchConnectionError";
    }
}

export async function getElasticsearchClient(
    config?: Partial<ElasticsearchConfigOptions> | ElasticsearchConfig
): Promise<Client> {
    let cfg: ElasticsearchConfig;
    if (config instanceof ElasticsearchConfig) {
        cfg = config;
    } else {
        cfg = new ElasticsearchConfig(config);
    }

    const client = getSyncElasticsearchClient(cfg);

    if (cfg.options.verifyClusterConnection) {
        try {
            const ping = await client.ping();
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
): Client {
    let cfg: ElasticsearchConfig;
    if (config instanceof ElasticsearchConfig) {
        cfg = config;
    } else {
        cfg = new ElasticsearchConfig(config);
    }

    if (cfg.options.vendorType === VENDOR_ELASTIC_CLOUD) {
        return _createSyncCloudClient(cfg);
    } else {
        return _createSyncUrlClient(cfg);
    }
}

function _createSyncCloudClient(cfg: ElasticsearchConfig): Client {
    const opts = cfg.getConnectionOptions();
    return new Client(opts);
}

function _createSyncUrlClient(cfg: ElasticsearchConfig): Client {
    const opts = cfg.getConnectionOptions();

    // Ensure we passed node/hosts logic in config
    return new Client(opts);
}

export async function checkConnection(
    config?: ElasticsearchConfig
): Promise<{ success: boolean; info?: any; error?: string }> {
    let client: Client | null = null;
    try {
        client = await getElasticsearchClient(config);
        const info = await client.info();
        return { success: true, info };
    } catch (e: any) {
        const host = config?.options?.host || "unknown";
        return {
            success: false,
            error: formatConnectionError(e, host),
        };
    } finally {
        if (client) {
            await client.close();
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
