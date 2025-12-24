/**
 * Endpoint Auth Compute Registry.
 *
 * This file is the entry point for registering custom compute functions for
 * authentication token resolution.
 *
 * Usage:
 *   import { ComputeRegistry } from '@internal/fetch-auth-config';
 *
 *   ComputeRegistry.registerStartup('my_custom_provider', async () => {
 *     // Compute token at startup
 *     return 'my-startup-token';
 *   });
 *
 *   ComputeRegistry.registerRequest('my_request_provider', async (request) => {
 *     // Compute token per request
 *     return request.headers['x-custom-token'];
 *   });
 */

import { ComputeRegistry } from '@internal/fetch-auth-config';

// Add your custom compute functions here
