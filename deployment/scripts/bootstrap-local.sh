#!/usr/bin/env sh
set -eu

docker compose -f deployment/compose/docker-compose.dev.yml up -d --build
docker compose -f deployment/compose/docker-compose.dev.yml exec web python manage.py migrate
docker compose -f deployment/compose/docker-compose.dev.yml exec web python manage.py bootstrap_smart360 --demo-password "${BOOTSTRAP_DEMO_PASSWORD:-admin123!}"
