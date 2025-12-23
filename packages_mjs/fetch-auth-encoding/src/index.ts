// --- Sensitive Data Helpers (Inlined) ---

const USERNAME_KEYS = ['username', 'user', 'login', 'id', 'email', 'user_id', 'userId'];
const PASSWORD_KEYS = ['password', 'pwd', 'pass', 'secret', 'token', 'credential', 'access_token', 'accessToken'];
const API_KEY_KEYS = ['api_key', 'apiKey', 'access_key', 'accessKey', 'auth_token', 'authToken', 'token', 'rawApiKey', 'raw_api_key', 'key'];

function getValueFromKeys(obj: any, keys: string[]): string | undefined {
    if (!obj) return undefined;

    // Direct key check
    for (const key of keys) {
        if (obj[key] !== undefined) return obj[key];
    }
    return undefined;
}

function getUsername(obj: any): string | undefined { return getValueFromKeys(obj, USERNAME_KEYS); }
function getPassword(obj: any): string | undefined { return getValueFromKeys(obj, PASSWORD_KEYS); }
function getApiKey(obj: any): string | undefined { return getValueFromKeys(obj, API_KEY_KEYS); }

export interface AuthCredentials {
    username?: string;
    password?: string;
    email?: string;
    token?: string;
    headerKey?: string;
    headerValue?: string;
    value?: string;
    key?: string;
    [key: string]: string | undefined;
}

function b64(str: string): string {
    return Buffer.from(str).toString("base64");
}

export function encodeAuth(authType: string, creds: AuthCredentials): Record<string, string> {
    const type = authType.toLowerCase();

    // Basic Family
    if (type === "basic") {
        const user = getUsername(creds);
        const pass = getPassword(creds);
        if (!user || !pass) throw new Error("Basic auth requires username/email and password/token");
        return { Authorization: `Basic ${b64(`${user}:${pass}`)}` };
    }

    if (type === "basic_email_token") {
        const user = getUsername(creds);
        const pass = getPassword(creds) || getApiKey(creds);
        if (!user || !pass) throw new Error("basic_email_token requires email and token");
        return { Authorization: `Basic ${b64(`${user}:${pass}`)}` };
    }

    if (type === "basic_token") {
        const user = getUsername(creds);
        const pass = getPassword(creds) || getApiKey(creds);
        if (!user || !pass) throw new Error("basic_token requires username and token");
        return { Authorization: `Basic ${b64(`${user}:${pass}`)}` };
    }

    if (type === "basic_email") {
        const user = getUsername(creds);
        const pass = getPassword(creds);
        if (!user || !pass) throw new Error("basic_email requires email and password");
        return { Authorization: `Basic ${b64(`${user}:${pass}`)}` };
    }

    // Bearer Family
    if (["bearer", "bearer_oauth", "bearer_jwt"].includes(type)) {
        const val = getApiKey(creds) || getPassword(creds);
        if (!val) throw new Error(`${type} requires token`);
        return { Authorization: `Bearer ${val}` };
    }

    if (type === "bearer_username_token") {
        const user = getUsername(creds);
        const pass = getPassword(creds) || getApiKey(creds);
        if (!user || !pass) throw new Error("bearer_username_token requires username and token");
        return { Authorization: `Bearer ${b64(`${user}:${pass}`)}` };
    }

    if (type === "bearer_username_password") {
        const user = getUsername(creds);
        const pass = getPassword(creds);
        if (!user || !pass) throw new Error("bearer_username_password requires username and password");
        return { Authorization: `Bearer ${b64(`${user}:${pass}`)}` };
    }

    if (type === "bearer_email_token") {
        const user = getUsername(creds);
        const pass = getPassword(creds) || getApiKey(creds);
        if (!user || !pass) throw new Error("bearer_email_token requires email and token");
        return { Authorization: `Bearer ${b64(`${user}:${pass}`)}` };
    }

    if (type === "bearer_email_password") {
        const user = getUsername(creds);
        const pass = getPassword(creds);
        if (!user || !pass) throw new Error("bearer_email_password requires email and password");
        return { Authorization: `Bearer ${b64(`${user}:${pass}`)}` };
    }

    // Custom
    if (type === "x-api-key") {
        const val = getApiKey(creds) || creds.value;
        if (!val) throw new Error("x-api-key requires token/value");
        return { "X-API-Key": val };
    }

    if (["custom", "custom_header"].includes(type)) {
        const key = creds.headerKey;
        const val = creds.headerValue || getApiKey(creds) || creds.value;
        if (!key) throw new Error(`${type} requires headerKey`);
        return { [key]: val || "" };
    }

    if (type === "none") {
        return {};
    }

    throw new Error(`Unsupported auth type: ${authType}`);
}
