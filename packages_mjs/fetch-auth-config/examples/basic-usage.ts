import { fetchAuthConfig } from '@internal/fetch-auth-config';

function example1_resolveBearer() {
    console.log('\n--- Example 1: Resolve Bearer ---');

    process.env.MY_API_TOKEN = 'sk-test-123';

    try {
        const config = fetchAuthConfig({
            providerName: 'my-provider',
            providerConfig: {
                api_auth_type: 'bearer',
                env_api_key: 'MY_API_TOKEN'
            }
        });

        console.log('Resolved:', {
            type: config.type,
            token: config.token,
            source: config.resolution.resolvedFrom
        });
    } catch (e) {
        console.error('Error:', e);
    } finally {
        delete process.env.MY_API_TOKEN;
    }
}

function example2_resolveBasic() {
    console.log('\n--- Example 2: Resolve Basic Auth ---');

    process.env.API_USER = 'admin';
    process.env.API_PASS = 'secret';

    try {
        const config = fetchAuthConfig({
            providerName: 'basic-provider',
            providerConfig: {
                api_auth_type: 'basic',
                env_username: 'API_USER',
                env_password: 'API_PASS'
            }
        });

        console.log('Resolved:', {
            type: config.type,
            user: config.username,
            pass: config.password, // Warning: sensitive
            source: config.resolution.resolvedFrom
        });
    } finally {
        delete process.env.API_USER;
        delete process.env.API_PASS;
    }
}

example1_resolveBearer();
example2_resolveBasic();
