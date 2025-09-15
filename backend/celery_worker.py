#!/usr/bin/env python
"""
Celery worker entry point
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.app.core.celery_app import celery_app

if __name__ == "__main__":
    celery_app.start()