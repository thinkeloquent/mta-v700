/**
 * Adapter for undici library.
 */
import { Agent, ProxyAgent } from "undici";
import { BaseAdapter } from "./base";
import { DispatcherResult, ProxyConfig } from "../types";

export class UndiciAdapter extends BaseAdapter {
    get name(): string {
        return "undici";
    }

    supportsSync(): boolean {
        return false;
    }

    supportsAsync(): boolean {
        return true;
    }

    getDispatcherOptions(config: ProxyConfig): Record<string, any> {
        // Keep alive settings similar to existing agents.mts
        const options: any = {
            connect: {
                timeout: config.timeout,
                rejectUnauthorized: config.verifySsl,
            },
            pipelining: 0,
        };

        if (config.cert) {
            options.connect.cert = config.cert;
        }

        if (config.caBundle) {
            options.connect.ca = config.caBundle;
        }

        return options;
    }

    createClient(config: ProxyConfig): DispatcherResult {
        const options = this.getDispatcherOptions(config);
        let client: any;

        if (config.proxyUrl) {
            // ProxyAgent logic
            const proxyOptions = {
                uri: config.proxyUrl,
                ...options
            };
            // ProxyAgent in undici handles connection to proxy
            // But authentication and verification happens there
            client = new ProxyAgent(proxyOptions);
        } else {
            // Standard Agent
            client = new Agent(options);
        }

        return {
            client,
            config,
            proxyDict: options,
        };
    }
}
