#!/usr/bin/env python3
"""
Database initialization script - creates all tables from scratch
Run this to set up the database structure without migrations
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add backend directory to path to import Base
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

# Load environment variables
load_dotenv()

# Import the shared Base from backend
from backend.app.core.database import Base

# Import all models to register them with Base
from models.user import User
from models.auth import WealthsimpleAuth
from models.portfolio import (
    Portfolio, Holding, Transaction,
    PerformanceHistory, Watchlist, Alert
)
from models.yfinance import (
    StockInfo, StockPrice, StockNews, Earnings,
    Financials, DividendHistory, StockSplit, AnalystRating
)
from models.openinsider import (
    InsiderTrade, InsiderSummary, TopInsider, InsiderAlert
)
from models.social_sentiment import (
    RedditPost, RedditComment, StockSentiment
)

def init_database():
    """Initialize database with all tables"""
    
    # Get database URL from environment
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        "postgresql://myapp_user:secure_password_123@localhost:5432/myapp_db"
    )
    
    print(f"Connecting to database...")
    print(f"URL: {DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('//')[1], '***:***')}")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Test connection
        with engine.connect() as conn:
            print("Database connection successful!")
        
        # Create all tables
        print("\nCreating tables...")

        # Now all models share the same Base, so we only need one create_all call
        Base.metadata.create_all(bind=engine)
        print("All tables created")
        
        print("\nDatabase initialization complete!")
        
        # List all created tables
        print("\nCreated tables:")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        for table_name in sorted(inspector.get_table_names()):
            print(f"  - {table_name}")
        
        return True
        
    except Exception as e:
        print(f"\n Error initializing database: {e}")
        return False

def drop_all_tables():
    """Drop all tables - use with caution!"""
    
    response = input("This will DELETE ALL DATA. Are you sure? (type 'yes' to confirm): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        "postgresql://myapp_user:secure_password_123@localhost:5432/myapp_db"
    )
    
    try:
        engine = create_engine(DATABASE_URL)
        
        # Drop all tables (now using shared Base)
        Base.metadata.drop_all(bind=engine)
        
        print("All tables dropped successfully")
        
    except Exception as e:
        print(f"Error dropping tables: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database initialization script")
    parser.add_argument(
        "--drop", 
        action="store_true", 
        help="Drop all tables before creating (WARNING: Deletes all data!)"
    )
    
    args = parser.parse_args()
    
    if args.drop:
        drop_all_tables()
        print()
    
    init_database()