#!/bin/bash

echo "Starting Loan Management System services..."

# Initialize PID variables
REDIS_PID=""
CELERY_PID=""
DJANGO_PID=""

cleanup() {
    echo -e "\nStopping services..."
    if [ -n "$DJANGO_PID" ]; then kill $DJANGO_PID 2>/dev/null || true; fi
    if [ -n "$CELERY_PID" ]; then kill $CELERY_PID 2>/dev/null || true; fi
    if [ -n "$REDIS_PID" ]; then kill $REDIS_PID 2>/dev/null || true; fi
    echo "Services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if Redis is running, start it if not
if ! pgrep -x "redis-server" > /dev/null; then
    if command -v redis-server >/dev/null 2>&1; then
        echo "Starting Redis Server..."
        redis-server &
        REDIS_PID=$!
    else
        echo "WARNING: redis-server not found. Make sure Redis is running (e.g., via Docker or systemd)."
    fi
else
    echo "Redis is already running."
fi

# Check for uv package manager
if command -v uv >/dev/null 2>&1; then
    CMD_PREFIX="uv run"
else
    # Fallback to current environment if uv is not available
    CMD_PREFIX=""
fi

echo "Starting Celery worker..."
$CMD_PREFIX celery -A config worker --loglevel=INFO &
CELERY_PID=$!

echo "Starting Django server..."
$CMD_PREFIX python manage.py runserver &
DJANGO_PID=$!

echo "========================================="
echo "All services are running!"
echo "Django Server: http://127.0.0.1:8000"
echo "Press Ctrl+C to stop all services."
echo "========================================="

# Wait for all background processes
wait
