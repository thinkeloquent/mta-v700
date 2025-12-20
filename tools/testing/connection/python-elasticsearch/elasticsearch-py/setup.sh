#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "[elasticsearch-py] Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[elasticsearch-py] Installing dependencies..."
pip install -r requirements.txt

echo "[elasticsearch-py] Setup complete."
