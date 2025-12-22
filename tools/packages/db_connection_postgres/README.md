# Database Connection Postgres

Unified PostgreSQL database connection package for Python and Node.js applications.

## Overview

This package provides a standardized way to connect to PostgreSQL databases, handling:
- Configuration from environment variables
- Connection pooling
- SSL mode configuration (crucial for cloud deployments)
- Health checks
- Framework integration (FastAPI)

## Python Usage

```python
from db_connection_postgres import DatabaseConfig, DatabaseManager

# Config automatically loads from env vars
config = DatabaseConfig()

# Get manager
manager = DatabaseManager(config)

# Get async session
async with manager.async_session() as session:
    result = await session.execute("SELECT 1")
```

## Node.js Usage

```javascript
import { PostgresConfig, getPostgresClient } from '@internal/db_connection_postgres';

const config = new PostgresConfig();
const client = getPostgresClient(config);

await client.authenticate();
```
