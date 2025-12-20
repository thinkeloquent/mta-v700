import { z } from 'zod';
import { SSL_MODES } from './constants.mjs';

export const PostgresConfigSchema = z.object({
    host: z.string().min(1),
    port: z.number().int().min(1).max(65535),
    username: z.string().min(1),
    password: z.string().nullable().optional(),
    database: z.string().min(1),
    sslMode: z.enum(SSL_MODES),
    sslCaCerts: z.string().nullable().optional(),
    connectTimeout: z.number().int().positive(),
    maxConnections: z.number().int().positive(),
});
