"""
FastAPI example using fetch_auth_config.
"""
import logging
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException
from fetch_auth_config import fetch_auth_config, AuthConfig, AuthType

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- Mock Configuration (simulating loading from a yaml file) ---
MOCK_APP_CONFIG = {
    "providers": {
        "github": {
            "api_auth_type": "bearer",
            "env_api_key": "GITHUB_TOKEN"
        },
        "stripe": {
            "api_auth_type": "basic",
            "env_username": "STRIPE_KEY",
            "env_password": "STRIPE_SECRET"
        },
        "internal_service": {
            "api_auth_type": "custom_header",
            "api_auth_header_name": "X-Service-Token",
            "env_api_key": "SERVICE_TOKEN"
        }
    }
}

# --- Dependencies ---

def get_github_auth() -> AuthConfig:
    """Dependency to resolve GitHub authentication."""
    try:
        # In a real app, you would load MOCK_APP_CONFIG['providers']['github'] from app-yaml-config
        config = fetch_auth_config("github", MOCK_APP_CONFIG["providers"]["github"])
        return config
    except Exception as e:
        logger.error(f"Failed to resolve GitHub auth: {e}")
        raise HTTPException(status_code=500, detail="Auth configuration error")

def get_stripe_auth() -> AuthConfig:
    """Dependency to resolve Stripe authentication."""
    return fetch_auth_config("stripe", MOCK_APP_CONFIG["providers"]["stripe"])

# --- Routes ---

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/github-status")
async def github_status(auth: Annotated[AuthConfig, Depends(get_github_auth)]):
    """
    Example route that needs GitHub authentication.
    The 'auth' object contains the resolved token/credentials.
    """
    return {
        "provider": auth.provider_name,
        "auth_type": auth.type,
        "header_name": auth.header_name,
        # In production, NEVER return the actual token. This is just for demo verification.
        "token_preview": f"{auth.token[:4]}..." if auth.token else None,
        "resolved_from": auth.resolution.resolved_from
    }

@app.get("/payment-check")
async def payment_check(auth: Annotated[AuthConfig, Depends(get_stripe_auth)]):
    """Example route using Basic auth resolution."""
    return {
        "provider": auth.provider_name,
        "auth_type": auth.type,
        # Basic auth might resolve username/password
        "has_username": bool(auth.username),
        "has_password": bool(auth.password),
        "resolution_source": auth.resolution.resolved_from
    }

if __name__ == "__main__":
    import uvicorn
    # To run this example, ensure you have env vars set or expect errors/empty values
    # export GITHUB_TOKEN="test_token"
    # export STRIPE_KEY="pk_test_123"
    uvicorn.run(app, host="0.0.0.0", port=8000)
