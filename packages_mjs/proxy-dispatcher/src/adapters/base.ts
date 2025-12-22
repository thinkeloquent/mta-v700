/**
 * Abstract base adapter for HTTP libraries.
 */
import { DispatcherResult, ProxyConfig } from "../types";

export abstract class BaseAdapter {
    /** Name of the adapter */
    abstract get name(): string;

    /** Whether the adapter supports synchronous clients */
    abstract supportsSync(): boolean;

    /** Whether the adapter supports asynchronous clients */
    abstract supportsAsync(): boolean;

    /** Create a configured client (Agent for undici) */
    abstract createClient(config: ProxyConfig): DispatcherResult;

    /** Get dispatcher options */
    abstract getDispatcherOptions(config: ProxyConfig): Record<string, any>;
}
