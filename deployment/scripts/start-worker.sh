#!/usr/bin/env sh
set -eu

/app/deployment/scripts/wait-for-services.sh

exec celery -A config worker \
  --loglevel "${CELERY_LOG_LEVEL:-info}" \
  --queues "${CELERY_QUEUES:-default}"
