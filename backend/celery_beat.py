#!/usr/bin/env python
"""
Celery beat scheduler entry point
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.app.core.celery_app import celery_app
from celery import beat

if __name__ == "__main__":
    beat_app = beat.Beat(app=celery_app)
    beat_app.run()