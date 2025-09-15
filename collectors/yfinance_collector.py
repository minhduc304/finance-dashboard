import yfinance as yf
import pandas as pd
import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

class YFinanceCollector:
    """Simplified Yahoo Finance data collector"""

    def __init__(self, db_session: Optional[Session] = None):
        self.session = db_session

    def collect_stock_info(self, ticker: str) -> Dict[str, Any]:
        """Collect basic stock information"""
        stock = yf.Ticker(ticker)
        info = stock.info

        return {
            'ticker': ticker.upper(),
            'name': info.get('shortName'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE'),
            'dividend_yield': info.get('dividendYield'),
            'beta': info.get('beta')
        }

    def collect_price_history(self, ticker: str, period: str = "1mo") -> pd.DataFrame:
        """Collect historical price data"""
        stock = yf.Ticker(ticker)
        history = stock.history(period=period)

        if not history.empty:
            history.reset_index(inplace=True)
            history['ticker'] = ticker.upper()
            history.columns = history.columns.str.lower()
            history.rename(columns={'adj close': 'adj_close'}, inplace=True)

        return history

    def collect_news(self, ticker: str, max_items: int = 10) -> list:
        """Collect recent news"""
        stock = yf.Ticker(ticker)
        news = stock.news[:max_items] if hasattr(stock, 'news') else []

        return [{
            'title': item.get('title'),
            'link': item.get('link'),
            'publisher': item.get('publisher'),
            'publish_time': datetime.datetime.fromtimestamp(item.get('providerPublishTime', 0))
        } for item in news]

    def collect_all(self, ticker: str) -> Dict[str, Any]:
        """Collect all available data for a ticker"""
        return {
            'info': self.collect_stock_info(ticker),
            'prices': self.collect_price_history(ticker),
            'news': self.collect_news(ticker)
        }