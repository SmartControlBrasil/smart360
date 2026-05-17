#!/usr/bin/env sh
set -eu

/app/deployment/scripts/wait-for-services.sh

exec "$@"
