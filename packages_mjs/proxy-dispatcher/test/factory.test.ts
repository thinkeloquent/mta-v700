import { ProxyDispatcherFactory } from "../src/factory";
import { FactoryConfig } from "../src/types";

describe("ProxyDispatcherFactory", () => {
    it("should create a client with defaults", () => {
        const factory = new ProxyDispatcherFactory();
        const result = factory.getProxyDispatcher();
        expect(result.client).toBeDefined();
        // Undici Agent doesn't expose clean public props to verify easily without mocking
        // But we can check our returned config
        expect(result.config.verifySsl).toBe(true);
    });

    it("should disable SSL", () => {
        const factory = new ProxyDispatcherFactory();
        const result = factory.getProxyDispatcher({ disableTls: true });
        expect(result.config.verifySsl).toBe(false);
    });

    it("should using proxy URL from config", () => {
        const config: FactoryConfig = {
            proxyUrl: "http://override",
            proxyUrls: {}
        };
        const factory = new ProxyDispatcherFactory(config);
        const result = factory.getProxyDispatcher();
        expect(result.config.proxyUrl).toBe("http://override");
    });
});
