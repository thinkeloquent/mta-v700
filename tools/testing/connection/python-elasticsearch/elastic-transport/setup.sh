#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "[elastic-transport] Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[elastic-transport] Installing dependencies..."
pip install -r requirements.txt

echo "[elastic-transport] Setup complete."
