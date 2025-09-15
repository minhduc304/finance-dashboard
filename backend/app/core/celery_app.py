"""
Celery configuration for background tasks
"""
from celery import Celery
from celery.schedules import crontab
import os
from datetime import timedelta

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "finance_dashboard",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Scheduled tasks
celery_app.conf.beat_schedule = {
    "update-market-data": {
        "task": "app.tasks.update_market_data",
        "schedule": timedelta(minutes=15),  # Every 15 minutes during market hours
        "options": {"expires": 300}
    },
    "collect-reddit-sentiment": {
        "task": "app.tasks.collect_reddit_sentiment",
        "schedule": timedelta(hours=1),  # Every hour
        "options": {"expires": 600}
    },
    "scrape-insider-trading": {
        "task": "app.tasks.scrape_insider_trading",
        "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM
        "options": {"expires": 3600}
    },
    "update-portfolio-values": {
        "task": "app.tasks.update_portfolio_values",
        "schedule": timedelta(minutes=5),  # Every 5 minutes
        "options": {"expires": 180}
    },
    "cleanup-old-data": {
        "task": "app.tasks.cleanup_old_data",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
        "options": {"expires": 3600}
    }
}