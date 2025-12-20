import { describe, it, expect } from "vitest";
import { ElasticsearchConfig, getElasticsearchClient, VENDOR_ON_PREM } from "../src";

describe("db-connection-elasticsearch", () => {
    it("should export main classes", () => {
        expect(ElasticsearchConfig).toBeDefined();
        expect(getElasticsearchClient).toBeDefined();
        expect(VENDOR_ON_PREM).toBe("on-prem");
    });

    it("should support overrides", () => {
        // Explicitly override env vars
        const config = new ElasticsearchConfig({
            vendorType: VENDOR_ON_PREM,
            host: "localhost",
            port: 9200
        });
        expect(config.options.vendorType).toBe(VENDOR_ON_PREM);
        expect(config.options.port).toBe(9200);
    });

    it("should respect env vars or defaults", () => {
        const config = new ElasticsearchConfig({});
        if (process.env.ELASTIC_DB_HOST) {
            // If env var set, expect it to be used
            expect(config.options.host).toBeDefined();
        } else {
            expect(config.options.vendorType).toBe(VENDOR_ON_PREM);
        }
    });
});
