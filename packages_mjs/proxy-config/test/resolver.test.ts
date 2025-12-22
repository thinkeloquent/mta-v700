import { resolveProxyUrl, NetworkConfig } from "../src";

describe("resolveProxyUrl", () => {
    const originalEnv = process.env;

    beforeEach(() => {
        jest.resetModules();
        process.env = { ...originalEnv };
    });

    afterAll(() => {
        process.env = originalEnv;
    });

    it("should return null when override is false", () => {
        expect(resolveProxyUrl(null, false)).toBeNull();
    });

    it("should return override string", () => {
        expect(resolveProxyUrl(null, "http://override")).toBe("http://override");
    });

    it("should use agent proxy over env config", () => {
        const config: NetworkConfig = {
            defaultEnvironment: "dev",
            proxyUrls: { dev: "http://dev-proxy" },
            agentProxy: {
                httpsProxy: "http://agent-https",
            },
            certVerify: false,
        };
        expect(resolveProxyUrl(config)).toBe("http://agent-https");
    });

    it("should use environment specific proxy", () => {
        const config: NetworkConfig = {
            defaultEnvironment: "stage",
            proxyUrls: { stage: "http://stage-proxy" },
            certVerify: false,
        };
        expect(resolveProxyUrl(config)).toBe("http://stage-proxy");
    });

    it("should fall back to env vars", () => {
        process.env.PROXY_URL = "http://env-proxy";
        expect(resolveProxyUrl()).toBe("http://env-proxy");
    });
});
