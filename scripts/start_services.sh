#!/bin/bash

# Start all backend services

# Create logs directory if it doesn't exist
mkdir -p logs

# Set up log files with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs"
MAIN_LOG="$LOG_DIR/services_${TIMESTAMP}.log"
CELERY_WORKER_LOG="$LOG_DIR/celery_worker_${TIMESTAMP}.log"
CELERY_BEAT_LOG="$LOG_DIR/celery_beat_${TIMESTAMP}.log"
FASTAPI_LOG="$LOG_DIR/fastapi_${TIMESTAMP}.log"

# Function to log to both console and file
log() {
    echo "$1" | tee -a "$MAIN_LOG"
}

log "Starting Finance Dashboard Services..."
log "Log files created at: $(date)"
log "Main log: $MAIN_LOG"

# Start Docker services (Redis & PostgreSQL)
echo "Starting Docker services (Redis & PostgreSQL)..."
docker-compose up -d redis postgres

# Wait for services to be ready using healthchecks
echo "Waiting for services to be ready..."
echo "Waiting for PostgreSQL..."
docker-compose exec -T postgres pg_isready -U myapp_user -d myapp_db || sleep 10
echo "Waiting for Redis..."
docker-compose exec -T redis redis-cli ping || sleep 5

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Change to backend directory for Python services
cd backend

# Start Celery Worker
echo "Starting Celery Worker..."
celery -A app.core.celery_app worker --loglevel=info &

# Start Celery Beat
echo "Starting Celery Beat..."
celery -A app.core.celery_app beat --loglevel=info &

# Start FastAPI
echo "Starting FastAPI..."
python start_api.py &

# Return to root directory
cd ..

echo "All services started!"
echo "API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"