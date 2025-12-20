import { z } from 'zod';

export const VaultHeaderSchema = z.object({
    id: z.string().uuid(),
    version: z.string().regex(/^\d+\.\d+(\.\d+)?$/), // Allow 1.0 or 1.0.0
    createdAt: z.string().datetime()
});

export const VaultMetadataSchema = z.object({
    data: z.record(z.any()).default({})
});

export const VaultPayloadSchema = z.object({
    content: z.any()
});

export const VaultFileSchema = z.object({
    header: VaultHeaderSchema,
    metadata: VaultMetadataSchema,
    payload: VaultPayloadSchema
});

export class VaultValidationError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'VaultValidationError';
    }
}

export class VaultSerializationError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'VaultSerializationError';
    }
}
