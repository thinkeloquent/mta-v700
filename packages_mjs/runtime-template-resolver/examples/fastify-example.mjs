/**
 * Fastify integration example for runtime-template-resolver.
 * Run with: node examples/fastify-example.mjs
 */
import Fastify from 'fastify';
import { resolve } from '../dist/index.js';

const fastify = Fastify({
    logger: true
});

// Simulated database/config
const TEMPLATE_CONFIG = {
    welcome_message: "Hello {{user.name}} from {{client.ip}}",
    status_header: "System is {{system.status}} at {{timestamp}}"
};

fastify.get('/', async (request, reply) => {
    // Build request context
    const context = {
        user: {
            name: request.query.name || "Anonymous",
            agent: request.headers['user-agent']
        },
        client: {
            ip: request.ip
        },
        system: {
            status: "operational"
        },
        timestamp: Date.now()
    };

    // Resolve templates
    const message = resolve(TEMPLATE_CONFIG.welcome_message, context);
    const header = resolve(TEMPLATE_CONFIG.status_header, context);

    return {
        message,
        debug_header: header,
        context
    };
});

// Handle missing deps gracefully for example
try {
    await fastify.listen({ port: 3000 });
} catch (err) {
    fastify.log.error(err);
    process.exit(1);
}
