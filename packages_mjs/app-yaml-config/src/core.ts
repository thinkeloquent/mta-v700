/**
 * Core business logic for AppYamlConfig.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import merge from 'lodash.merge';
// Note: lodash.merge merges arrays by index/concatenation logic depending on version/config?
// But standard lodash.merge merges objects recursive, and treats arrays as objects where indices are keys.
// Wait, spec requirement: "Arrays replaced (not concatenated)"
// lodash.merge DEFAULT behavior is to merge indices (concat-like or override-by-index).
// This might NOT match Python "replace".
// We might need a custom merge or specific settings.
// Let's implement a custom deep merge or check lodash behavior carefully. 
// Actually for simplicity in this MVP to match "replace arrays", we can write a simple deep merge,
// or use lodash.mergeWith

import {
    LoadResult,
    ComputedDefinition,
    ComputedRegistry,
    InitOptions
} from './domain';

import {
    ValidationError,
    ConfigNotInitializedError,
    ComputedKeyNotFoundError,
    CircularDependencyError
} from './validators';

export class AppYamlConfig {
    private static instance: AppYamlConfig | null = null;
    private initialized: boolean = false;
    private data: Record<string, any> = {};
    private computedDefinitions: ComputedRegistry = {};
    private computedCache: Map<string, any> = new Map();
    private loadResult: LoadResult | null = null;
    private computingStack: string[] = [];

    private constructor() { }

    public static getInstance(): AppYamlConfig {
        if (!AppYamlConfig.instance) {
            AppYamlConfig.instance = new AppYamlConfig();
        }
        // Strict singleton access check per parity with Python
        if (!AppYamlConfig.instance.initialized) {
            throw new ConfigNotInitializedError();
        }
        return AppYamlConfig.instance;
    }

    // Creating a private accessor for test reset
    public static _resetForTesting(): void {
        const inst = AppYamlConfig.instance || new AppYamlConfig();
        inst.initialized = false;
        inst.data = {};
        inst.computedDefinitions = {};
        inst.computedCache.clear();
        inst.loadResult = null;
        inst.computingStack = [];
        AppYamlConfig.instance = inst;
    }

    public static async initialize(options: InitOptions): Promise<AppYamlConfig> {
        let instance = AppYamlConfig.instance;
        if (!instance) {
            instance = new AppYamlConfig();
            AppYamlConfig.instance = instance;
        }

        if (instance.initialized) {
            console.warn("AppYamlConfig already initialized. Returning existing instance.");
            return instance;
        }

        const { files, configDir, appEnv, computedDefinitions } = options;
        const env = (appEnv || process.env.APP_ENV || 'dev').toLowerCase();

        const result: LoadResult = {
            filesLoaded: [],
            errors: [],
            appEnv: env,
            mergeOrder: []
        };

        let mergedData: Record<string, any> = {};

        // Resolve files
        const filesToLoad: string[] = [];
        for (const fileRaw of files) {
            // 1. Substitute {APP_ENV}
            const resolvedName = fileRaw.replace("{APP_ENV}", env);

            // 2. Resolve relative
            let resolvedPath = resolvedName;
            if (configDir && !path.isAbsolute(resolvedName)) {
                resolvedPath = path.join(configDir, resolvedName);
            } else {
                resolvedPath = path.resolve(resolvedName);
            }

            // 3. Env specific override ({name}.{env}.yaml)
            const ext = path.extname(resolvedPath);
            const base = resolvedPath.substring(0, resolvedPath.length - ext.length);
            const envSpecificPath = `${base}.${env}${ext}`;

            let finalPath = resolvedPath;
            if (fs.existsSync(envSpecificPath)) {
                finalPath = envSpecificPath;
            } else if (fs.existsSync(resolvedPath)) {
                finalPath = resolvedPath;
            } else {
                const msg = `Config file not found: ${resolvedPath}`;
                console.error(msg);
                throw new Error(msg); // Fatal
            }

            filesToLoad.push(finalPath);
        }

        // Load and Merge
        for (const filePath of filesToLoad) {
            try {
                const content = fs.readFileSync(filePath, 'utf8');
                const fileData = yaml.load(content) as Record<string, any> || {};

                // Custom Deep Merge (Array Replacement)
                // using logic comparable to Python
                mergedData = AppYamlConfig.deepMerge(mergedData, fileData);

                result.filesLoaded.push(filePath);
                result.mergeOrder.push(filePath);
            } catch (e: any) {
                const msg = `YAML parsing error in ${filePath}: ${e.message}`;
                console.error(msg);
                throw new ValidationError(msg);
            }
        }

        instance.data = mergedData;
        instance.computedDefinitions = computedDefinitions || {};
        instance.computedCache.clear();
        instance.loadResult = result;
        instance.initialized = true;

        console.log(`AppYamlConfig initialized. Loaded: ${result.filesLoaded.length} files.`);
        return instance;
    }

    private static deepMerge(target: Record<string, any>, source: Record<string, any>): Record<string, any> {
        for (const key of Object.keys(source)) {
            const val = source[key];
            if (val && typeof val === 'object' && !Array.isArray(val) &&
                target[key] && typeof target[key] === 'object' && !Array.isArray(target[key])) {
                AppYamlConfig.deepMerge(target[key], val);
            } else {
                target[key] = val; // Replace primitives and arrays
            }
        }
        return target;
    }

    public get<T = any>(key: string, defaultValue?: T): T | undefined {
        return (this.data[key] !== undefined) ? this.data[key] : defaultValue;
    }

    public getNested<T = any>(keys: string[], defaultValue?: T): T | undefined {
        let current = this.data;
        for (const key of keys) {
            if (current && typeof current === 'object' && key in current) {
                current = current[key];
            } else {
                return defaultValue;
            }
        }
        return current as T;
    }

    public getComputed<T = any>(key: string): T {
        if (!this.initialized) {
            throw new ConfigNotInitializedError();
        }

        if (!(key in this.computedDefinitions)) {
            throw new ComputedKeyNotFoundError(key);
        }

        if (this.computedCache.has(key)) {
            return this.computedCache.get(key);
        }

        if (this.computingStack.includes(key)) {
            throw new CircularDependencyError(key, this.computingStack);
        }

        this.computingStack.push(key);
        try {
            const def = this.computedDefinitions[key];
            const val = def(this);
            this.computedCache.set(key, val);
            return val;
        } finally {
            this.computingStack.pop();
        }
    }

    public getAll(): Record<string, any> {
        // Deep copy to prevent mutation
        return JSON.parse(JSON.stringify(this.data));
    }

    public isInitialized(): boolean {
        return this.initialized;
    }

    public getLoadResult(): LoadResult | null {
        return this.loadResult;
    }
}
