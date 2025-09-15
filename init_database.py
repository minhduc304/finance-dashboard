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

# Add models directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import all models to register them with Base
from models.user import Base as UserBase, User
from models.auth import Base as AuthBase, WealthsimpleAuth
from models.portfolio import (
    Base as PortfolioBase, 
    Portfolio, Holding, Transaction, 
    PerformanceHistory, Watchlist, Alert
)
from models.yfinance import (
    Base as YFinanceBase,
    StockInfo, StockPrice, StockNews, Earnings,
    Financials, DividendHistory, StockSplit, AnalystRating
)
from models.openinsider import (
    Base as OpenInsiderBase,
    InsiderTrade, InsiderSummary, TopInsider, InsiderAlert
)
from models.social_sentiment import (
    Base as SentimentBase,
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
        
        # Since we have multiple Base objects, we need to create tables for each
        UserBase.metadata.create_all(bind=engine)
        print("User tables created")
        
        AuthBase.metadata.create_all(bind=engine)
        print("Auth tables created")
        
        PortfolioBase.metadata.create_all(bind=engine)
        print("Portfolio tables created")
        
        YFinanceBase.metadata.create_all(bind=engine)
        print("YFinance tables created")
        
        OpenInsiderBase.metadata.create_all(bind=engine)
        print("OpenInsider tables created")
        
        SentimentBase.metadata.create_all(bind=engine)
        print("Sentiment tables created")
        
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
        
        # Drop all tables
        UserBase.metadata.drop_all(bind=engine)
        AuthBase.metadata.drop_all(bind=engine)
        PortfolioBase.metadata.drop_all(bind=engine)
        YFinanceBase.metadata.drop_all(bind=engine)
        OpenInsiderBase.metadata.drop_all(bind=engine)
        SentimentBase.metadata.drop_all(bind=engine)
        
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