import fs from 'fs';
import path from 'path';
import dotenv from 'dotenv';
import { LoadResult } from './domain.js';
import { glob } from 'glob';

export type ComputedDefinition = (store: EnvStore) => any;
export type ComputedRegistry = Record<string, ComputedDefinition>;

export type Base64FileParser = (store: EnvStore) => any;
export type Base64FileParserRegistry = Record<string, Base64FileParser>;

export class EnvStore {
    private static instance: EnvStore;
    private store: Map<string, string> = new Map();
    private loadedFiles: string[] = [];
    private _isInitialized: boolean = false;

    // Computed support
    private computedDefinitions: ComputedRegistry = {};
    private computedCache: Map<string, any> = new Map();

    // Base64 file parsers support
    private base64FileParsers: Base64FileParserRegistry = {};

    private constructor() { }

    public static getInstance(): EnvStore {
        if (!EnvStore.instance) {
            EnvStore.instance = new EnvStore();
        }
        return EnvStore.instance;
    }

    public isInitialized(): boolean {
        return this._isInitialized;
    }

    /**
     * Loads environment variables from a file or directory.
     * @param location Path to file or directory
     * @param pattern Glob pattern for directory loading
     * @param override Whether to override existing variables
     * @param computedDefinitions Registry of computed value definitions
     * @param base64FileParsers Registry of base64 file parsers
     */
    public load(
        location: string,
        pattern: string = '.env*',
        override: boolean = false,
        computedDefinitions: ComputedRegistry = {},
        base64FileParsers: Base64FileParserRegistry = {}
    ): LoadResult {
        const result: LoadResult = { loaded: [], errors: [] };

        // Register new computed definitions
        this.computedDefinitions = { ...this.computedDefinitions, ...computedDefinitions };

        // Register new base64 file parsers
        this.base64FileParsers = { ...this.base64FileParsers, ...base64FileParsers };

        let filesToProcess: string[] = [];

        try {
            if (fs.existsSync(location)) {
                const stat = fs.statSync(location);
                if (stat.isFile()) {
                    filesToProcess.push(location);
                } else if (stat.isDirectory()) {
                    const searchPath = path.join(location, pattern);
                    // Use glob sync for simplicity in this MVP, assumed safe for config loading
                    const files = glob.sync(searchPath);
                    filesToProcess = files.sort();
                } else {
                    result.errors.push({ file: location, error: 'Location is not a file or directory' });
                }
            } else {
                result.errors.push({ file: location, error: 'Location not found' });
            }

            for (const filePath of filesToProcess) {
                try {
                    const fileContent = fs.readFileSync(filePath);
                    const parsed = dotenv.parse(fileContent);

                    for (const [key, value] of Object.entries(parsed)) {
                        const existsInStore = this.store.has(key);
                        const existsInProcess = process.env[key] !== undefined;

                        if (override || !existsInStore) {
                            this.store.set(key, value);
                        }

                        // JS Spec: process.env takes precedence mostly, but if override=true we might want to push?
                        // "override=true overwrites all" impl:
                        if (override || !existsInProcess) {
                            process.env[key] = value;
                        }
                    }

                    this.loadedFiles.push(filePath);
                    result.loaded.push(filePath);
                } catch (error: any) {
                    result.errors.push({ file: filePath, error: error.message });
                }
            }

            // Clear cache on new load to ensure consistency if env vars changed
            this.computedCache.clear();

            // Process base64 file parsers after env files are loaded
            this.processBase64FileParsers(result, override);

            this._isInitialized = true;
        } catch (e: any) {
            result.errors.push({ file: location, error: e.message });
        }

        return result;
    }

    /**
     * Process registered base64 file parsers.
     * Each parser returns data that gets flattened and merged into the store.
     */
    private processBase64FileParsers(result: LoadResult, override: boolean): void {
        for (const [prefix, parser] of Object.entries(this.base64FileParsers)) {
            try {
                const parsed = parser(this);

                if (parsed === null || parsed === undefined) {
                    continue;
                }

                // If parsed result is an object, flatten it with prefix
                if (typeof parsed === 'object' && !Array.isArray(parsed)) {
                    const flattened = this.flattenObject(parsed, prefix);

                    for (const [key, value] of Object.entries(flattened)) {
                        const existsInStore = this.store.has(key);
                        const existsInProcess = process.env[key] !== undefined;

                        if (override || !existsInStore) {
                            this.store.set(key, value);
                        }

                        if (override || !existsInProcess) {
                            process.env[key] = value;
                        }
                    }

                    result.loaded.push(`base64:${prefix}`);
                } else {
                    // For non-object values, store directly with prefix as key
                    const key = prefix;
                    const value = String(parsed);

                    if (override || !this.store.has(key)) {
                        this.store.set(key, value);
                    }

                    if (override || process.env[key] === undefined) {
                        process.env[key] = value;
                    }

                    result.loaded.push(`base64:${prefix}`);
                }
            } catch (error: any) {
                result.errors.push({ file: `base64:${prefix}`, error: error.message });
            }
        }
    }

    /**
     * Flatten a nested object into a flat key-value map.
     * Keys are uppercased and joined with underscores.
     * Example: { database: { host: "localhost" } } => { DATABASE_HOST: "localhost" }
     */
    private flattenObject(
        obj: Record<string, any>,
        prefix: string = ''
    ): Record<string, string> {
        const result: Record<string, string> = {};

        for (const [key, value] of Object.entries(obj)) {
            const newKey = prefix
                ? `${prefix}_${key}`.toUpperCase()
                : key.toUpperCase();

            if (value === null || value === undefined) {
                // Skip null/undefined values
                continue;
            } else if (typeof value === 'object' && !Array.isArray(value)) {
                // Recursively flatten nested objects
                const nested = this.flattenObject(value, newKey);
                Object.assign(result, nested);
            } else if (Array.isArray(value)) {
                // Handle arrays by indexing
                value.forEach((item, index) => {
                    const arrayKey = `${newKey}_${index}`;
                    if (typeof item === 'object' && item !== null) {
                        const nested = this.flattenObject(item, arrayKey);
                        Object.assign(result, nested);
                    } else {
                        result[arrayKey] = String(item);
                    }
                });
            } else {
                // Convert primitive values to strings
                result[newKey] = String(value);
            }
        }

        return result;
    }

    public get(key: string): string | undefined {
        // Spec: "Check process.env first, Fall back to internal Map"
        return process.env[key] ?? this.store.get(key);
    }

    public getOrThrow(key: string): string {
        const val = this.get(key);
        if (val === undefined) {
            throw new Error(`Environment variable '${key}' not found`);
        }
        return val;
    }

    /**
     * Computed values support.
     * Retrives a computed value by key, calculating it if not already cached.
     */
    public getComputed<T = any>(key: string): T {
        if (this.computedCache.has(key)) {
            return this.computedCache.get(key);
        }

        const dev = this.computedDefinitions[key];
        if (!dev) {
            throw new Error(`Computed value '${key}' not defined`);
        }

        const value = dev(this);
        this.computedCache.set(key, value);
        return value;
    }

    public getAll(): Record<string, string> {
        // Merge internal with process.env, process.env winning
        const all: Record<string, string | undefined> = {};
        for (const [k, v] of this.store) {
            all[k] = v;
        }
        return { ...all, ...process.env } as Record<string, string>;
    }

    public getLoadResult(): { loadedFiles: string[], storeSize: number } {
        return {
            loadedFiles: [...this.loadedFiles],
            storeSize: this.store.size
        };
    }

    public reset(): void {
        this.store.clear();
        this.loadedFiles = [];
        this.computedDefinitions = {};
        this.computedCache.clear();
        this.base64FileParsers = {};
        this._isInitialized = false;
    }

    public static async onStartup(
        location: string,
        pattern: string = '.env*',
        override: boolean = false,
        computedDefinitions: ComputedRegistry = {},
        base64FileParsers: Base64FileParserRegistry = {}
    ): Promise<EnvStore> {
        const instance = EnvStore.getInstance();
        instance.load(location, pattern, override, computedDefinitions, base64FileParsers);
        return instance;
    }
}

export const env = EnvStore.getInstance();
