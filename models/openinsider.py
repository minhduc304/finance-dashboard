# models/openinsider.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class InsiderTrade(Base):
    """Model for storing insider trading data from OpenInsider"""
    __tablename__ = "insider_trades"
    
    id = Column(Integer, primary_key=True)
    
    # Date fields
    transaction_date = Column(DateTime)  # Filing date/time
    trade_date = Column(DateTime)  # Actual trade execution date
    
    # Company information
    ticker = Column(String(10), index=True)
    company_name = Column(String(255))
    
    # Insider information
    owner_name = Column(String(255))
    title = Column(String(255))  # CEO, CFO, Director, etc.
    
    # Transaction details
    transaction_type = Column(String(50))  # P - Purchase, S - Sale, etc.
    last_price = Column(Numeric(12, 2))  # Price per share
    quantity = Column(Integer)  # Number of shares traded (can be negative for sales)
    shares_held = Column(Integer)  # Total shares held after transaction
    ownership_percentage = Column(Float)  # Percentage owned after transaction
    value = Column(Numeric(15, 2))  # Total transaction value
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Create composite index for efficient queries
    __table_args__ = (
        Index('idx_ticker_date', 'ticker', 'transaction_date'),
        Index('idx_owner_date', 'owner_name', 'transaction_date'),
        Index('idx_transaction_type', 'transaction_type'),
    )
    
    def __repr__(self):
        return f"<InsiderTrade(ticker={self.ticker}, owner={self.owner_name}, type={self.transaction_type}, value={self.value})>"


class InsiderSummary(Base):
    """Aggregated summary of insider trading activity per ticker"""
    __tablename__ = "insider_summary"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), unique=True, index=True)
    company_name = Column(String(255))
    
    # Purchase statistics
    total_purchases = Column(Integer, default=0)
    total_purchase_value = Column(Numeric(15, 2), default=0)
    total_purchase_shares = Column(Integer, default=0)
    avg_purchase_price = Column(Numeric(12, 2))
    
    # Sale statistics
    total_sales = Column(Integer, default=0)
    total_sale_value = Column(Numeric(15, 2), default=0)
    total_sale_shares = Column(Integer, default=0)
    avg_sale_price = Column(Numeric(12, 2))
    
    # Net activity
    net_insider_activity = Column(Numeric(15, 2))  # Purchase value - Sale value
    net_shares_traded = Column(Integer)  # Purchase shares - Sale shares
    
    # Recent activity
    last_purchase_date = Column(DateTime)
    last_sale_date = Column(DateTime)
    last_activity_date = Column(DateTime)
    
    # Insider counts
    unique_buyers = Column(Integer, default=0)
    unique_sellers = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<InsiderSummary(ticker={self.ticker}, net_activity={self.net_insider_activity})>"


class TopInsider(Base):
    """Track top insiders by trading volume and success"""
    __tablename__ = "top_insiders"
    
    id = Column(Integer, primary_key=True)
    
    # Insider identification
    owner_name = Column(String(255), unique=True, index=True)
    most_common_title = Column(String(255))
    
    # Trading statistics
    total_trades = Column(Integer, default=0)
    total_purchases = Column(Integer, default=0)
    total_sales = Column(Integer, default=0)
    
    # Volume statistics
    total_value_traded = Column(Numeric(15, 2), default=0)
    total_purchase_value = Column(Numeric(15, 2), default=0)
    total_sale_value = Column(Numeric(15, 2), default=0)
    
    # Company associations
    companies_traded = Column(Text)  # JSON array of tickers
    primary_company = Column(String(255))  # Most frequently traded company
    
    # Recent activity
    last_trade_date = Column(DateTime)
    last_trade_ticker = Column(String(10))
    last_trade_type = Column(String(50))
    
    # Performance metrics (can be calculated later)
    avg_return_30d = Column(Float)  # Average return 30 days after purchase
    avg_return_90d = Column(Float)  # Average return 90 days after purchase
    win_rate = Column(Float)  # Percentage of profitable trades
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<TopInsider(name={self.owner_name}, trades={self.total_trades}, value={self.total_value_traded})>"


class InsiderAlert(Base):
    """Store notable insider trading alerts and patterns"""
    __tablename__ = "insider_alerts"
    
    id = Column(Integer, primary_key=True)
    
    # Alert details
    alert_type = Column(String(50))  # "cluster_buying", "unusual_volume", "ceo_purchase", etc.
    ticker = Column(String(10), index=True)
    company_name = Column(String(255))
    
    # Alert metadata
    severity = Column(String(20))  # "low", "medium", "high"
    description = Column(Text)
    
    # Related trades
    related_trade_ids = Column(Text)  # JSON array of InsiderTrade IDs
    total_value = Column(Numeric(15, 2))
    num_insiders = Column(Integer)
    
    # Timing
    alert_date = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Status
    is_active = Column(Integer, default=1)  # Boolean as integer for SQLite compatibility
    resolved_date = Column(DateTime)
    
    def __repr__(self):
        return f"<InsiderAlert(type={self.alert_type}, ticker={self.ticker}, severity={self.severity})>"