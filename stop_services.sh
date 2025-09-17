#!/bin/bash

# Stop all backend services

echo "Stopping Finance Dashboard Services..."

# Stop Python processes
echo "Stopping Python services..."
pkill -f "celery.*app.core.celery_app.*worker"
pkill -f "celery.*app.core.celery_app.*beat"
pkill -f "python start_api.py"
pkill -f "uvicorn.*app.main:app"

# Stop Docker services
echo "Stopping Docker services..."
docker-compose stop redis postgres

echo "All services stopped!"