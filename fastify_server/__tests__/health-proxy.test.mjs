
import path from 'path';
import { fileURLToPath } from 'url';
import Fastify from 'fastify';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Ensure APP_ENV is set
process.env.APP_ENV = process.env.APP_ENV || 'dev';
process.env.FIGMA_PROXY_URL = 'http://figma-proxy:8080';

async function run() {
    try {
        await import('../src/load_app_config.mjs');
        const { default: appYamlConfigRoutes } = await import('../src/routes/healthz/app-yaml-config.mjs');

        const fastify = Fastify();
        fastify.register(appYamlConfigRoutes);

        await fastify.ready();

        // 1. Test Disabled Proxy (gemini_openai has proxy_url: false)
        console.log("Testing /provider/gemini_openai/proxy (Disabled)...");
        const resDisabled = await fastify.inject({
            method: 'GET',
            url: '/healthz/admin/app-yaml-config/provider/gemini_openai/proxy'
        });

        if (resDisabled.statusCode === 200) {
            const body = JSON.parse(resDisabled.payload);
            console.log(`SUCCESS: Source=${body.resolution.source}, Proxy=${body.proxy_url}`);
            if (body.proxy_url !== null || body.resolution.source !== 'disabled') {
                throw new Error(`Expected disabled/null, got ${body.resolution.source}/${body.proxy_url}`);
            }
        } else {
            console.error(`FAILED: Status ${resDisabled.statusCode}, Body: ${resDisabled.payload}`);
            process.exit(1);
        }

        // 2. Test Env Overwrite (figma)
        console.log("Testing /provider/figma/proxy (Env Overwrite)...");
        const resEnv = await fastify.inject({
            method: 'GET',
            url: '/healthz/admin/app-yaml-config/provider/figma/proxy'
        });

        if (resEnv.statusCode === 200) {
            const body = JSON.parse(resEnv.payload);
            console.log(`SUCCESS: Source=${body.resolution.source}, Proxy=${body.proxy_url}`);
            if (body.resolution.source !== 'env_overwrite') {
                throw new Error(`Expected env_overwrite, got ${body.resolution.source}`);
            }
            if (body.proxy_url !== 'http://figma-proxy:8080') {
                throw new Error(`Expected http://figma-proxy:8080, got ${body.proxy_url}`);
            }
        } else {
            console.error(`FAILED: Status ${resEnv.statusCode}, Body: ${resEnv.payload}`);
            process.exit(1);
        }

        process.exit(0);
    } catch (err) {
        console.error(`ERROR: ${err.message}`);
        console.error(err);
        process.exit(1);
    }
}

run();
