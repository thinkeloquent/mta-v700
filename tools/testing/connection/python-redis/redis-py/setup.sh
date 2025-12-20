#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "[redis-py] Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[redis-py] Installing dependencies..."
pip install -r requirements.txt

echo "[redis-py] Setup complete."
