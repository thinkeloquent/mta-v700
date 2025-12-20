/**
 * Fastify Hello World Server
 */

import Fastify from "fastify";
import { AppYamlConfig } from "@internal/app-yaml-config";
import "./load_app_env.mjs";
import "./load_app_config.mjs";
import { printRoutes } from "./print_routes.mjs";
import vaultFileRoutes from "./routes/healthz/vault-file.mjs";
import appYamlConfigRoutes from "./routes/healthz/app-yaml-config.mjs";

const fastify = Fastify({
  logger: true,
});

// Root endpoint
fastify.get("/", async (request, reply) => {
  return { message: "Hello World" };
});

// Health check endpoint
fastify.get("/health", async (request, reply) => {
  return { status: "healthy" };
});

// Register healthz routes
fastify.register(vaultFileRoutes);
fastify.register(appYamlConfigRoutes);

// Start server
const start = async () => {
  try {
    const config = AppYamlConfig.getInstance();

    const port =
      process.env.PORT || config.getNested(["server", "port"]) || 8080;
    const host =
      process.env.HOST || config.getNested(["server", "host"]) || "0.0.0.0";

    await fastify.listen({ port, host });
    printRoutes(fastify);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
