#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "[redis-om] Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[redis-om] Installing dependencies..."
pip install -r requirements.txt

echo "[redis-om] Setup complete."
