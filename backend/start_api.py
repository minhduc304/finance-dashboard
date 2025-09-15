#!/usr/bin/env python3
"""
Start the FastAPI development server
"""

import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Add the parent directory (project root) to Python path for models
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Finance Dashboard API...")
    print("📊 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("📈 Market Data: http://localhost:8000/api/v1/market/")
    print("💼 Portfolio: http://localhost:8000/api/v1/portfolio/")
    print("💭 Sentiment: http://localhost:8000/api/v1/sentiment/")
    print("👥 Insiders: http://localhost:8000/api/v1/insiders/")
    print("\n" + "="*50)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )