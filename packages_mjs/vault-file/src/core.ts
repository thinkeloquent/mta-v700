import { v4 as uuidv4 } from 'uuid';
import yaml from 'js-yaml';
import dotenv from 'dotenv';
import { VaultHeader, VaultMetadata, VaultPayload } from './domain.js';
import {
    VaultFileSchema, VaultValidationError, VaultSerializationError
} from './validators.js';
import { getLogger } from './logger.js';

const logger = getLogger();

export class VaultFile {
    public header: VaultHeader;
    public metadata: VaultMetadata;
    public payload: VaultPayload;

    constructor(
        header?: Partial<VaultHeader>,
        metadata?: Partial<VaultMetadata>,
        payload?: Partial<VaultPayload>
    ) {
        this.header = {
            id: header?.id || uuidv4(),
            version: header?.version || '1.0.0',
            createdAt: header?.createdAt || new Date().toISOString()
        };

        this.metadata = {
            data: metadata?.data || {}
        };

        this.payload = {
            content: payload?.content || null
        };

        this.validateState();
    }

    public validateState(): void {
        const result = VaultFileSchema.safeParse({
            header: this.header,
            metadata: this.metadata,
            payload: this.payload
        });

        if (!result.success) {
            const errorMsg = result.error.errors.map(e => `${e.path.join('.')}: ${e.message}`).join(', ');
            throw new VaultValidationError(`Invalid VaultFile state: ${errorMsg}`);
        }
    }

    public toJSON(): string {
        this.validateState();
        return JSON.stringify({
            header: this.header,
            metadata: this.metadata,
            payload: this.payload
        }, null, 2);
    }

    public static fromJSON(jsonStr: string): VaultFile {
        try {
            const data = JSON.parse(jsonStr);
            const result = VaultFileSchema.safeParse(data);

            if (!result.success) {
                const errorMsg = result.error.errors.map(e => `${e.path.join('.')}: ${e.message}`).join(', ');
                throw new VaultValidationError(`Validation failed: ${errorMsg}`);
            }

            const parsed = result.data;
            return new VaultFile(parsed.header, parsed.metadata, parsed.payload);

        } catch (error) {
            if (error instanceof SyntaxError) {
                throw new VaultSerializationError(`Invalid JSON: ${error.message}`);
            }
            if (error instanceof VaultValidationError) {
                throw new VaultSerializationError(error.message);
            }
            throw error;
        }
    }

    private static readonly BASE64_PREFIX = 'data:application/json;base64,';

    // MIME type constants for format detection
    public static readonly MIME_JSON = 'application/json';
    public static readonly MIME_YAML = 'application/x-yaml';
    public static readonly MIME_YAML_ALT = 'text/x-yaml';
    public static readonly MIME_PROPERTIES = 'text/x-properties';
    public static readonly MIME_PLAIN = 'text/plain';

    private static readonly SUPPORTED_MIME_TYPES = [
        VaultFile.MIME_JSON,
        VaultFile.MIME_YAML,
        VaultFile.MIME_YAML_ALT,
        VaultFile.MIME_PROPERTIES,
        VaultFile.MIME_PLAIN
    ];

    /**
     * Parse a VaultFile from a base64-encoded data URI.
     * Format: data:application/json;base64,<BASE64 Encoded String>
     */
    public static fromBase64File(dataUri: string): VaultFile {
        logger.debug('Parsing VaultFile from base64 data URI');
        if (!dataUri.startsWith(VaultFile.BASE64_PREFIX)) {
            throw new VaultSerializationError(
                `Invalid base64 data URI format. Expected prefix: ${VaultFile.BASE64_PREFIX}`
            );
        }

        const base64Data = dataUri.slice(VaultFile.BASE64_PREFIX.length);

        try {
            const jsonStr = Buffer.from(base64Data, 'base64').toString('utf-8');
            return VaultFile.fromJSON(jsonStr);
        } catch (error) {
            if (error instanceof VaultSerializationError) {
                throw error;
            }
            throw new VaultSerializationError(`Failed to decode base64: ${(error as Error).message}`);
        }
    }

    /**
     * Serialize this VaultFile to a base64-encoded data URI.
     * Format: data:application/json;base64,<BASE64 Encoded String>
     */
    public toBase64File(): string {
        const jsonStr = this.toJSON();
        const base64Data = Buffer.from(jsonStr, 'utf-8').toString('base64');
        return `${VaultFile.BASE64_PREFIX}${base64Data}`;
    }

    /**
     * Decode a base64 data URI to raw string (without parsing).
     * Extracts MIME type and returns decoded content.
     * @param dataUri The data URI in format: data:<mime>;base64,<content>
     * @returns Object with decoded content and detected MIME type
     */
    public static decodeBase64(dataUri: string): { content: string; mimeType: string } {
        const dataUriRegex = /^data:([^;]+);base64,(.+)$/;
        const match = dataUri.match(dataUriRegex);

        if (!match) {
            logger.error('Invalid base64 data URI format');
            throw new VaultSerializationError(
                `Invalid base64 data URI format. Expected: data:<mime>;base64,<content>`
            );
        }

        const mimeType = match[1];
        const base64Data = match[2];

        try {
            const content = Buffer.from(base64Data, 'base64').toString('utf-8');
            return { content, mimeType };
        } catch (error) {
            throw new VaultSerializationError(`Failed to decode base64: ${(error as Error).message}`);
        }
    }

    /**
     * Auto-detect format from MIME type in data URI and parse accordingly.
     * @param dataUri The data URI with MIME type
     * @returns Object with parsed content and detected format
     */
    public static fromBase64Auto(dataUri: string): { content: any; format: string } {
        const { content, mimeType } = VaultFile.decodeBase64(dataUri);
        logger.debug(`Auto-detecting format for MIME: ${mimeType}`);

        switch (mimeType) {
            case VaultFile.MIME_JSON:
                try {
                    return { content: JSON.parse(content), format: 'json' };
                } catch (error) {
                    throw new VaultSerializationError(`Failed to parse JSON: ${(error as Error).message}`);
                }

            case VaultFile.MIME_YAML:
            case VaultFile.MIME_YAML_ALT:
                try {
                    return { content: yaml.load(content), format: 'yaml' };
                } catch (error) {
                    throw new VaultSerializationError(`Failed to parse YAML: ${(error as Error).message}`);
                }

            case VaultFile.MIME_PROPERTIES:
            case VaultFile.MIME_PLAIN:
                try {
                    return { content: dotenv.parse(content), format: 'properties' };
                } catch (error) {
                    throw new VaultSerializationError(`Failed to parse properties: ${(error as Error).message}`);
                }

            default:
                throw new VaultSerializationError(
                    `Unsupported MIME type: ${mimeType}. Supported types: ${VaultFile.SUPPORTED_MIME_TYPES.join(', ')}`
                );
        }
    }

    /**
     * Parse a VaultFile from a YAML string.
     * The YAML should contain header, metadata, and payload structure.
     */
    public static fromYaml(yamlStr: string): VaultFile {
        try {
            const data = yaml.load(yamlStr);

            if (typeof data !== 'object' || data === null) {
                throw new VaultSerializationError('YAML content must be an object');
            }

            const result = VaultFileSchema.safeParse(data);

            if (!result.success) {
                const errorMsg = result.error.errors.map(e => `${e.path.join('.')}: ${e.message}`).join(', ');
                throw new VaultValidationError(`Validation failed: ${errorMsg}`);
            }

            const parsed = result.data;
            return new VaultFile(parsed.header, parsed.metadata, parsed.payload);

        } catch (error) {
            if (error instanceof VaultSerializationError || error instanceof VaultValidationError) {
                throw new VaultSerializationError((error as Error).message);
            }
            throw new VaultSerializationError(`Failed to parse YAML: ${(error as Error).message}`);
        }
    }

    /**
     * Parse a VaultFile from a property file string (.env format).
     * Each line is key=value, which is stored in payload.content.
     */
    public static fromPropertyFile(propStr: string): VaultFile {
        try {
            const parsed = dotenv.parse(propStr);

            // Create a VaultFile with the parsed properties as payload content
            return new VaultFile(
                undefined, // auto-generate header
                { data: {} }, // empty metadata
                { content: parsed }
            );

        } catch (error) {
            throw new VaultSerializationError(`Failed to parse property file: ${(error as Error).message}`);
        }
    }

    /**
     * Serialize this VaultFile to YAML format.
     */
    public toYaml(): string {
        this.validateState();
        return yaml.dump({
            header: this.header,
            metadata: this.metadata,
            payload: this.payload
        });
    }

    /**
     * Update this instance with partial data.
     * Header fields are selectively updated, metadata.data and payload.content are replaced.
     */
    public update(options: {
        header?: Partial<VaultHeader>;
        metadata?: Partial<VaultMetadata>;
        payload?: Partial<VaultPayload>;
    }): this {
        if (options.header) {
            this.header = { ...this.header, ...options.header };
        }
        if (options.metadata) {
            this.metadata = {
                data: options.metadata.data ?? this.metadata.data
            };
        }
        if (options.payload) {
            this.payload = {
                content: options.payload.content ?? this.payload.content
            };
        }
        this.validateState();
        return this;
    }

    /**
     * Deep merge another VaultFile into this instance.
     * - Header: other's fields override this (except id)
     * - Metadata.data: deep merged (other overrides conflicts)
     * - Payload.content: replaced by other's content
     */
    public merge(other: VaultFile): this {
        // Keep original id, merge other header fields
        this.header = {
            ...this.header,
            ...other.header,
            id: this.header.id // preserve original id
        };

        // Deep merge metadata.data
        this.metadata.data = this.deepMerge(this.metadata.data, other.metadata.data);

        // Replace payload content
        if (other.payload.content !== null) {
            this.payload.content = other.payload.content;
        }

        this.validateState();
        return this;
    }

    /**
     * Merge from JSON string into this instance.
     */
    public mergeFromJSON(jsonStr: string): this {
        const other = VaultFile.fromJSON(jsonStr);
        return this.merge(other);
    }

    private deepMerge(target: Record<string, any>, source: Record<string, any>): Record<string, any> {
        const result = { ...target };
        for (const key of Object.keys(source)) {
            const val = source[key];
            if (val && typeof val === 'object' && !Array.isArray(val) &&
                result[key] && typeof result[key] === 'object' && !Array.isArray(result[key])) {
                result[key] = this.deepMerge(result[key], val);
            } else {
                result[key] = val;
            }
        }
        return result;
    }
}
