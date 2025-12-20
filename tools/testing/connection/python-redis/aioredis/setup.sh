#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "[aioredis] Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[aioredis] Installing dependencies..."
pip install -r requirements.txt

echo "[aioredis] Setup complete."
