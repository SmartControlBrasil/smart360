#!/usr/bin/env sh
set -eu

python - <<'PY'
import os
import socket
import sys
import time


def wait_for(host, port, label, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, int(port)), timeout=3):
                print(f"{label} available at {host}:{port}")
                return
        except OSError:
            time.sleep(1)
    print(f"Timeout waiting for {label} at {host}:{port}", file=sys.stderr)
    sys.exit(1)


wait_for(os.environ.get("POSTGRES_HOST", "db"), os.environ.get("POSTGRES_PORT", "5432"), "postgres")
wait_for(os.environ.get("REDIS_HOST", "redis"), os.environ.get("REDIS_PORT", "6379"), "redis")
PY
