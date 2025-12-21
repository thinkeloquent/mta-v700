"""
FastAPI example demonstrating db_connection_postgres usage.

Run with: uvicorn main:app --reload
"""

import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, Text, select
from sqlalchemy.orm import declarative_base

from db_connection_postgres import (
    PostgresConfig,
    DatabaseManager,
    get_db_manager,
)


# SQLAlchemy Base for models
Base = declarative_base()


class User(Base):
    """Example User model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic models
class UserCreate(BaseModel):
    name: str
    email: str
    bio: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    bio: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    database: Dict[str, Any]


# Global database manager
db_manager: Optional[DatabaseManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database connection lifecycle."""
    global db_manager

    # Initialize database manager on startup
    config = PostgresConfig(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        database=os.getenv("POSTGRES_DATABASE", "postgres"),
        ssl_mode=os.getenv("POSTGRES_SSL_MODE", "prefer"),
    )

    db_manager = DatabaseManager(config)

    # Create tables
    try:
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables created")
    except Exception as e:
        print(f"Warning: Could not create tables: {e}")

    yield

    # Cleanup on shutdown
    if db_manager:
        await db_manager.dispose()
        print("Database connections closed")


app = FastAPI(
    title="PostgreSQL FastAPI Example",
    description="Example API demonstrating db_connection_postgres usage",
    version="1.0.0",
    lifespan=lifespan,
)


async def get_session():
    """Dependency to get database session."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not initialized")
    async with db_manager.async_session() as session:
        yield session


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API and database health."""
    if not db_manager:
        return HealthResponse(
            status="degraded",
            database={"connected": False, "error": "Manager not initialized"},
        )

    try:
        is_healthy = await db_manager.test_connection()
        if is_healthy:
            return HealthResponse(
                status="healthy",
                database={
                    "connected": True,
                    "host": db_manager.config.host,
                    "database": db_manager.config.database,
                },
            )
        else:
            return HealthResponse(
                status="degraded",
                database={"connected": False, "error": "Health check failed"},
            )
    except Exception as e:
        return HealthResponse(
            status="degraded",
            database={"connected": False, "error": str(e)},
        )


@app.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    session=Depends(get_session),
):
    """List all users."""
    result = await session.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return users


@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    session=Depends(get_session),
):
    """Create a new user."""
    user = User(
        name=user_data.name,
        email=user_data.email,
        bio=user_data.bio,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    session=Depends(get_session),
):
    """Get a user by ID."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session=Depends(get_session),
):
    """Update a user."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.name is not None:
        user.name = user_data.name
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.bio is not None:
        user.bio = user_data.bio

    user.updated_at = datetime.utcnow()
    await session.flush()
    await session.refresh(user)
    return user


@app.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    session=Depends(get_session),
):
    """Delete a user."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await session.delete(user)
    return None


@app.post("/query")
async def execute_query(
    query: str,
    session=Depends(get_session),
):
    """Execute a raw SQL query (for testing purposes only)."""
    from sqlalchemy import text

    try:
        result = await session.execute(text(query))
        if result.returns_rows:
            rows = result.fetchall()
            columns = result.keys()
            return {
                "rows": [dict(zip(columns, row)) for row in rows],
                "count": len(rows),
            }
        return {"affected_rows": result.rowcount}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
