# Elasticsearch Connection Examples

Example projects demonstrating usage of the `db_connection_elasticsearch` packages.

## Projects

### FastAPI Example (Python)
A FastAPI application showcasing the Python `db_connection_elasticsearch` package.

**Endpoints:**
- `GET /health` - Health check with Elasticsearch status
- `GET /connection/check` - Check connection using library function
- `GET /indices` - List all Elasticsearch indices
- `POST /search` - Search documents
- `POST /documents` - Index a document
- `GET /documents/{index}/{doc_id}` - Get document by ID
- `DELETE /documents/{index}/{doc_id}` - Delete document by ID

### Fastify Example (Node.js/TypeScript)
A Fastify application showcasing the Node.js `db-connection-elasticsearch` package.

**Endpoints:**
- `GET /health` - Health check with Elasticsearch status
- `GET /connection/check` - Check connection using library function
- `GET /indices` - List all Elasticsearch indices
- `POST /search` - Search documents
- `POST /documents` - Index a document
- `GET /documents/:index/:docId` - Get document by ID
- `DELETE /documents/:index/:docId` - Delete document by ID

## Running with Docker Compose

The easiest way to run all examples together with Elasticsearch:

```bash
cd examples
docker-compose up --build
```

This starts:
- **Elasticsearch** on `http://localhost:9200`
- **FastAPI Example** on `http://localhost:8000`
- **Fastify Example** on `http://localhost:3000`

### Container Names
All containers use unique prefixed names:
- `es-examples-elasticsearch`
- `es-examples-fastapi`
- `es-examples-fastify`

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
# Edit .env with your Elasticsearch settings

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
# Edit .env with your Elasticsearch settings

# Run the server (JavaScript)
npm run dev

# Or run TypeScript version
npm run dev:ts
```

## Testing the APIs

### Health Check
```bash
# FastAPI
curl http://localhost:8000/health

# Fastify
curl http://localhost:3000/health
```

### Index a Document
```bash
# FastAPI
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"index": "test-index", "document": {"title": "Hello", "content": "World"}}'

# Fastify
curl -X POST http://localhost:3000/documents \
  -H "Content-Type: application/json" \
  -d '{"index": "test-index", "document": {"title": "Hello", "content": "World"}}'
```

### Search Documents
```bash
# FastAPI
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello", "index": "test-index"}'

# Fastify
curl -X POST http://localhost:3000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello", "index": "test-index"}'
```

## Environment Variables

Both examples support the same environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ELASTIC_DB_HOST` | Elasticsearch host | `localhost` |
| `ELASTIC_DB_PORT` | Elasticsearch port | `9200` |
| `ELASTIC_DB_SCHEME` | HTTP or HTTPS | `https` |
| `ELASTIC_DB_API_KEY` | API key authentication | - |
| `ELASTIC_DB_USERNAME` | Basic auth username | - |
| `ELASTIC_DB_PASSWORD` | Basic auth password | - |
| `ELASTIC_DB_VERIFY_CERTS` | Verify SSL certificates | `false` |
| `ELASTIC_DB_CLOUD_ID` | Elastic Cloud deployment ID | - |
