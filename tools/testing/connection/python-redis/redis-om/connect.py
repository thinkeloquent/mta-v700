import redis
from redis_om import get_redis_connection, HashModel, Field
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


def build_redis_url(config, use_ssl=False):
    """Build a Redis URL from config."""
    scheme = "rediss" if use_ssl else "redis"
    if config['password']:
        if config['username']:
            return f"{scheme}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['db']}"
        else:
            return f"{scheme}://:{config['password']}@{config['host']}:{config['port']}/{config['db']}"
    else:
        return f"{scheme}://{config['host']}:{config['port']}/{config['db']}"


def main():
    print("=" * 60)
    print("redis-om Connection Test (SSL=false)")
    print("=" * 60)

    config = get_redis_config()

    print(f"Config:")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  Username: {config['username'] or '(none)'}")
    print(f"  Password: {'***' if config['password'] else '(none)'}")
    print(f"  DB: {config['db']}")
    print(f"  SSL: {config['use_ssl']}")

    # ---------------------------------------------------------
    # Test 4: SSL connection with verification disabled
    # ---------------------------------------------------------
    print("\n[Test 4] SSL connection with verification disabled")
    try:
        url = build_redis_url(config, use_ssl=True)
        # For rediss:// URLs, we need to pass ssl_cert_reqs
        conn = get_redis_connection(
            url=url,
            decode_responses=True,
            ssl_cert_reqs=None,
        )
        pong = conn.ping()
        print(f"  SUCCESS: Connected with SSL (no verify)! PING returned: {pong}")
        conn.close()
    except Exception as e:
        print(f"  FAILURE: {e}")



if __name__ == "__main__":
    main()
