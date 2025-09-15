"""
Database configuration and connection management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create database engine
if settings.ENVIRONMENT == "development":
    # Development settings with more verbose logging
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,  # Set to True for SQL query logging
        pool_pre_ping=True,  # Validate connections before use
        pool_recycle=300,  # Recycle connections after 5 minutes
    )
else:
    # Production settings
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=20,
        max_overflow=30,
    )

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create declarative base for models
Base = declarative_base()


def get_db():
    """
    Database dependency for FastAPI
    Provides database session to route handlers
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables
    """
    try:
        # Import all models to ensure they're registered with Base
        import sys
        import os
        
        # Add project root to path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        if project_root not in sys.path:
            sys.path.append(project_root)
        
        # Import models
        from models.user import User
        from models.auth import WealthsimpleAuth
        from models.portfolio import Portfolio, Holding, Transaction, PerformanceHistory, Watchlist, Alert
        from models.yfinance import (
            StockInfo, StockPrice, StockNews, Earnings,
            Financials, DividendHistory, StockSplit, AnalystRating
        )
        from models.openinsider import InsiderTrade, InsiderSummary, TopInsider, InsiderAlert
        from models.social_sentiment import RedditPost, RedditComment, StockSentiment
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise


def check_db_connection():
    """
    Check if database connection is working
    """
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False