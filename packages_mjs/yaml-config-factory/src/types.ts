

import type { AuthConfig } from '@internal/fetch-auth-config';
import type { ProxyResolutionResult } from '@internal/app-yaml-config';

export type ConfigPath = 'providers' | 'services' | 'storages';

export interface NetworkConfig {
    defaultEnvironment: string;
    proxyUrls: Record<string, string | null>;
    caBundle: string | null;
    cert: string | null;
    certVerify: boolean;
    agentProxy: {
        httpProxy: string | null;
        httpsProxy: string | null;
    } | null;
}

export interface ComputeOptions {
    includeHeaders?: boolean;
    includeProxy?: boolean;
    includeNetwork?: boolean;
    includeConfig?: boolean;
    environment?: string;
    suppressAuthErrors?: boolean;
    resolveTemplates?: boolean;
}

export interface ComputeResult {
    configType: ConfigPath;
    configName: string;
    authConfig?: AuthConfig;
    authError?: any;
    headers?: Record<string, string>;
    proxyConfig?: ProxyResolutionResult;
    networkConfig?: NetworkConfig;
    config?: Record<string, any>;
}

export interface ComputedAuthConfig {
    authConfig: AuthConfig;
    headers?: Record<string, string>;
}
