# models/yfinance.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric, Text, Index, Boolean, JSON
from datetime import datetime

# Import shared Base from backend
import sys
import os
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
sys.path.insert(0, backend_path)
from app.core.database import Base

class StockInfo(Base):
    """Basic stock/ETF information and metadata"""
    __tablename__ = "stock_info"
    
    id = Column(Integer, primary_key=True)
    
    # Identifiers
    ticker = Column(String(10), unique=True, index=True)
    name = Column(String(255))
    long_name = Column(String(255))
    
    # Classification
    sector = Column(String(100))
    industry = Column(String(100))
    exchange = Column(String(50))
    quote_type = Column(String(50))  # EQUITY, ETF, etc.
    
    # Company details
    website = Column(String(255))
    description = Column(Text)
    country = Column(String(50))
    currency = Column(String(10))
    
    # Market data
    market_cap = Column(Numeric(20, 2))
    enterprise_value = Column(Numeric(20, 2))
    shares_outstanding = Column(Numeric(20, 0))
    float_shares = Column(Numeric(20, 0))
    
    # Key metrics
    beta = Column(Float)
    trailing_pe = Column(Float)
    forward_pe = Column(Float)
    peg_ratio = Column(Float)
    price_to_book = Column(Float)
    
    # Dividends
    dividend_rate = Column(Numeric(10, 4))
    dividend_yield = Column(Float)
    ex_dividend_date = Column(DateTime)
    payout_ratio = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<StockInfo(ticker={self.ticker}, name={self.name})>"


class StockPrice(Base):
    """Historical and real-time price data"""
    __tablename__ = "stock_prices"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), index=True)
    
    # Price data
    date = Column(DateTime, index=True)
    open = Column(Numeric(12, 4))
    high = Column(Numeric(12, 4))
    low = Column(Numeric(12, 4))
    close = Column(Numeric(12, 4))
    adj_close = Column(Numeric(12, 4))
    volume = Column(Numeric(20, 0))
    
    # Additional metrics
    daily_return = Column(Float)  # Percentage change from previous close
    volatility = Column(Float)  # Rolling volatility (optional)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_ticker_date_unique', 'ticker', 'date', unique=True),
    )
    
    def __repr__(self):
        return f"<StockPrice(ticker={self.ticker}, date={self.date}, close={self.close})>"


class StockNews(Base):
    """News articles related to stocks"""
    __tablename__ = "stock_news"
    
    id = Column(Integer, primary_key=True)
    
    # Article info
    title = Column(String(500))
    link = Column(String(500), unique=True)
    publisher = Column(String(100))
    
    # Related stocks
    primary_ticker = Column(String(10), index=True)
    related_tickers = Column(JSON)  # ["AAPL", "MSFT", etc.]
    
    # Content
    summary = Column(Text)
    
    # Metadata
    publish_time = Column(DateTime, index=True)
    provider_publish_time = Column(DateTime)
    
    # Sentiment (can be populated later)
    sentiment_score = Column(Float)
    sentiment_label = Column(String(20))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_ticker_publish', 'primary_ticker', 'publish_time'),
    )
    
    def __repr__(self):
        return f"<StockNews(ticker={self.primary_ticker}, title={self.title[:50]}...)>"


class Earnings(Base):
    """Quarterly and annual earnings data"""
    __tablename__ = "earnings"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), index=True)
    
    # Period info
    period = Column(String(10))  # Q1, Q2, Q3, Q4, FY
    fiscal_year = Column(Integer)
    earnings_date = Column(DateTime, index=True)
    
    # Earnings data
    reported_eps = Column(Numeric(10, 4))
    estimated_eps = Column(Numeric(10, 4))
    surprise_eps = Column(Numeric(10, 4))
    surprise_percent = Column(Float)
    
    # Revenue data
    reported_revenue = Column(Numeric(20, 2))
    estimated_revenue = Column(Numeric(20, 2))
    surprise_revenue = Column(Numeric(20, 2))
    revenue_surprise_percent = Column(Float)
    
    # Growth metrics
    earnings_growth_yoy = Column(Float)
    revenue_growth_yoy = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_ticker_date_period', 'ticker', 'earnings_date', 'period', unique=True),
    )
    
    def __repr__(self):
        return f"<Earnings(ticker={self.ticker}, period={self.period}, year={self.fiscal_year})>"


class Financials(Base):
    """Financial statements data (income statement, balance sheet, cash flow)"""
    __tablename__ = "financials"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), index=True)
    
    # Period identification
    statement_type = Column(String(20))  # income, balance, cashflow
    period_type = Column(String(10))  # annual, quarterly
    period_ending = Column(DateTime, index=True)
    
    # Income Statement items
    total_revenue = Column(Numeric(20, 2))
    cost_of_revenue = Column(Numeric(20, 2))
    gross_profit = Column(Numeric(20, 2))
    operating_income = Column(Numeric(20, 2))
    net_income = Column(Numeric(20, 2))
    ebitda = Column(Numeric(20, 2))
    
    # Balance Sheet items
    total_assets = Column(Numeric(20, 2))
    total_liabilities = Column(Numeric(20, 2))
    total_equity = Column(Numeric(20, 2))
    cash_and_equivalents = Column(Numeric(20, 2))
    total_debt = Column(Numeric(20, 2))
    
    # Cash Flow items
    operating_cash_flow = Column(Numeric(20, 2))
    investing_cash_flow = Column(Numeric(20, 2))
    financing_cash_flow = Column(Numeric(20, 2))
    free_cash_flow = Column(Numeric(20, 2))
    
    # Ratios
    current_ratio = Column(Float)
    debt_to_equity = Column(Float)
    roe = Column(Float)  # Return on Equity
    roa = Column(Float)  # Return on Assets
    profit_margin = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_financials_unique', 'ticker', 'statement_type', 'period_type', 'period_ending', unique=True),
    )
    
    def __repr__(self):
        return f"<Financials(ticker={self.ticker}, type={self.statement_type}, period={self.period_ending})>"


class DividendHistory(Base):
    """Historical dividend payments"""
    __tablename__ = "dividend_history"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), index=True)
    
    # Dividend data
    ex_date = Column(DateTime, index=True)
    payment_date = Column(DateTime)
    record_date = Column(DateTime)
    declaration_date = Column(DateTime)
    
    amount = Column(Numeric(10, 4))
    frequency = Column(String(20))  # quarterly, monthly, annual
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_dividend_unique', 'ticker', 'ex_date', unique=True),
    )
    
    def __repr__(self):
        return f"<DividendHistory(ticker={self.ticker}, ex_date={self.ex_date}, amount={self.amount})>"


class StockSplit(Base):
    """Stock split history"""
    __tablename__ = "stock_splits"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), index=True)
    
    split_date = Column(DateTime, index=True)
    split_ratio = Column(String(20))  # "2:1", "3:2", etc.
    split_factor = Column(Float)  # Numerical representation
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_split_unique', 'ticker', 'split_date', unique=True),
    )
    
    def __repr__(self):
        return f"<StockSplit(ticker={self.ticker}, date={self.split_date}, ratio={self.split_ratio})>"


class AnalystRating(Base):
    """Analyst recommendations and price targets"""
    __tablename__ = "analyst_ratings"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), index=True)
    
    # Current consensus
    recommendation = Column(String(20))  # buy, hold, sell, strong_buy, strong_sell
    recommendation_mean = Column(Float)  # Numerical score
    
    # Price targets
    target_high = Column(Numeric(10, 2))
    target_low = Column(Numeric(10, 2))
    target_mean = Column(Numeric(10, 2))
    target_median = Column(Numeric(10, 2))
    
    # Analyst counts
    strong_buy = Column(Integer)
    buy = Column(Integer)
    hold = Column(Integer)
    sell = Column(Integer)
    strong_sell = Column(Integer)
    
    # Timestamps
    last_updated = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AnalystRating(ticker={self.ticker}, recommendation={self.recommendation})>"