import redis.asyncio as aioredis
import asyncio
import os
import ssl
from dotenv import load_dotenv

load_dotenv()


def get_redis_config():
    """Get Redis configuration from environment."""
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    password = os.getenv("REDIS_PASSWORD", "")
    username = os.getenv("REDIS_USERNAME", "")
    db = os.getenv("REDIS_DB", "0")
    use_ssl = os.getenv("REDIS_SSL", "false").lower() == "true"

    return {
        "host": host,
        "port": int(port),
        "password": password if password else None,
        "username": username if username else None,
        "db": int(db),
        "use_ssl": use_ssl,
    }


async def test_ssl_disabled(config):
    """Test 4: SSL connection with verification disabled"""
    print("\n[Test 4] SSL connection with verification disabled")
    try:
        r = aioredis.Redis(
            host=config['host'],
            port=config['port'],
            db=config['db'],
            username=config['username'],
            password=config['password'],
            decode_responses=True,
            socket_connect_timeout=5,
            ssl=True,
            ssl_cert_reqs=None,
        )
        pong = await r.ping()
        print(f"  SUCCESS: Connected with SSL (no verify)! PING returned: {pong}")
        await r.close()
    except Exception as e:
        print(f"  FAILURE: {e}")


async def test_ssl_context(config):
    """Test 5: SSL with custom context (verification disabled)"""
    print("\n[Test 5] SSL with custom context (verification disabled)")
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        r = aioredis.Redis(
            host=config['host'],
            port=config['port'],
            db=config['db'],
            username=config['username'],
            password=config['password'],
            decode_responses=True,
            socket_connect_timeout=5,
            ssl=True,
            ssl_cert_reqs="none",
        )
        pong = await r.ping()
        print(f"  SUCCESS: Connected with custom SSL! PING returned: {pong}")
        await r.close()
    except Exception as e:
        print(f"  FAILURE: {e}")



async def main():
    print("=" * 60)
    print("aioredis (redis.asyncio) Connection Test (SSL=false)")
    print("=" * 60)

    config = get_redis_config()

    print(f"Config:")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  Username: {config['username'] or '(none)'}")
    print(f"  Password: {'***' if config['password'] else '(none)'}")
    print(f"  DB: {config['db']}")
    print(f"  SSL: {config['use_ssl']}")

    await test_ssl_disabled(config)
    await test_ssl_context(config)

if __name__ == "__main__":
    asyncio.run(main())
