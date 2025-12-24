/**
 * Endpoint Auth Compute Registry.
 *
 * This file is the entry point for registering custom compute functions for
 * authentication token resolution.
 *
 * Usage:
 *   import { ComputeRegistry } from '@internal/fetch-auth-config';
 *
 *   ComputeRegistry.registerStartup('my_custom_provider', async () => {
 *     // Compute token at startup
 *     return 'my-startup-token';
 *   });
 *
 *   ComputeRegistry.registerRequest('my_request_provider', async (request) => {
 *     // Compute token per request
 *     return request.headers['x-custom-token'];
 *   });
 */

import { ComputeRegistry } from "@internal/fetch-auth-config";

// Startup Compute for Figma (Env var)
ComputeRegistry.registerStartup("figma", async (server) => {
  // Can use server instance here if needed, e.g. server.log.info(...)
  return process.env.FIGMA_TOKEN || "";
});

// Request Compute for Gemini OpenAI (Header)
ComputeRegistry.registerRequest("gemini_openai", async (request) => {
  return process.env.GEMINI_API_KEY || "";
  return request.headers["x-custom-token"] || "dynamic-token-fallback";
});
