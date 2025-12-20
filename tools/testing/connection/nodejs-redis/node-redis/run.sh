#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Installing dependencies..."
npm install --silent

echo "Running node-redis connection test..."
node connect.mjs
