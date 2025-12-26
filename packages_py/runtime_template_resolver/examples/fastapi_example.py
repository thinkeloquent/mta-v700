"""
FastAPI integration example for runtime_template_resolver.

Usage:
    uvicorn fastapi_example:app --reload
"""
from fastapi import FastAPI, Request
from runtime_template_resolver import resolve
import uvicorn
import time

app = FastAPI()

# Simulated database/config
TEMPLATE_CONFIG = {
    "welcome_message": "Hello {{user.name}} from {{client.ip}}",
    "status_header": "System is {{system.status}} at {{timestamp}}"
}

@app.get("/")
async def root(request: Request):
    # Build request context
    context = {
        "user": {
            "name": request.query_params.get("name", "Anonymous"),
            "agent": request.headers.get("user-agent")
        },
        "client": {
            "ip": request.client.host
        },
        "system": {
            "status": "operational"
        },
        "timestamp": time.time()
    }
    
    # Resolve templates
    message = resolve(TEMPLATE_CONFIG["welcome_message"], context)
    header = resolve(TEMPLATE_CONFIG["status_header"], context)
    
    return {
        "message": message,
        "debug_header": header,
        "context": context
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
