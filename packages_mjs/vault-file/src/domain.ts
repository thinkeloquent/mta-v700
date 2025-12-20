export interface VaultHeader {
    id: string;
    version: string;
    createdAt: string; // ISO 8601
}

export interface VaultMetadata {
    data: Record<string, any>;
}

export interface VaultPayload {
    content: any;
}

export interface LoadResult {
    loaded: string[];
    errors: Array<{ file: string; error: string }>;
}
