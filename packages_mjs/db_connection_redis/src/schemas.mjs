import { z } from 'zod';
import { VALID_VENDORS } from './constants.mjs';

export const RedisConfigSchema = z.object({
    host: z.string().min(1),
    port: z.number().int().min(1).max(65535),
    username: z.string().nullable().optional(),
    password: z.string().nullable().optional(),
    db: z.number().int().min(0),
    useTls: z.boolean(),
    sslCertReqs: z.enum(['none', 'optional', 'required']),
    sslCaCerts: z.string().nullable().optional(),
    sslCheckHostname: z.boolean(),
    socketTimeout: z.number().positive(),
    socketConnectTimeout: z.number().positive(),
    retryOnTimeout: z.boolean(),
    maxConnections: z.number().int().positive().nullable().optional(),
    minConnections: z.number().int().min(0).nullable().optional(),
    healthCheckInterval: z.number().min(0),
    vendorType: z.enum(VALID_VENDORS).optional(),
});
