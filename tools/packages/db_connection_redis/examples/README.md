# Redis Connection Examples

Example projects demonstrating usage of the `db_connection_redis` packages.

## Projects

### FastAPI Example (Python)
A FastAPI application showcasing the Python `db_connection_redis` package with async redis-py.

**Endpoints:**
- `GET /health` - Health check with Redis status
- `GET /stats` - Get cache statistics
- `GET /keys` - List keys matching pattern
- `GET /keys/{key}` - Get value by key
- `POST /keys` - Set a key-value pair
- `DELETE /keys/{key}` - Delete a key
- `GET /hash/{key}` - Get all hash fields
- `POST /hash` - Set hash field
- `DELETE /hash/{key}/{field}` - Delete hash field
- `GET /list/{key}` - Get list items
- `POST /list` - Push to list
- `DELETE /list/{key}` - Pop from list
- `POST /counter/{key}/incr` - Increment counter
- `POST /counter/{key}/decr` - Decrement counter
- `POST /keys/{key}/expire` - Set TTL
- `DELETE /keys/{key}/expire` - Remove TTL

### Fastify Example (Node.js)
A Fastify application showcasing the Node.js `db_connection_redis` package with ioredis.

**Endpoints:** Same as FastAPI example above.

## Running with Docker Compose

The easiest way to run all examples together with Redis:

```bash
cd examples
docker-compose up --build
```

This starts:
- **Redis** on `localhost:6379`
- **FastAPI Example** on `http://localhost:8000`
- **Fastify Example** on `http://localhost:3000`

### Container Names
All containers use unique prefixed names:
- `redis-examples-redis`
- `redis-examples-fastapi`
- `redis-examples-fastify`

### Stopping Services
```bash
docker-compose down

# To also remove volumes:
docker-compose down -v
```

## Running Locally

### FastAPI Example

```bash
cd fastapi-example

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install poetry
poetry install

# Copy and configure environment
cp .env.example .env
# Edit .env with your Redis settings

# Run the server
uvicorn main:app --reload
```

### Fastify Example

```bash
cd fastify-example

# Install dependencies
npm install

# Copy and configure environment
cp .env.example .env
# Edit .env with your Redis settings

# Run the server
npm run dev
```

## Testing the APIs

### Health Check
```bash
# FastAPI
curl http://localhost:8000/health

# Fastify
curl http://localhost:3000/health
```

### Set a Key
```bash
# FastAPI
curl -X POST http://localhost:8000/keys \
  -H "Content-Type: application/json" \
  -d '{"key": "greeting", "value": "Hello World", "ttl": 3600}'

# Fastify
curl -X POST http://localhost:3000/keys \
  -H "Content-Type: application/json" \
  -d '{"key": "counter", "value": "100"}'
```

### Get a Key
```bash
# FastAPI
curl http://localhost:8000/keys/greeting

# Fastify
curl http://localhost:3000/keys/counter
```

### List Keys
```bash
# FastAPI
curl "http://localhost:8000/keys?pattern=*&limit=50"

# Fastify
curl "http://localhost:3000/keys?pattern=*&limit=50"
```

### Hash Operations
```bash
# Set hash field
curl -X POST http://localhost:8000/hash \
  -H "Content-Type: application/json" \
  -d '{"key": "user:1", "field": "name", "value": "John Doe"}'

# Get hash
curl http://localhost:8000/hash/user:1

# Delete hash field
curl -X DELETE http://localhost:8000/hash/user:1/name
```

### List Operations
```bash
# Push to list
curl -X POST http://localhost:8000/list \
  -H "Content-Type: application/json" \
  -d '{"key": "queue", "value": "task1", "position": "right"}'

# Get list
curl http://localhost:8000/list/queue

# Pop from list
curl -X DELETE "http://localhost:8000/list/queue?position=left"
```

### Counter Operations
```bash
# Increment
curl -X POST "http://localhost:8000/counter/visits/incr?amount=1"

# Decrement
curl -X POST "http://localhost:8000/counter/visits/decr?amount=1"
```

### TTL Operations
```bash
# Set expiry
curl -X POST http://localhost:8000/keys/greeting/expire \
  -H "Content-Type: application/json" \
  -d '{"seconds": 300}'

# Remove expiry
curl -X DELETE http://localhost:8000/keys/greeting/expire
```

## Environment Variables

Both examples support the same environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_PASSWORD` | Redis password | - |
| `REDIS_DB` | Redis database number | `0` |
| `REDIS_SSL` | Enable SSL/TLS | `false` |
| `REDIS_SSL_CA_CERTS` | Path to CA certificate | - |
| `REDIS_URL` | Full Redis URL (overrides individual settings) | - |

## Redis Data Types Demonstrated

| Type | Operations |
|------|------------|
| **String** | GET, SET, SETEX, DEL, TTL, EXPIRE, PERSIST |
| **Hash** | HGETALL, HSET, HDEL |
| **List** | LRANGE, LPUSH, RPUSH, LPOP, RPOP, LLEN |
| **Counter** | INCRBY, DECRBY |
| **Keys** | SCAN, DBSIZE, INFO |
