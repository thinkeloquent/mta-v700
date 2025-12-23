

import path from 'path';
import { fileURLToPath } from 'url';
import Fastify from 'fastify';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Ensure APP_ENV is set
process.env.APP_ENV = process.env.APP_ENV || 'dev';
process.env.GEMINI_API_KEY = 'mock_gemini_key';
process.env.CONFLUENCE_API_TOKEN = 'mock_confluence_token';
process.env.CONFLUENCE_EMAIL = 'mock@example.com';
process.env.REDIS_HOST = 'localhost';

async function run() {
    try {
        await import('../src/load_app_config.mjs');
        const { default: appYamlConfigRoutes } = await import('../src/routes/healthz/app-yaml-config.mjs');

        const fastify = Fastify();
        fastify.register(appYamlConfigRoutes);

        await fastify.ready();

        // 1. Test Provider Auth Config (gemini_openai)
        console.log("Testing /healthz/admin/app-yaml-config/provider/gemini_openai/auth_config...");
        const resProvider = await fastify.inject({
            method: 'GET',
            url: '/healthz/admin/app-yaml-config/provider/gemini_openai/auth_config'
        });

        if (resProvider.statusCode === 200) {
            const body = JSON.parse(resProvider.payload);
            console.log(`SUCCESS: Provider Auth Type: ${body.authType}`);
            if (!body.credentials) throw new Error("Missing credentials object");
        } else if (resProvider.statusCode === 404) {
            console.log("SUCCESS: Provider not found (Access Allowed).");
        } else {
            console.error(`FAILED: Status ${resProvider.statusCode}, Body: ${resProvider.payload}`);
            process.exit(1);
        }

        // 2. Test Provider Auth Config (confluence)
        console.log("Testing /healthz/admin/app-yaml-config/provider/confluence/auth_config...");
        const resService = await fastify.inject({
            method: 'GET',
            url: '/healthz/admin/app-yaml-config/provider/confluence/auth_config'
        });

        if (resService.statusCode === 200) {
            const body = JSON.parse(resService.payload);
            console.log(`SUCCESS: Service Auth Type: ${body.authType}`);
        } else {
            console.error(`FAILED: Status ${resService.statusCode}, Body: ${resService.payload}`);
            process.exit(1);
        }


        // 4. Test Forbidden
        console.log("Testing /healthz/admin/app-yaml-config/provider/forbidden_provider/auth_config...");
        const resForbidden = await fastify.inject({
            method: 'GET',
            url: '/healthz/admin/app-yaml-config/provider/forbidden_provider/auth_config'
        });

        if (resForbidden.statusCode !== 403) {
            console.error(`FAILED: Expected 403, got ${resForbidden.statusCode}`);
            process.exit(1);
        }
        console.log("SUCCESS: 403 verified.");

        process.exit(0);
    } catch (err) {
        console.error(`ERROR: ${err.message}`);
        console.error(err);
        process.exit(1);
    }
}

run();
