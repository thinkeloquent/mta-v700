/**
 * Fastify example demonstrating db-connection-elasticsearch usage.
 *
 * Run with: npm run dev:ts
 */

import Fastify, { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { Client } from "@elastic/elasticsearch";
import {
    ElasticsearchConfig,
    getElasticsearchClient,
    getSyncElasticsearchClient,
    checkConnection,
} from "@internal/db-connection-elasticsearch";

// Request/Response types
interface SearchRequest {
    query: string;
    index?: string;
    size?: number;
}

interface DocumentRequest {
    index: string;
    document: Record<string, any>;
    id?: string;
}

interface SearchResult {
    total: number;
    hits: Array<{
        _id: string;
        _index: string;
        _score: number;
        _source: Record<string, any>;
    }>;
}

interface HealthResponse {
    status: string;
    elasticsearch: {
        connected: boolean;
        cluster_name?: string;
        version?: string;
        error?: string;
    };
}

// Global client reference
let esClient: Client | null = null;

// Create Fastify instance
const fastify: FastifyInstance = Fastify({
    logger: true,
});

// Initialize Elasticsearch client
async function initElasticsearch(): Promise<void> {
    const config = new ElasticsearchConfig({
        host: process.env.ELASTIC_DB_HOST || "localhost",
        port: process.env.ELASTIC_DB_PORT ? parseInt(process.env.ELASTIC_DB_PORT) : 9200,
        scheme: process.env.ELASTIC_DB_SCHEME || "https",
        username: process.env.ELASTIC_DB_USERNAME || undefined,
        password: process.env.ELASTIC_DB_PASSWORD || undefined,
        apiKey: process.env.ELASTIC_DB_API_KEY || undefined,
        verifyCerts: process.env.ELASTIC_DB_VERIFY_CERTS === "true",
    });

    try {
        esClient = await getElasticsearchClient(config);
        fastify.log.info("Elasticsearch client initialized");
    } catch (e: any) {
        fastify.log.warn(`Could not connect to Elasticsearch: ${e.message}`);
        esClient = null;
    }
}

// Health check endpoint
fastify.get<{ Reply: HealthResponse }>("/health", async (request, reply) => {
    if (!esClient) {
        return {
            status: "degraded",
            elasticsearch: { connected: false, error: "Client not initialized" },
        };
    }

    try {
        const info = await esClient.info();
        return {
            status: "healthy",
            elasticsearch: {
                connected: true,
                cluster_name: info.cluster_name,
                version: info.version?.number,
            },
        };
    } catch (e: any) {
        return {
            status: "degraded",
            elasticsearch: { connected: false, error: e.message },
        };
    }
});

// Connection check using library function
fastify.get("/connection/check", async (request, reply) => {
    const result = await checkConnection();
    return result;
});

// List indices
fastify.get("/indices", async (request, reply) => {
    if (!esClient) {
        return reply.code(503).send({ error: "Elasticsearch not connected" });
    }

    try {
        const indices = await esClient.cat.indices({ format: "json" });
        return { indices };
    } catch (e: any) {
        return reply.code(500).send({ error: e.message });
    }
});

// Search documents
fastify.post<{ Body: SearchRequest; Reply: SearchResult }>(
    "/search",
    async (request, reply) => {
        if (!esClient) {
            return reply.code(503).send({ error: "Elasticsearch not connected" } as any);
        }

        const { query, index = "_all", size = 10 } = request.body;

        try {
            const response = await esClient.search({
                index,
                body: {
                    query: {
                        multi_match: {
                            query,
                            fields: ["*"],
                        },
                    },
                    size,
                },
            });

            const hits = response.hits;
            return {
                total:
                    typeof hits.total === "number"
                        ? hits.total
                        : hits.total?.value || 0,
                hits: hits.hits.map((hit: any) => ({
                    _id: hit._id,
                    _index: hit._index,
                    _score: hit._score,
                    _source: hit._source,
                })),
            };
        } catch (e: any) {
            return reply.code(500).send({ error: e.message } as any);
        }
    }
);

// Index a document
fastify.post<{ Body: DocumentRequest }>("/documents", async (request, reply) => {
    if (!esClient) {
        return reply.code(503).send({ error: "Elasticsearch not connected" });
    }

    const { index, document, id } = request.body;

    try {
        const response = id
            ? await esClient.index({ index, id, document })
            : await esClient.index({ index, document });

        return {
            _id: response._id,
            _index: response._index,
            result: response.result,
        };
    } catch (e: any) {
        return reply.code(500).send({ error: e.message });
    }
});

// Get document by ID
fastify.get<{ Params: { index: string; docId: string } }>(
    "/documents/:index/:docId",
    async (request, reply) => {
        if (!esClient) {
            return reply.code(503).send({ error: "Elasticsearch not connected" });
        }

        const { index, docId } = request.params;

        try {
            const response = await esClient.get({ index, id: docId });
            return {
                _id: response._id,
                _index: response._index,
                _source: response._source,
            };
        } catch (e: any) {
            if (e.meta?.statusCode === 404) {
                return reply.code(404).send({ error: "Document not found" });
            }
            return reply.code(500).send({ error: e.message });
        }
    }
);

// Delete document by ID
fastify.delete<{ Params: { index: string; docId: string } }>(
    "/documents/:index/:docId",
    async (request, reply) => {
        if (!esClient) {
            return reply.code(503).send({ error: "Elasticsearch not connected" });
        }

        const { index, docId } = request.params;

        try {
            const response = await esClient.delete({ index, id: docId });
            return {
                _id: response._id,
                _index: response._index,
                result: response.result,
            };
        } catch (e: any) {
            if (e.meta?.statusCode === 404) {
                return reply.code(404).send({ error: "Document not found" });
            }
            return reply.code(500).send({ error: e.message });
        }
    }
);

// Start server
async function start(): Promise<void> {
    try {
        // Initialize Elasticsearch
        await initElasticsearch();

        // Start Fastify
        const port = process.env.PORT ? parseInt(process.env.PORT) : 3000;
        await fastify.listen({ port, host: "0.0.0.0" });
        fastify.log.info(`Server running on port ${port}`);
    } catch (err) {
        fastify.log.error(err);
        process.exit(1);
    }
}

// Graceful shutdown
const signals: NodeJS.Signals[] = ["SIGINT", "SIGTERM"];
signals.forEach((signal) => {
    process.on(signal, async () => {
        fastify.log.info(`Received ${signal}, shutting down...`);
        if (esClient) {
            await esClient.close();
            fastify.log.info("Elasticsearch client closed");
        }
        await fastify.close();
        process.exit(0);
    });
});

start();
