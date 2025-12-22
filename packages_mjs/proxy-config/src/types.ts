/**
 * Data models for proxy configuration.
 */
import { z } from "zod";

export const AgentProxyConfigSchema = z.object({
    httpProxy: z.string().nullable().optional(),
    httpsProxy: z.string().nullable().optional(),
});

export type AgentProxyConfig = z.infer<typeof AgentProxyConfigSchema>;

export const NetworkConfigSchema = z.object({
    defaultEnvironment: z.string().nullable().default("dev"),
    proxyUrls: z.record(z.string().nullable()).default({}),
    caBundle: z.string().nullable().optional(),
    cert: z.string().nullable().optional(),
    certVerify: z.boolean().default(false),
    agentProxy: AgentProxyConfigSchema.nullable().optional(),
});

export type NetworkConfig = z.infer<typeof NetworkConfigSchema>;

export function parseNetworkConfig(config: unknown): NetworkConfig {
    return NetworkConfigSchema.parse(config);
}

export function validateNetworkConfig(config: unknown): boolean {
    return NetworkConfigSchema.safeParse(config).success;
}
