"""
Alpha Vantage data collector for technical indicators and fundamentals
API Key: AP94QIZQCM2AJ6QZ (from .env)
Free tier: 25 requests/day, 5 requests/minute
"""

import requests
import time
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AlphaVantageCollector:
    """Alpha Vantage API collector - complements YFinance with technical data"""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.last_request_time = 0
        self.min_request_interval = 12  # 5 requests/min = 12s between requests

    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Make API request with rate limiting"""
        self._rate_limit()
        params['apikey'] = self.api_key

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Check for API error messages
            if 'Error Message' in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return {}

            if 'Note' in data:
                logger.warning(f"Alpha Vantage API limit: {data['Note']}")
                return {}

            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {}

    def get_global_quote(self, ticker: str) -> Dict[str, Any]:
        """Get real-time quote"""
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': ticker
        }
        data = self._make_request(params)
        quote = data.get('Global Quote', {})

        if not quote:
            return {}

        return {
            'ticker': ticker,
            'price': float(quote.get('05. price', 0)),
            'change': float(quote.get('09. change', 0)),
            'change_percent': quote.get('10. change percent', '0%').strip('%'),
            'volume': int(quote.get('06. volume', 0)),
            'latest_trading_day': quote.get('07. latest trading day'),
            'previous_close': float(quote.get('08. previous close', 0))
        }

    def get_technical_indicator(self, ticker: str, indicator: str,
                                interval: str = 'daily', time_period: int = 14,
                                series_type: str = 'close') -> pd.DataFrame:
        """
        Get technical indicators
        Indicators: RSI, MACD, SMA, EMA, BBANDS, ADX, CCI, STOCH
        """
        params = {
            'function': indicator,
            'symbol': ticker,
            'interval': interval,
            'time_period': time_period,
            'series_type': series_type
        }
        data = self._make_request(params)

        if not data:
            return pd.DataFrame()

        # Parse time series data
        indicator_key = f'Technical Analysis: {indicator}'
        if indicator_key in data:
            df = pd.DataFrame.from_dict(data[indicator_key], orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.apply(pd.to_numeric, errors='coerce')
            return df.sort_index()

        return pd.DataFrame()

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float, handling 'None' strings and empty values"""
        if value is None or value == '' or value == 'None':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def get_company_overview(self, ticker: str) -> Dict[str, Any]:
        """Get fundamental company data"""
        params = {
            'function': 'OVERVIEW',
            'symbol': ticker
        }
        data = self._make_request(params)

        if not data:
            return {}

        return {
            'ticker': ticker,
            'name': data.get('Name'),
            'description': data.get('Description'),
            'sector': data.get('Sector'),
            'industry': data.get('Industry'),
            'market_cap': self._safe_float(data.get('MarketCapitalization')),
            'ebitda': self._safe_float(data.get('EBITDA')),
            'pe_ratio': self._safe_float(data.get('PERatio')),
            'peg_ratio': self._safe_float(data.get('PEGRatio')),
            'book_value': self._safe_float(data.get('BookValue')),
            'dividend_per_share': self._safe_float(data.get('DividendPerShare')),
            'dividend_yield': self._safe_float(data.get('DividendYield')),
            'eps': self._safe_float(data.get('EPS')),
            'revenue_per_share': self._safe_float(data.get('RevenuePerShareTTM')),
            'profit_margin': self._safe_float(data.get('ProfitMargin')),
            'operating_margin': self._safe_float(data.get('OperatingMarginTTM')),
            'return_on_assets': self._safe_float(data.get('ReturnOnAssetsTTM')),
            'return_on_equity': self._safe_float(data.get('ReturnOnEquityTTM')),
            'revenue_ttm': self._safe_float(data.get('RevenueTTM')),
            'gross_profit_ttm': self._safe_float(data.get('GrossProfitTTM')),
            '52_week_high': self._safe_float(data.get('52WeekHigh')),
            '52_week_low': self._safe_float(data.get('52WeekLow')),
            '50_day_ma': self._safe_float(data.get('50DayMovingAverage')),
            '200_day_ma': self._safe_float(data.get('200DayMovingAverage')),
            'analyst_target_price': self._safe_float(data.get('AnalystTargetPrice'))
        }

    def get_rsi(self, ticker: str, time_period: int = 14) -> pd.DataFrame:
        """Get RSI (Relative Strength Index)"""
        return self.get_technical_indicator(ticker, 'RSI', time_period=time_period)

    def get_macd(self, ticker: str) -> pd.DataFrame:
        """Get MACD (Moving Average Convergence Divergence)"""
        params = {
            'function': 'MACD',
            'symbol': ticker,
            'interval': 'daily',
            'series_type': 'close'
        }
        data = self._make_request(params)

        if not data:
            return pd.DataFrame()

        indicator_key = 'Technical Analysis: MACD'
        if indicator_key in data:
            df = pd.DataFrame.from_dict(data[indicator_key], orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.apply(pd.to_numeric, errors='coerce')
            return df.sort_index()

        return pd.DataFrame()
