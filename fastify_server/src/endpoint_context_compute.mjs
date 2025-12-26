/**
 * Endpoint Context Compute Registry.
 *
 * This file is the entry point for registering custom compute functions for
 * context-based template resolution via overwrite_from_context.
 *
 * Unlike endpoint_auth_compute.mjs (for auth token resolution), this file
 * handles dynamic value resolution in YAML config templates using {{fn:name}} syntax.
 *
 * Usage:
 *   import { ContextComputeRegistry } from '@internal/yaml-config-factory';
 *
 *   ContextComputeRegistry.registerStartup('my_startup_resolver', (context) => {
 *     // context = {env, app, config, request}
 *     // Runs once when context is built
 *     return context.env.MY_VALUE || 'default';
 *   });
 *
 *   ContextComputeRegistry.registerRequest('my_request_resolver', (context, request) => {
 *     // context = {env, app, config, request}
 *     // request = Fastify Request object
 *     // Runs per request when template is resolved
 *     return request.headers['x-custom-header'] || 'fallback';
 *   });
 *
 * YAML usage:
 *   overwrite_from_context:
 *     my_value: "{{fn:my_startup_resolver}}"
 *     custom_header: "{{fn:my_request_resolver}}"
 */

import { ContextComputeRegistry } from "@internal/yaml-config-factory";
import { randomUUID } from "crypto";

// =============================================================================
// Startup Resolvers (run when context is built at startup)
// =============================================================================

ContextComputeRegistry.registerStartup("get_build_info", (context) => {
  /**
   * Get build information from environment or config.
   */
  return {
    build_id: context.env.BUILD_ID || "dev-local",
    build_time: context.env.BUILD_TIME || new Date().toISOString(),
    git_sha: context.env.GIT_SHA || "unknown",
  };
});

ContextComputeRegistry.registerStartup("get_service_name", (context) => {
  /**
   * Get service name from app config.
   */
  return context.app?.name || "mta-server";
});

// =============================================================================
// Request Resolvers (run per-request when template is resolved)
// =============================================================================

ContextComputeRegistry.registerRequest(
  "compute_gemini_v2_token",
  (context, request) => {
    /**
     * Compute dynamic token for gemini_openai_v2 provider.
     *
     * Priority:
     * 1. x-gemini-token header from request
     * 2. GEMINI_API_KEY from environment
     * 3. Fallback empty string
     */
    if (request) {
      // Check for token in request header
      const token = request.headers["x-gemini-token"];
      if (token) {
        return token;
      }
    }

    // Fall back to environment variable
    return context.env.GEMINI_API_KEY || "";
  }
);

ContextComputeRegistry.registerRequest(
  "compute_request_id",
  (context, request) => {
    /**
     * Get or generate a request ID for tracing.
     *
     * Uses x-request-id header if present, otherwise generates a new UUID.
     */
    if (request) {
      const requestId = request.headers["x-request-id"];
      if (requestId) {
        return requestId;
      }
    }

    return randomUUID();
  }
);

ContextComputeRegistry.registerRequest(
  "compute_tenant_id",
  (context, request) => {
    /**
     * Extract tenant ID from request headers or query params.
     */
    if (request) {
      // Try header first
      const tenantIdHeader = request.headers["x-tenant-id"];
      if (tenantIdHeader) {
        return tenantIdHeader;
      }

      // Then query params
      const tenantIdQuery = request.query?.tenant_id;
      if (tenantIdQuery) {
        return tenantIdQuery;
      }
    }

    return "default";
  }
);

ContextComputeRegistry.registerRequest(
  "compute_user_agent",
  (context, request) => {
    /**
     * Build a custom user agent string including app version.
     */
    const appName = context.app?.name || "MTA-Server";
    const appVersion = context.app?.version || "0.0.0";

    const baseUA = `${appName}/${appVersion}`;

    if (request) {
      const clientUA = request.headers["user-agent"];
      if (clientUA) {
        return `${baseUA} (via ${clientUA})`;
      }
    }

    return baseUA;
  }
);
