/**
 * Basic usage examples for proxy-dispatcher package.
 *
 * This package provides HTTP client factory with proxy configuration.
 */
import {
    ProxyDispatcherFactory,
    FactoryConfig,
    getProxyDispatcher,
    createProxyDispatcherFactory
} from "@internal/proxy-dispatcher";

// =============================================================================
// Example 1: Create factory with environment-specific proxy URLs
// =============================================================================
/**
 * >>> factory = ProxyDispatcherFactory(
 * ...     config=FactoryConfig(
 * ...         proxy_urls=ProxyUrlConfig(
 * ...             PROD="http://proxy.company.com:8080",
 * ...             QA="http://qa-proxy.company.com:8080",
 * ...         ),
 * ...     ),
 * ... )
 * >>> result = factory.get_proxy_dispatcher()
 * >>> async with result.client as client:
 * ...     response = await client.get("https://api.example.com")
 */
async function example1_factoryWithEnvProxy(): Promise<void> {
    const factory = new ProxyDispatcherFactory({
        proxyUrls: {
            PROD: "http://proxy.company.com:8080",
            QA: "http://qa-proxy.company.com:8080",
            dev: "http://dev-proxy:3128"
        },
        defaultEnvironment: "dev"
    });

    const result = factory.getProxyDispatcher();

    console.log("Example 1 - Factory with env proxy:");
    console.log("  proxyUrl:", result.config.proxyUrl);
    console.log("  verifySsl:", result.config.verifySsl);
    console.log("  timeout:", result.config.timeout);

    // Use the client (undici Agent)
    // const response = await fetch("https://api.example.com", {
    //     dispatcher: result.client
    // });
}

// =============================================================================
// Example 2: Get request kwargs for direct HTTP calls
// =============================================================================
/**
 * >>> factory = ProxyDispatcherFactory(...)
 * >>> kwargs = factory.get_request_kwargs("QA")
 * >>> response = httpx.post("https://api.example.com", json=data, **kwargs)
 */
function example2_getRequestKwargs(): void {
    const factory = new ProxyDispatcherFactory({
        proxyUrls: {
            QA: "http://qa-proxy:8080",
            PROD: "http://prod-proxy:8080"
        },
        defaultEnvironment: "QA",
        certVerify: true
    });

    const options = factory.getDispatcherOptions({ timeout: 30000 });

    console.log("\nExample 2 - Get request kwargs:");
    console.log("  options:", JSON.stringify(options, null, 2));

    // Use with fetch or undici request
    // const response = await request("https://api.example.com", {
    //     method: "POST",
    //     body: JSON.stringify(data),
    //     ...options
    // });
}

// =============================================================================
// Example 3: Convenience function for quick scripts
// =============================================================================
/**
 * >>> factory = create_proxy_dispatcher_factory(
 * ...     config=FactoryConfig(
 * ...         proxy_urls=ProxyUrlConfig(PROD="http://proxy:8080"),
 * ...     ),
 * ... )
 * >>> result = factory.get_proxy_dispatcher()
 */
function example3_convenienceFunction(): void {
    // Using the convenience factory creator
    const factory = createProxyDispatcherFactory({
        proxyUrls: {
            PROD: "http://proxy:8080"
        }
    });

    const result = factory.getProxyDispatcher();

    console.log("\nExample 3 - Convenience function:");
    console.log("  proxyUrl:", result.config.proxyUrl);

    // Or use the global convenience function (uses env vars)
    const globalResult = getProxyDispatcher();
    console.log("  globalResult.proxyUrl:", globalResult.config.proxyUrl);
}

// =============================================================================
// Example 4: Environment-specific dispatcher
// =============================================================================
function example4_environmentSpecific(): void {
    const factory = new ProxyDispatcherFactory({
        proxyUrls: {
            dev: "http://dev-proxy:3128",
            staging: "http://staging-proxy:3128",
            prod: "http://prod-proxy:3128"
        }
    });

    // Get dispatcher for specific environment
    const devDispatcher = factory.getDispatcherForEnvironment("dev");
    const prodDispatcher = factory.getDispatcherForEnvironment("prod");

    console.log("\nExample 4 - Environment-specific:");
    console.log("  dev proxy:", devDispatcher.config.proxyUrl);
    console.log("  prod proxy:", prodDispatcher.config.proxyUrl);
}

// =============================================================================
// Example 5: Full configuration with SSL and certificates
// =============================================================================
function example5_fullConfig(): void {
    const factory = new ProxyDispatcherFactory({
        proxyUrls: {
            prod: "http://secure-proxy:8080"
        },
        defaultEnvironment: "prod",
        certVerify: true,
        cert: "/path/to/client-cert.pem",
        caBundle: "/path/to/ca-bundle.crt"
    });

    const result = factory.getProxyDispatcher({
        timeout: 60000,
        disableTls: false
    });

    console.log("\nExample 5 - Full config:");
    console.log("  proxyUrl:", result.config.proxyUrl);
    console.log("  verifySsl:", result.config.verifySsl);
    console.log("  cert:", result.config.cert);
    console.log("  caBundle:", result.config.caBundle);
}

// =============================================================================
// Example 6: Disable proxy explicitly
// =============================================================================
function example6_disableProxy(): void {
    const factory = new ProxyDispatcherFactory({
        proxyUrls: {
            prod: "http://prod-proxy:8080"
        },
        proxyUrl: false  // Explicitly disable
    });

    const result = factory.getProxyDispatcher();

    console.log("\nExample 6 - Disable proxy:");
    console.log("  proxyUrl:", result.config.proxyUrl);  // null
}

// =============================================================================
// Example 7: Override proxy URL
// =============================================================================
function example7_overrideProxy(): void {
    const factory = new ProxyDispatcherFactory({
        proxyUrls: {
            prod: "http://prod-proxy:8080"
        },
        proxyUrl: "http://override-proxy:9999"  // Takes precedence
    });

    const result = factory.getProxyDispatcher();

    console.log("\nExample 7 - Override proxy:");
    console.log("  proxyUrl:", result.config.proxyUrl);  // http://override-proxy:9999
}

// =============================================================================
// Example 8: Integration with Fastify (singleton pattern)
// =============================================================================
function example8_fastifyIntegration(): void {
    // See examples/fastify-app/src/server.ts for full example

    const factoryConfig: FactoryConfig = {
        defaultEnvironment: process.env.APP_ENV || "dev",
        proxyUrls: {
            dev: "http://dev-proxy:3128",
            prod: "http://prod-proxy:3128"
        }
    };

    // Create singleton factory at app startup
    const factory = new ProxyDispatcherFactory(factoryConfig);

    // In route handlers:
    // const { client, config } = factory.getProxyDispatcher();

    console.log("\nExample 8 - Fastify integration:");
    console.log("  Factory created with config:", Object.keys(factoryConfig));
    console.log("  See examples/fastify-app/ for full integration");
}

// =============================================================================
// Run all examples
// =============================================================================
async function main(): Promise<void> {
    console.log("=== proxy-dispatcher Examples ===\n");

    await example1_factoryWithEnvProxy();
    example2_getRequestKwargs();
    example3_convenienceFunction();
    example4_environmentSpecific();
    example5_fullConfig();
    example6_disableProxy();
    example7_overrideProxy();
    example8_fastifyIntegration();

    console.log("\n=== Examples Complete ===");
}

main().catch(console.error);
