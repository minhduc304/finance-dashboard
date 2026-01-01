"""
Consolidated model imports for the application
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import all models (no user/auth - single-user local app)
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
    RedditPost, RedditComment, StockSentiment, SentimentValidationSample
)
from models.alphavantage import (
    TechnicalIndicator, CompanyFundamentals
)

__all__ = [
    'Portfolio', 'Holding', 'Transaction', 'PerformanceHistory', 'Watchlist', 'Alert',
    'StockInfo', 'StockPrice', 'StockNews', 'Earnings', 'Financials',
    'DividendHistory', 'StockSplit', 'AnalystRating',
    'InsiderTrade', 'InsiderSummary', 'TopInsider', 'InsiderAlert',
    'RedditPost', 'RedditComment', 'StockSentiment', 'SentimentValidationSample',
    'TechnicalIndicator', 'CompanyFundamentals'
]