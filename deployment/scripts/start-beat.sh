#!/usr/bin/env sh
set -eu

/app/deployment/scripts/wait-for-services.sh

exec celery -A config beat \
  --loglevel "${CELERY_LOG_LEVEL:-info}" \
  --scheduler "${CELERY_BEAT_SCHEDULER:-celery.beat:PersistentScheduler}"
