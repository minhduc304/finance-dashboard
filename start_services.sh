#!/bin/bash

# Start all backend services

echo "Starting Finance Dashboard Services..."

# Start Redis (if not using Docker)
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    redis-server redis.conf &
fi

# Start PostgreSQL (if not using Docker)
# Uncomment if needed
# pg_ctl start

# Start Celery Worker
echo "Starting Celery Worker..."
celery -A backend.app.core.celery_app worker --loglevel=info &

# Start Celery Beat
echo "Starting Celery Beat..."
celery -A backend.app.core.celery_app beat --loglevel=info &

# Start FastAPI
echo "Starting FastAPI..."
cd backend && python start_api.py &

echo "All services started!"
echo "API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"