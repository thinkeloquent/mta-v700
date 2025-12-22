# PostgreSQL Connection Examples

Example projects demonstrating usage of the `db_connection_postgres` packages.

## Projects

### FastAPI Example (Python)
A FastAPI application showcasing the Python `db_connection_postgres` package with SQLAlchemy async.

**Endpoints:**
- `GET /health` - Health check with database status
- `GET /users` - List all users
- `POST /users` - Create a new user
- `GET /users/{id}` - Get user by ID
- `PUT /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user
- `POST /query` - Execute raw SQL query (testing only)

### Fastify Example (Node.js)
A Fastify application showcasing the Node.js `db_connection_postgres` package with Sequelize.

**Endpoints:**
- `GET /health` - Health check with database status
- `GET /users` - List all users
- `POST /users` - Create a new user
- `GET /users/:id` - Get user by ID
- `PUT /users/:id` - Update user
- `DELETE /users/:id` - Delete user
- `POST /query` - Execute raw SQL query (testing only)

## Running with Docker Compose

The easiest way to run all examples together with PostgreSQL:

```bash
cd examples
docker-compose up --build
```

This starts:
- **PostgreSQL** on `localhost:5432`
- **FastAPI Example** on `http://localhost:8000`
- **Fastify Example** on `http://localhost:3000`

### Container Names
All containers use unique prefixed names:
- `pg-examples-postgres`
- `pg-examples-fastapi`
- `pg-examples-fastify`

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
# Edit .env with your PostgreSQL settings

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
# Edit .env with your PostgreSQL settings

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

### Create a User
```bash
# FastAPI
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com", "bio": "A test user"}'

# Fastify
curl -X POST http://localhost:3000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane Doe", "email": "jane@example.com", "bio": "Another test user"}'
```

### List Users
```bash
# FastAPI
curl http://localhost:8000/users

# Fastify
curl http://localhost:3000/users
```

### Get User by ID
```bash
# FastAPI
curl http://localhost:8000/users/1

# Fastify
curl http://localhost:3000/users/1
```

### Update User
```bash
# FastAPI
curl -X PUT http://localhost:8000/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "John Updated"}'

# Fastify
curl -X PUT http://localhost:3000/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane Updated"}'
```

### Delete User
```bash
# FastAPI
curl -X DELETE http://localhost:8000/users/1

# Fastify
curl -X DELETE http://localhost:3000/users/1
```

## Environment Variables

Both examples support the same environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `postgres` |
| `POSTGRES_DATABASE` | Database name | `postgres` |
| `POSTGRES_SSL_MODE` | SSL mode (disable, prefer, require, verify-ca, verify-full) | `prefer` |
| `POSTGRES_SSL_CA_FILE` | Path to CA certificate file | - |
| `POSTGRES_POOL_SIZE` | Connection pool size | `5` |
| `DATABASE_URL` | Full database URL (overrides individual settings) | - |

## Data Model

Both examples use a simple User model:

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key, auto-increment |
| `name` | String(255) | User's name |
| `email` | String(255) | User's email (unique) |
| `bio` | Text | User's biography |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |
