"""
Portfolio models for local finance dashboard
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

# Import shared Base from backend
import sys
import os
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
sys.path.insert(0, backend_path)
from app.core.database import Base


class Portfolio(Base):
    """Portfolio for tracking investments"""
    __tablename__ = 'portfolios'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

    # Current values
    total_value = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    total_gain_loss = Column(Float, default=0.0)
    cash_balance = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    holdings = relationship("Holding", back_populates="portfolio")
    transactions = relationship("Transaction", back_populates="portfolio")


class Holding(Base):
    """Stock holding in a portfolio"""
    __tablename__ = 'holdings'

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)

    # Stock info - using actual database column names
    ticker = Column(String(10), nullable=False)
    name = Column(String(255))
    security_type = Column(String(20))
    quantity = Column(Float, nullable=False)
    average_cost = Column(Float, nullable=False)
    total_cost = Column(Float)

    # Current values
    current_price = Column(Float)
    market_value = Column(Float)
    unrealized_gain = Column(Float)
    unrealized_gain_percent = Column(Float)
    realized_gain = Column(Float)
    portfolio_percent = Column(Float)

    # Timestamps - using actual database column names
    first_purchase_date = Column(DateTime)
    last_updated = Column(DateTime)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")


class Transaction(Base):
    """Buy/sell transaction record"""
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)

    # Transaction info
    type = Column(String(20), nullable=False)  # buy, sell, dividend
    symbol = Column(String(20))
    quantity = Column(Float)
    price = Column(Float)
    total_amount = Column(Float, nullable=False)

    # Timestamps
    transaction_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="transactions")


class PerformanceHistory(Base):
    """Daily portfolio performance snapshot"""
    __tablename__ = 'performance_history'

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)

    # Snapshot values
    date = Column(DateTime, nullable=False)
    total_value = Column(Float, nullable=False)
    daily_return = Column(Float)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class Watchlist(Base):
    """Stock watchlist"""
    __tablename__ = 'watchlists'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    tickers = Column(JSON)  # List of stock tickers
    is_public = Column(Boolean)
    is_default = Column(Boolean)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Alert(Base):
    """Price alerts"""
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True)

    # Alert config
    symbol = Column(String(20), nullable=False)
    alert_type = Column(String(50), nullable=False)  # price_above, price_below
    trigger_value = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    triggered_at = Column(DateTime)