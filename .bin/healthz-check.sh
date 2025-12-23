#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${HEALTHZ_BASE_URL:-http://localhost:52000}"
TIMEOUT="${HEALTHZ_TIMEOUT:-5}"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

FAILED=0

check_endpoint() {
    local path="$1"
    local jq_filter="$2"
    local expected="$3"
    local url="${BASE_URL}${path}"

    response=$(curl -s --max-time "$TIMEOUT" "$url" 2>/dev/null) || {
        echo -e "${RED}FAIL${NC} $path - connection failed"
        FAILED=1
        return
    }

    actual=$(echo "$response" | jq -r "$jq_filter" 2>/dev/null) || {
        echo -e "${RED}FAIL${NC} $path - invalid JSON"
        FAILED=1
        return
    }

    if [[ "$actual" == "$expected" ]]; then
        echo -e "${GREEN}OK${NC}   $path"
    else
        echo -e "${RED}FAIL${NC} $path - expected $expected, got $actual"
        FAILED=1
    fi
}

echo "Checking health endpoints at ${BASE_URL}..."
echo

check_endpoint "/healthz/admin/db-connection-elasticsearch/status" ".connected" "true"
check_endpoint "/healthz/admin/db-connection-redis/status" ".connected" "true"
check_endpoint "/healthz/admin/db-connection-postgres/status" ".connected" "true"
check_endpoint "/healthz/admin/vault-file/status" ".loaded" "true"
check_endpoint "/healthz/admin/app-yaml-config/status" ".initialized" "true"

echo
if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}All checks passed${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed${NC}"
    exit 1
fi
