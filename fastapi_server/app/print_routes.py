"""Print registered FastAPI routes."""

from fastapi import FastAPI
from fastapi.routing import APIRoute


def print_routes(app: FastAPI):
    """Print all registered routes in a formatted table."""
    print("Registered Routes:")
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = ", ".join(sorted(route.methods))
            print(f"  {route.path:<40} | {methods:<10} | {route.name}")
