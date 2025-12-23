import Fastify from 'fastify';
import { fetchAuthConfig, AuthConfig } from '@internal/fetch-auth-config';

const fastify = Fastify({
    logger: true
});

// --- Mock Configuration ---
const MOCK_CONFIG = {
    github: {
        api_auth_type: 'bearer',
        env_api_key: 'GITHUB_TOKEN'
    },
    stripe: {
        api_auth_type: 'basic',
        env_username: 'STRIPE_KEY',
        env_password: 'STRIPE_SECRET'
    }
};

// --- Plugin/Decorator to resolve auth ---
// In a real app, this logic might be in a separate plugin or middleware

fastify.decorate('getGitHubAuth', (): AuthConfig => {
    return fetchAuthConfig({
        providerName: 'github',
        providerConfig: MOCK_CONFIG.github
    });
});

// Add type definition
declare module 'fastify' {
    interface FastifyInstance {
        getGitHubAuth(): AuthConfig;
    }
}

// --- Routes ---

fastify.get('/health', async () => {
    return { status: 'ok' };
});

fastify.get('/github-check', async (request, reply) => {
    try {
        // Resolve auth for this request (or could be resolved at startup if static)
        const auth = fastify.getGitHubAuth();

        return {
            provider: auth.providerName,
            type: auth.type,
            headerName: auth.headerName,
            // Demo only - do not log tokens in production
            tokenPreview: auth.token ? `${auth.token.substring(0, 4)}...` : null,
            source: auth.resolution.resolvedFrom
        };
    } catch (err) {
        request.log.error(err);
        reply.status(500).send({ error: 'Auth resolution failed', details: (err as Error).message });
    }
});

// --- Start ---
const start = async () => {
    try {
        // Note: Set GITHUB_TOKEN env var before running
        // export GITHUB_TOKEN=ghp_test123
        await fastify.listen({ port: 3000, host: '0.0.0.0' });
    } catch (err) {
        fastify.log.error(err);
        process.exit(1);
    }
};

start();
