
// Mock Decorators
function Get(path: string) { return (target: any, propertyKey: string) => { }; }
function Post(path: string) { return (target: any, propertyKey: string) => { }; }

class ConnectDto {
    host: string;
    port: number;
}

class UserController {
    @Get('/users')
    findAll() {
        return [];
    }

    @Post('/users')
    create(dto: ConnectDto) {
        if (!dto.host) {
            throw new Error('Host required');
        }
    }
}

const app = { get: (path: string, cb: any) => { } };
app.get('/health', () => {
    return 'ok';
});
