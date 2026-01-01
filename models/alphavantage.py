"""
Database models for Alpha Vantage data
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Index, UniqueConstraint, Text
from datetime import datetime, timezone

# Import shared Base from backend
import sys
import os
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
sys.path.insert(0, backend_path)
from app.core.database import Base


class TechnicalIndicator(Base):
    """Technical indicators (RSI, MACD, SMA, etc.)"""
    __tablename__ = "technical_indicators"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    indicator_type = Column(String(20), nullable=False)  # RSI, MACD, SMA, etc.
    date = Column(DateTime(timezone=True), nullable=False)
    value = Column(Float, nullable=False)

    # For multi-value indicators (e.g., MACD has signal, histogram)
    value_2 = Column(Float, nullable=True)
    value_3 = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_ticker_indicator_date', 'ticker', 'indicator_type', 'date'),
        UniqueConstraint('ticker', 'indicator_type', 'date', name='uq_ticker_indicator_date'),
    )


class CompanyFundamentals(Base):
    """Company fundamental data from Alpha Vantage"""
    __tablename__ = "company_fundamentals"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)

    # Basic info
    name = Column(String(255))
    description = Column(Text)

    # From Alpha Vantage OVERVIEW
    peg_ratio = Column(Float)
    book_value = Column(Float)
    revenue_per_share = Column(Float)
    profit_margin = Column(Float)
    operating_margin = Column(Float)
    return_on_assets = Column(Float)
    return_on_equity = Column(Float)
    revenue_ttm = Column(Float)
    gross_profit_ttm = Column(Float)
    ebitda = Column(Float)
    analyst_target_price = Column(Float)
    moving_avg_50_day = Column(Float)
    moving_avg_200_day = Column(Float)
    week_52_high = Column(Float)
    week_52_low = Column(Float)

    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))
