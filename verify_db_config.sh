#!/bin/bash
set -e

echo "Verifying DB Connection Config Endpoints..."

# Function to check endpoint
check_endpoint() {
    local url=$1
    local name=$2
    echo "Checking $name at $url..."
    response=$(curl -s "$url")
    
    # Check if response contains expected keys
    if echo "$response" | grep -q "config_type" && \
       echo "$response" | grep -q "config_name" && \
       echo "$response" | grep -q "config"; then
        echo "✅ $name OK"
    else
        echo "❌ $name FAILED"
        echo "Response: $response"
        return 1
    fi
}

# FastAPI (52000)
check_endpoint "http://localhost:52000/healthz/admin/db-connection-elasticsearch/config" "FastAPI Elasticsearch"
check_endpoint "http://localhost:52000/healthz/admin/db-connection-postgres/config" "FastAPI Postgres"
check_endpoint "http://localhost:52000/healthz/admin/db-connection-redis/config" "FastAPI Redis"

# Fastify (51000)
check_endpoint "http://localhost:51000/healthz/admin/db-connection-elasticsearch/config" "Fastify Elasticsearch"
check_endpoint "http://localhost:51000/healthz/admin/db-connection-postgres/config" "Fastify Postgres"
check_endpoint "http://localhost:51000/healthz/admin/db-connection-redis/config" "Fastify Redis"

echo "All checks passed!"
