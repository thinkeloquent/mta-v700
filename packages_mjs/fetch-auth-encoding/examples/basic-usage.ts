import { encodeAuth } from '@internal/fetch-auth-encoding';

function main() {
    console.log('--- Basic Auth ---');
    const basic = encodeAuth('basic', { username: 'user1', password: 'password1' });
    console.log('Headers:', basic);

    console.log('\n--- Bearer Token ---');
    const bearer = encodeAuth('bearer', { token: 'sk-123456' });
    console.log('Headers:', bearer);

    console.log('\n--- Custom Header ---');
    const custom = encodeAuth('custom_header', { headerKey: 'X-My-Service', headerValue: 'secret-val' });
    console.log('Headers:', custom);
}

main();
