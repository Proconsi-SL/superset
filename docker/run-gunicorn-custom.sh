#!/usr/bin/env bash

echo "⚙️  Starting Superset with custom_app.py..."

export PYTHONPATH=/app:$PYTHONPATH
exec gunicorn \
    -w ${SERVER_WORKERS:-4} \
    -k gevent \
    --timeout 60 \
    -b 0.0.0.0:8088 \
    "docker.custom_app:app"
