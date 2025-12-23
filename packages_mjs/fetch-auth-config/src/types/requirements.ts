import { AuthType } from './auth-type.js';

export interface AuthTypeRequirement {
    required: string[];
    optional: string[];
    headerName: string | null;
}

export const AUTH_TYPE_REQUIREMENTS: Record<AuthType, AuthTypeRequirement> = {
    [AuthType.BASIC]: {
        required: ['username', 'password'],
        optional: [],
        headerName: 'Authorization'
    },
    [AuthType.BASIC_EMAIL_TOKEN]: {
        required: ['email', 'token'],
        optional: [],
        headerName: 'Authorization'
    },
    [AuthType.BASIC_TOKEN]: {
        required: ['username', 'token'],
        optional: [],
        headerName: 'Authorization'
    },
    [AuthType.BASIC_EMAIL]: {
        required: ['email', 'password'],
        optional: [],
        headerName: 'Authorization'
    },
    [AuthType.BEARER]: {
        required: ['token'],
        optional: [],
        headerName: 'Authorization'
    },
    [AuthType.BEARER_OAUTH]: {
        required: ['token'],
        optional: [],
        headerName: 'Authorization'
    },
    [AuthType.BEARER_JWT]: {
        required: ['token'],
        optional: [],
        headerName: 'Authorization'
    },
    [AuthType.BEARER_USERNAME_TOKEN]: {
        required: ['username', 'token'],
        optional: [],
        headerName: 'Authorization'
    },
    [AuthType.BEARER_USERNAME_PASSWORD]: {
        required: ['username', 'password'],
        optional: [],
        headerName: 'Authorization'
    },
    [AuthType.BEARER_EMAIL_TOKEN]: {
        required: ['email', 'token'],
        optional: [],
        headerName: 'Authorization'
    },
    [AuthType.BEARER_EMAIL_PASSWORD]: {
        required: ['email', 'password'],
        optional: [],
        headerName: 'Authorization'
    },
    [AuthType.X_API_KEY]: {
        required: ['token'],
        optional: [],
        headerName: 'X-API-Key'
    },
    [AuthType.CUSTOM]: {
        required: ['token', 'headerName'],
        optional: [],
        headerName: null // dynamic
    },
    [AuthType.CUSTOM_HEADER]: {
        required: ['token', 'headerName'],
        optional: [],
        headerName: null // dynamic
    },
    [AuthType.EDGEGRID]: {
        required: ['clientToken', 'clientSecret', 'accessToken', 'baseUrl'],
        optional: ['headersToSign'],
        headerName: 'Authorization'
    },
    [AuthType.CONNECTION_STRING]: {
        required: ['connectionString'],
        optional: [],
        headerName: null
    },
    [AuthType.HMAC]: {
        required: ['accessKey', 'secretKey'],
        optional: ['region', 'service'],
        headerName: 'Authorization'
    },
    [AuthType.NONE]: {
        required: [],
        optional: [],
        headerName: null
    }
};
