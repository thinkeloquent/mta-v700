/**
 * Data models for proxy dispatcher.
 */
import { z } from "zod";
import { AgentProxyConfigSchema } from "@internal/proxy-config";

// Resolved proxy configuration for HTTP clients
export const ProxyConfigSchema = z.object({
    proxyUrl: z.string().nullable().optional(),
    verifySsl: z.boolean().default(false),
    timeout: z.number().default(30000), // ms
    trustEnv: z.boolean().default(false),
    cert: z.string().nullable().optional(),
    caBundle: z.string().nullable().optional(),
});

export type ProxyConfig = z.infer<typeof ProxyConfigSchema>;

// Configuration for ProxyDispatcherFactory
export const FactoryConfigSchema = z.object({
    proxyUrls: z.record(z.string().nullable()).optional(),
    proxyUrl: z.union([z.string(), z.boolean()]).nullable().optional(),
    agentProxy: AgentProxyConfigSchema.nullable().optional(),
    defaultEnvironment: z.string().nullable().optional(),
    cert: z.string().nullable().optional(),
    caBundle: z.string().nullable().optional(),
    certVerify: z.boolean().nullable().optional(),
});

export type FactoryConfig = z.infer<typeof FactoryConfigSchema>;

// Result wrapper
export interface DispatcherResult {
    client: any; // e.g. undici.Dispatcher or similar
    config: ProxyConfig;
    proxyDict: Record<string, any>; // Options passed to client
}
