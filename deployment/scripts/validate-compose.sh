#!/usr/bin/env sh
set -eu

COMPOSE_FILE="${1:-deployment/compose/docker-compose.dev.yml}"

docker compose -f "${COMPOSE_FILE}" config >/dev/null
echo "Compose file valid: ${COMPOSE_FILE}"
