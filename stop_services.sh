#!/bin/bash

# Stop all backend services

echo "Stopping Finance Dashboard Services..."

# Stop Python processes
echo "Stopping Python services..."

# Kill Celery processes
pkill -f "celery.*worker" || true
pkill -f "celery.*beat" || true

# Kill FastAPI/Uvicorn processes
pkill -f "start_api.py" || true
pkill -f "uvicorn" || true

# Kill any Python processes using port 8000
echo "Killing processes on port 8000..."
lsof -ti :8000 | xargs -r kill -9 || true

# Kill any remaining Python processes in this project
echo "Killing remaining project processes..."
pkill -f "finance-dashboard" || true

# Stop Docker services
echo "Stopping Docker services..."
docker-compose stop redis postgres

# Wait a moment for processes to terminate
sleep 2

# Verify port 8000 is free
if lsof -i :8000 > /dev/null 2>&1; then
    echo "Warning: Some processes may still be running on port 8000"
    lsof -i :8000
else
    echo "Port 8000 is now free"
fi

echo "All services stopped!"