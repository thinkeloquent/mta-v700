export const VENDOR_ON_PREM = "on-prem";
export const VENDOR_ELASTIC_CLOUD = "elastic-cloud";
export const VENDOR_ELASTIC_TRANSPORT = "elastic-transport";
export const VENDOR_DIGITAL_OCEAN = "digital-ocean";

export const VALID_VENDORS = new Set([
    VENDOR_ON_PREM,
    VENDOR_ELASTIC_CLOUD,
    VENDOR_ELASTIC_TRANSPORT,
    VENDOR_DIGITAL_OCEAN,
]);

export const VENDOR_DEFAULT_PORTS: Record<string, number> = {
    [VENDOR_ON_PREM]: 9200,
    [VENDOR_ELASTIC_CLOUD]: 443,
    [VENDOR_ELASTIC_TRANSPORT]: 9200,
    [VENDOR_DIGITAL_OCEAN]: 25060,
};

export const TLS_PORTS = new Set([443, 9243, 25060]);
