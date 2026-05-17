#!/usr/bin/env sh
set -eu

/app/deployment/scripts/wait-for-services.sh

if [ "${RUN_MIGRATIONS_ON_START:-1}" = "1" ]; then
  python manage.py migrate --noinput
fi

if [ "${RUN_COLLECTSTATIC_ON_START:-1}" = "1" ]; then
  python manage.py collectstatic --noinput
fi

if [ "${RUN_BOOTSTRAP_ON_START:-0}" = "1" ]; then
  python manage.py bootstrap_smart360 --demo-password "${BOOTSTRAP_DEMO_PASSWORD:-admin123!}"
fi

if [ "${DJANGO_ENV:-development}" = "development" ]; then
  exec python manage.py runserver 0.0.0.0:${PORT:-8000}
fi

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
