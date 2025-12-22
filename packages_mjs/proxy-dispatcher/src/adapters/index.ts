/**
 * Adapter registry.
 */
import { BaseAdapter } from "./base";
import { UndiciAdapter } from "./adapter-undici";

const adapters: Record<string, new () => BaseAdapter> = {};

export function registerAdapter(name: string, adapterClass: new () => BaseAdapter): void {
    adapters[name] = adapterClass;
}

export function getAdapter(name: string): BaseAdapter {
    const AdapterClass = adapters[name];
    if (!AdapterClass) {
        throw new Error(`Adapter '${name}' not found. Available: ${Object.keys(adapters).join(", ")}`);
    }
    return new AdapterClass();
}

// Register default
registerAdapter("undici", UndiciAdapter);

export * from "./base";
export * from "./adapter-undici";
