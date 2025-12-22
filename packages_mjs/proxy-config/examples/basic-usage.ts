/**
 * Basic usage examples for proxy-config package.
 *
 * This package provides proxy URL resolution logic with 8-level precedence.
 */
import { resolveProxyUrl, NetworkConfig, AgentProxyConfig } from "@internal/proxy-config";

// =============================================================================
// Example 1: Simple resolution from environment variables
// =============================================================================
/**
 * When no config is provided, falls back to environment variables:
 * 1. PROXY_URL
 * 2. HTTPS_PROXY
 * 3. HTTP_PROXY
 */
function example1_envVarFallback(): void {
    // Set environment variables (in real app, these come from .env or cloud config)
    process.env.HTTPS_PROXY = "http://corporate-proxy:8080";

    const proxyUrl = resolveProxyUrl();
    console.log("Example 1 - ENV fallback:", proxyUrl);
    // Output: "http://corporate-proxy:8080"

    // Cleanup
    delete process.env.HTTPS_PROXY;
}

// =============================================================================
// Example 2: Environment-specific proxy URLs
// =============================================================================
/**
 * Configure different proxy URLs per environment (dev, staging, prod).
 * The `defaultEnvironment` determines which one is selected.
 */
function example2_environmentSpecific(): void {
    const networkConfig: NetworkConfig = {
        defaultEnvironment: "prod",
        proxyUrls: {
            dev: "http://dev-proxy.internal:3128",
            staging: "http://staging-proxy.internal:3128",
            prod: "http://prod-proxy.internal:3128"
        }
    };

    const proxyUrl = resolveProxyUrl(networkConfig);
    console.log("Example 2 - Environment-specific:", proxyUrl);
    // Output: "http://prod-proxy.internal:3128"
}

// =============================================================================
// Example 3: Agent proxy configuration (highest priority in config)
// =============================================================================
/**
 * Agent proxy settings take precedence over environment-specific URLs.
 * Useful for per-request or per-service overrides.
 */
function example3_agentProxy(): void {
    const networkConfig: NetworkConfig = {
        defaultEnvironment: "prod",
        proxyUrls: {
            prod: "http://prod-proxy:3128"
        },
        agentProxy: {
            httpsProxy: "http://special-https-proxy:8080",
            httpProxy: "http://special-http-proxy:8080"
        }
    };

    const proxyUrl = resolveProxyUrl(networkConfig);
    console.log("Example 3 - Agent proxy:", proxyUrl);
    // Output: "http://special-https-proxy:8080" (httpsProxy takes precedence)
}

// =============================================================================
// Example 4: Explicit override (highest priority)
// =============================================================================
/**
 * The `proxyUrlOverride` parameter takes absolute precedence.
 * Use this for one-off requests or testing.
 */
function example4_explicitOverride(): void {
    const networkConfig: NetworkConfig = {
        defaultEnvironment: "prod",
        proxyUrls: {
            prod: "http://prod-proxy:3128"
        }
    };

    // Override with explicit URL
    const proxyUrl = resolveProxyUrl(networkConfig, "http://test-proxy:9999");
    console.log("Example 4 - Explicit override:", proxyUrl);
    // Output: "http://test-proxy:9999"
}

// =============================================================================
// Example 5: Explicitly disable proxy
// =============================================================================
/**
 * Pass `false` as override to explicitly disable proxy.
 * Useful for local development or direct connections.
 */
function example5_disableProxy(): void {
    process.env.HTTPS_PROXY = "http://corporate-proxy:8080";

    const networkConfig: NetworkConfig = {
        defaultEnvironment: "prod",
        proxyUrls: {
            prod: "http://prod-proxy:3128"
        }
    };

    // Explicitly disable proxy
    const proxyUrl = resolveProxyUrl(networkConfig, false);
    console.log("Example 5 - Disabled proxy:", proxyUrl);
    // Output: null

    // Cleanup
    delete process.env.HTTPS_PROXY;
}

// =============================================================================
// Example 6: Full precedence demonstration
// =============================================================================
/**
 * Demonstrates the full 8-level precedence hierarchy.
 *
 * Resolution order:
 * 1. proxyUrlOverride = false  → null (disabled)
 * 2. proxyUrlOverride = string → use override
 * 3. agentProxy.httpsProxy     → agent HTTPS
 * 4. agentProxy.httpProxy      → agent HTTP
 * 5. proxyUrls[environment]    → environment-specific
 * 6. PROXY_URL env var         → generic env
 * 7. HTTPS_PROXY env var       → HTTPS env
 * 8. HTTP_PROXY env var        → HTTP env (lowest)
 */
function example6_fullPrecedence(): void {
    // Set all possible sources
    process.env.HTTP_PROXY = "http://env-http:8080";
    process.env.HTTPS_PROXY = "http://env-https:8080";
    process.env.PROXY_URL = "http://env-proxy:8080";

    const fullConfig: NetworkConfig = {
        defaultEnvironment: "prod",
        proxyUrls: {
            prod: "http://config-prod:3128"
        },
        agentProxy: {
            httpProxy: "http://agent-http:3128",
            httpsProxy: "http://agent-https:3128"
        }
    };

    // Each level overrides the ones below it
    console.log("\nExample 6 - Full precedence:");
    console.log("1. Override false:", resolveProxyUrl(fullConfig, false));
    console.log("2. Override string:", resolveProxyUrl(fullConfig, "http://explicit:9999"));
    console.log("3. Agent HTTPS:", resolveProxyUrl(fullConfig));
    console.log("4. Agent HTTP:", resolveProxyUrl({
        ...fullConfig,
        agentProxy: { httpProxy: "http://agent-http:3128" }
    }));
    console.log("5. Config env:", resolveProxyUrl({
        defaultEnvironment: "prod",
        proxyUrls: { prod: "http://config-prod:3128" }
    }));
    console.log("6. PROXY_URL:", resolveProxyUrl());

    delete process.env.PROXY_URL;
    console.log("7. HTTPS_PROXY:", resolveProxyUrl());

    delete process.env.HTTPS_PROXY;
    console.log("8. HTTP_PROXY:", resolveProxyUrl());

    // Cleanup
    delete process.env.HTTP_PROXY;
}

// =============================================================================
// Example 7: Integration with app-yaml-config (conceptual)
// =============================================================================
/**
 * Shows how proxy-config integrates with app-yaml-config.
 * The YAML global.network section maps directly to NetworkConfig.
 */
function example7_yamlIntegration(): void {
    // Simulated config loaded from app.yaml:
    // global:
    //   network:
    //     default_environment: "dev"
    //     proxy_urls:
    //       dev: "http://dev-proxy:3128"
    //       prod: "http://prod-proxy:3128"
    //     agent_proxy:
    //       https_proxy: "http://special:8080"

    const yamlNetworkSection = {
        default_environment: "dev",
        proxy_urls: {
            dev: "http://dev-proxy:3128",
            prod: "http://prod-proxy:3128"
        },
        agent_proxy: {
            https_proxy: "http://special:8080"
        }
    };

    // Map YAML snake_case to NetworkConfig camelCase
    const networkConfig: NetworkConfig = {
        defaultEnvironment: yamlNetworkSection.default_environment,
        proxyUrls: yamlNetworkSection.proxy_urls,
        agentProxy: yamlNetworkSection.agent_proxy ? {
            httpsProxy: yamlNetworkSection.agent_proxy.https_proxy,
            httpProxy: yamlNetworkSection.agent_proxy.http_proxy
        } : undefined
    };

    const proxyUrl = resolveProxyUrl(networkConfig);
    console.log("Example 7 - YAML integration:", proxyUrl);
    // Output: "http://special:8080" (agent_proxy takes precedence)
}

// =============================================================================
// Run all examples
// =============================================================================
function main(): void {
    console.log("=== proxy-config Examples ===\n");

    example1_envVarFallback();
    example2_environmentSpecific();
    example3_agentProxy();
    example4_explicitOverride();
    example5_disableProxy();
    example6_fullPrecedence();
    example7_yamlIntegration();

    console.log("\n=== Examples Complete ===");
}

main();
