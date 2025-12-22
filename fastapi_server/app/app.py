"""FastAPI Hello World Server."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from .app_yaml_config import AppYamlConfig
# from . import load_app_env  # noqa: F401 - Handled in main.py
from . import load_app_config  # noqa: F401 - loads AppYamlConfig
from .print_routes import print_routes
from .routes.healthz import (
    vault_file,
    app_yaml_config,
    db_connection_elasticsearch,
    db_connection_postgres,
    db_connection_redis,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print_routes(app)
    yield
    # Shutdown (if needed)


config = AppYamlConfig.get_instance()

app = FastAPI(
    title=config.get_nested("app", "name", default="MTA Server"),
    description=config.get_nested("app", "description", default=""),
    version=config.get_nested("app", "version", default="0.0.0"),
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


app.include_router(vault_file.router)
app.include_router(app_yaml_config.router)
app.include_router(db_connection_elasticsearch.router)
app.include_router(db_connection_postgres.router)
app.include_router(db_connection_redis.router)
