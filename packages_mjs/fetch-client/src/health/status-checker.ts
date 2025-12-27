
/**
 * Fetch Status Checker Implementation.
 */
import { FetchStatus, FetchStatusResult } from "./models.js";
import { ProviderClient, ComputeAllResult } from "../provider/provider-client.js";

export class FetchStatusChecker {
  constructor(
    private provider_name: string,
    private runtime_config: ComputeAllResult,
    private timeout_seconds: number = 10.0,
    private endpoint_override?: string
  ) { }

  public async check(): Promise<FetchStatusResult> {
    try {
      const provider = new ProviderClient(
        this.provider_name,
        this.runtime_config,
        {
          timeoutSeconds: this.timeout_seconds,
          endpointOverride: this.endpoint_override,
        }
      );

      try {
        return await provider.checkHealth();
      } finally {
        await provider.close();
      }
    } catch (e: any) {
      // console.log('DEBUG: Caught error in FetchStatusChecker:', e);
      // Maintain backward compatibility: validation errors return CONFIG_ERROR status
      // instead of throwing.
      const timestamp = new Date().toISOString();
      const result = {
        provider_name: this.provider_name,
        status: FetchStatus.CONFIG_ERROR,
        latency_ms: 0,
        timestamp,
        request: { method: 'UNKNOWN', url: 'UNKNOWN', timeout_seconds: 0 },
        config_used: {
          baseUrl: this.runtime_config.config.base_url || '',
          healthEndpoint: 'UNKNOWN',
          method: 'UNKNOWN',
          timeoutSeconds: 0,
          authType: null,
          authResolved: false,
          authHeaderPresent: false,
          isPlaceholder: null,
          proxyUrl: null,
          proxyResolved: false,
          headersCount: 0
        },
        fetch_option_used: {
          method: 'UNKNOWN',
          url: 'UNKNOWN',
          timeoutSeconds: 0,
          headers: {},
          headersCount: 0,
          followRedirects: false,
          proxy: null,
          verifySsl: false
        },
        error: {
          type: 'ConfigError',
          message: e.message || String(e)
        }
      };
      // console.log('DEBUG: Returning error result:', result);
      return result;
    }
  }
}
