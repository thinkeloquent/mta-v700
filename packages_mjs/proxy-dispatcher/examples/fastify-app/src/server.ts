import Fastify from "fastify";
import {
    ProxyDispatcherFactory,
    FactoryConfig,
    getProxyDispatcher
} from "@internal/proxy-dispatcher";
import { request } from "undici";

const fastify = Fastify({
    logger: true
});

// 1. Singleton pattern (Recommended)
// Initialize factory with config (e.g. from loaded app.yaml)
const factoryConfig: FactoryConfig = {
    defaultEnvironment: "dev",
    proxyUrls: {
        dev: "http://dev-proxy:3128",
        prod: "http://prod-proxy:3128"
    }
};

const factory = new ProxyDispatcherFactory(factoryConfig);

// Register a decorator or plugin to provide the configured dispatcher
fastify.decorate("getProxyDispatcher", (options?: any) => {
    return factory.getProxyDispatcher(options);
});

fastify.get("/health", async () => {
    return { status: "ok" };
});

fastify.get("/proxy-test", async (request, reply) => {
    try {
        // Get configured dispatcher
        const { client, config } = factory.getProxyDispatcher();

        reply.log.info({ config }, "Using proxy configuration");

        // Example request using the configured client (undici Agent)
        // Note: undici.request can take a dispatcher option
        // In a real app you might use fetch() with the dispatcher, or the client directly if it's a higher level client.
        // Here 'client' is an undici Agent.

        return {
            message: "Proxy configuration resolved",
            proxyUrl: config.proxyUrl,
            verifySsl: config.verifySsl
        };
    } catch (err) {
        request.log.error(err);
        return reply.code(500).send({ error: "Internal Server Error" });
    }
});

// 2. Simple Convenience Function approach (Quick scripts)
fastify.get("/simple-proxy-test", async () => {
    // Uses global default factory and env vars
    const { config } = getProxyDispatcher();
    return {
        message: "Key configuration resolved from env",
        proxyUrl: config.proxyUrl
    };
});

const start = async () => {
    try {
        await fastify.listen({ port: 3000 });
    } catch (err) {
        fastify.log.error(err);
        process.exit(1);
    }
};

start();
