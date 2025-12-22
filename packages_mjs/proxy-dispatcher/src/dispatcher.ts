/**
 * Convenience functions.
 */
import { ProxyDispatcherFactory } from "./factory";
import { DispatcherResult, FactoryConfig } from "./types";

const defaultFactory = new ProxyDispatcherFactory();

export function getProxyDispatcher(options?: {
    environment?: string;
    disableTls?: boolean;
    timeout?: number;
}): DispatcherResult {
    return defaultFactory.getProxyDispatcher(options);
}

export function createProxyDispatcherFactory(config?: FactoryConfig, adapter?: string): ProxyDispatcherFactory {
    return new ProxyDispatcherFactory(config, adapter);
}
