
import path from 'path';
import { fileURLToPath } from 'url';
import Fastify from 'fastify';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = "/Users/Shared/autoload/mta-v700";

// Ensure APP_ENV is set
process.env.APP_ENV = process.env.APP_ENV || 'dev';

// Import loader and route
import './fastify_server/src/load_app_config.mjs';
import appYamlConfigRoutes from './fastify_server/src/routes/healthz/app-yaml-config.mjs';

async function run() {
    try {
        const fastify = Fastify();
        fastify.register(appYamlConfigRoutes);

        await fastify.ready();

        // Test valid key (allowed)
        console.log("Testing /healthz/admin/app-yaml-config/compute/proxy_url (Allowed)...");
        const response = await fastify.inject({
            method: 'GET',
            url: '/healthz/admin/app-yaml-config/compute/proxy_url'
        });

        if (response.statusCode !== 200) {
            console.error(`FAILED: Status ${response.statusCode}, Body: ${response.payload}`);
            process.exit(1);
        }
        console.log(`SUCCESS: Got proxy_url = ${JSON.parse(response.payload).value}`);

        // Test forbidden key
        console.log("Testing /healthz/admin/app-yaml-config/compute/forbidden_key (Forbidden)...");
        const response403 = await fastify.inject({
            method: 'GET',
            url: '/healthz/admin/app-yaml-config/compute/forbidden_key'
        });

        if (response403.statusCode !== 403) {
            console.error(`FAILED: Expected 403, got ${response403.statusCode}`);
            process.exit(1);
        }

        console.log("SUCCESS: 403 handling verified.");

        // Test list providers
        console.log("Testing /healthz/admin/app-yaml-config/providers...");
        const responseList = await fastify.inject({
            method: 'GET',
            url: '/healthz/admin/app-yaml-config/providers'
        });

        if (responseList.statusCode !== 200) {
            console.error(`FAILED: Status ${responseList.statusCode}, Body: ${responseList.payload}`);
            process.exit(1);
        }

        const providers = JSON.parse(responseList.payload);
        console.log(`SUCCESS: Got providers list: ${JSON.stringify(providers)}`);
        if (!Array.isArray(providers)) {
            console.error("FAILED: Response is not an array");
            process.exit(1);
        }

        process.exit(0);

    } catch (err) {
        console.error(`ERROR: ${err.message}`);
        process.exit(1);
    }
}

run();
