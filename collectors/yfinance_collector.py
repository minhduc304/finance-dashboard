import yfinance as yf
import pandas as pd
import datetime
import pytz
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from models.yfinance import (
    Base, StockInfo, StockPrice, StockNews, Earnings, 
    Financials, DividendHistory, StockSplit, AnalystRating
)


class YFinanceCollector:
    """Collector for Yahoo Finance data"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.session = db_session
        self.timezone = pytz.timezone('US/Eastern')
    
    def collect_stock_info(self, ticker: str) -> Dict[str, Any]:
        """Collect basic stock information and metadata"""
        stock = yf.Ticker(ticker)
        info = stock.info
        
        stock_data = {
            'ticker': ticker.upper(),
            'name': info.get('shortName'),
            'long_name': info.get('longName'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'exchange': info.get('exchange'),
            'quote_type': info.get('quoteType'),
            'website': info.get('website'),
            'description': info.get('longBusinessSummary'),
            'country': info.get('country'),
            'currency': info.get('currency'),
            'market_cap': info.get('marketCap'),
            'enterprise_value': info.get('enterpriseValue'),
            'shares_outstanding': info.get('sharesOutstanding'),
            'float_shares': info.get('floatShares'),
            'beta': info.get('beta'),
            'trailing_pe': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'peg_ratio': info.get('pegRatio'),
            'price_to_book': info.get('priceToBook'),
            'dividend_rate': info.get('dividendRate'),
            'dividend_yield': info.get('dividendYield'),
            'ex_dividend_date': self._convert_timestamp(info.get('exDividendDate')),
            'payout_ratio': info.get('payoutRatio')
        }
        
        if self.session:
            self._upsert_stock_info(stock_data)
        
        return stock_data
    
    def collect_price_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        Collect historical price data
        
        Args:
            ticker: Stock ticker symbol
            period: Valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
            interval: Valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
        """
        stock = yf.Ticker(ticker)
        history = stock.history(period=period, interval=interval)
        
        if history.empty:
            return pd.DataFrame()
        
        history.reset_index(inplace=True)
        history['ticker'] = ticker.upper()
        
        # Calculate daily returns
        history['daily_return'] = history['Close'].pct_change()
        
        # Rename columns to match database schema
        history.rename(columns={
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Adj Close': 'adj_close'
        }, inplace=True)
        
        if self.session:
            self._bulk_insert_prices(history)
        
        return history
    
    def collect_news(self, ticker: str, max_news: int = 50) -> pd.DataFrame:
        """Collect recent news articles for a ticker"""
        news = yf.Search(ticker, news_count=max_news).news
        
        if not news:
            return pd.DataFrame()
        
        # Filter news with related tickers
        filtered_news = [n for n in news if 'relatedTickers' in n]
        
        df = pd.DataFrame(filtered_news)
        
        if df.empty:
            return df
        
        # Process the dataframe
        df['primary_ticker'] = ticker.upper()
        df['publish_time'] = df['providerPublishTime'].map(
            lambda ts: datetime.datetime.fromtimestamp(ts, tz=self.timezone) if pd.notna(ts) else None
        )
        
        # Rename columns to match database schema
        df.rename(columns={
            'title': 'title',
            'link': 'link',
            'publisher': 'publisher',
            'relatedTickers': 'related_tickers'
        }, inplace=True)
        
        # Select relevant columns
        columns = ['title', 'link', 'publisher', 'primary_ticker', 'related_tickers', 'publish_time']
        df = df[columns]
        
        if self.session:
            self._bulk_insert_news(df)
        
        return df
    
    def collect_earnings(self, ticker: str) -> pd.DataFrame:
        """Collect earnings history and estimates"""
        stock = yf.Ticker(ticker)
        
        # Get earnings dates
        earnings_dates = stock.earnings_dates
        if earnings_dates is not None and not earnings_dates.empty:
            earnings_dates.reset_index(inplace=True)
            earnings_dates['ticker'] = ticker.upper()
            
            # Rename columns
            earnings_dates.rename(columns={
                'Earnings Date': 'earnings_date',
                'Reported EPS': 'reported_eps',
                'EPS Estimate': 'estimated_eps',
                'Surprise(%)': 'surprise_percent'
            }, inplace=True)
            
            # Calculate surprise
            if 'reported_eps' in earnings_dates.columns and 'estimated_eps' in earnings_dates.columns:
                earnings_dates['surprise_eps'] = earnings_dates['reported_eps'] - earnings_dates['estimated_eps']
            
            if self.session:
                self._bulk_insert_earnings(earnings_dates)
            
            return earnings_dates
        
        return pd.DataFrame()
    
    def collect_financials(self, ticker: str) -> Dict[str, pd.DataFrame]:
        """Collect financial statements"""
        stock = yf.Ticker(ticker)
        
        financials_data = {}
        
        # Income statement
        if hasattr(stock, 'income_stmt') and stock.income_stmt is not None:
            income = stock.income_stmt.T
            income['ticker'] = ticker.upper()
            income['statement_type'] = 'income'
            income['period_type'] = 'annual'
            financials_data['income'] = income
        
        # Balance sheet
        if hasattr(stock, 'balance_sheet') and stock.balance_sheet is not None:
            balance = stock.balance_sheet.T
            balance['ticker'] = ticker.upper()
            balance['statement_type'] = 'balance'
            balance['period_type'] = 'annual'
            financials_data['balance'] = balance
        
        # Cash flow
        if hasattr(stock, 'cashflow') and stock.cashflow is not None:
            cashflow = stock.cashflow.T
            cashflow['ticker'] = ticker.upper()
            cashflow['statement_type'] = 'cashflow'
            cashflow['period_type'] = 'annual'
            financials_data['cashflow'] = cashflow
        
        # Quarterly financials
        if hasattr(stock, 'quarterly_income_stmt') and stock.quarterly_income_stmt is not None:
            quarterly_income = stock.quarterly_income_stmt.T
            quarterly_income['ticker'] = ticker.upper()
            quarterly_income['statement_type'] = 'income'
            quarterly_income['period_type'] = 'quarterly'
            financials_data['quarterly_income'] = quarterly_income
        
        if self.session:
            for df in financials_data.values():
                self._process_and_store_financials(df)
        
        return financials_data
    
    def collect_dividends(self, ticker: str) -> pd.DataFrame:
        """Collect dividend history"""
        stock = yf.Ticker(ticker)
        dividends = stock.dividends
        
        if dividends is not None and not dividends.empty:
            dividends = dividends.to_frame()
            dividends.reset_index(inplace=True)
            dividends['ticker'] = ticker.upper()
            
            dividends.rename(columns={
                'Date': 'ex_date',
                'Dividends': 'amount'
            }, inplace=True)
            
            if self.session:
                self._bulk_insert_dividends(dividends)
            
            return dividends
        
        return pd.DataFrame()
    
    def collect_splits(self, ticker: str) -> pd.DataFrame:
        """Collect stock split history"""
        stock = yf.Ticker(ticker)
        splits = stock.splits
        
        if splits is not None and not splits.empty:
            splits = splits.to_frame()
            splits.reset_index(inplace=True)
            splits['ticker'] = ticker.upper()
            
            splits.rename(columns={
                'Date': 'split_date',
                'Stock Splits': 'split_factor'
            }, inplace=True)
            
            # Convert split factor to ratio format
            splits['split_ratio'] = splits['split_factor'].apply(self._factor_to_ratio)
            
            if self.session:
                self._bulk_insert_splits(splits)
            
            return splits
        
        return pd.DataFrame()
    
    def collect_analyst_ratings(self, ticker: str) -> Dict[str, Any]:
        """Collect analyst recommendations and price targets"""
        stock = yf.Ticker(ticker)
        
        recommendations = stock.recommendations
        info = stock.info
        
        rating_data = {
            'ticker': ticker.upper(),
            'recommendation': info.get('recommendationKey'),
            'recommendation_mean': info.get('recommendationMean'),
            'target_high': info.get('targetHighPrice'),
            'target_low': info.get('targetLowPrice'),
            'target_mean': info.get('targetMeanPrice'),
            'target_median': info.get('targetMedianPrice'),
            'last_updated': datetime.datetime.now(self.timezone)
        }
        
        # Get analyst count from recommendations if available
        if recommendations is not None and not recommendations.empty:
            latest = recommendations.iloc[-1]
            rating_data.update({
                'strong_buy': latest.get('strongBuy', 0),
                'buy': latest.get('buy', 0),
                'hold': latest.get('hold', 0),
                'sell': latest.get('sell', 0),
                'strong_sell': latest.get('strongSell', 0)
            })
        
        if self.session:
            self._upsert_analyst_rating(rating_data)
        
        return rating_data
    
    def collect_all_data(self, ticker: str, price_period: str = "1y") -> Dict[str, Any]:
        """Collect all available data for a ticker"""
        results = {
            'ticker': ticker.upper(),
            'timestamp': datetime.datetime.now(self.timezone),
            'success': []
        }
        
        # Collect each data type
        try:
            results['info'] = self.collect_stock_info(ticker)
            results['success'].append('info')
        except Exception as e:
            results['info_error'] = str(e)
        
        try:
            results['prices'] = self.collect_price_history(ticker, period=price_period)
            results['success'].append('prices')
        except Exception as e:
            results['prices_error'] = str(e)
        
        try:
            results['news'] = self.collect_news(ticker)
            results['success'].append('news')
        except Exception as e:
            results['news_error'] = str(e)
        
        try:
            results['earnings'] = self.collect_earnings(ticker)
            results['success'].append('earnings')
        except Exception as e:
            results['earnings_error'] = str(e)
        
        try:
            results['financials'] = self.collect_financials(ticker)
            results['success'].append('financials')
        except Exception as e:
            results['financials_error'] = str(e)
        
        try:
            results['dividends'] = self.collect_dividends(ticker)
            results['success'].append('dividends')
        except Exception as e:
            results['dividends_error'] = str(e)
        
        try:
            results['splits'] = self.collect_splits(ticker)
            results['success'].append('splits')
        except Exception as e:
            results['splits_error'] = str(e)
        
        try:
            results['analyst_ratings'] = self.collect_analyst_ratings(ticker)
            results['success'].append('analyst_ratings')
        except Exception as e:
            results['analyst_ratings_error'] = str(e)
        
        return results
    
    # Helper methods for database operations
    def _convert_timestamp(self, timestamp):
        """Convert Unix timestamp to datetime"""
        if timestamp:
            return datetime.datetime.fromtimestamp(timestamp, tz=self.timezone)
        return None
    
    def _factor_to_ratio(self, factor):
        """Convert split factor to ratio string"""
        if factor >= 1:
            return f"{int(factor)}:1"
        else:
            return f"1:{int(1/factor)}"
    
    def _upsert_stock_info(self, data):
        """Upsert stock info to database"""
        if not self.session:
            return
        
        existing = self.session.query(StockInfo).filter_by(ticker=data['ticker']).first()
        if existing:
            for key, value in data.items():
                if value is not None:
                    setattr(existing, key, value)
        else:
            stock_info = StockInfo(**data)
            self.session.add(stock_info)
        
        self.session.commit()
    
    def _bulk_insert_prices(self, df):
        """Bulk insert price data"""
        if not self.session or df.empty:
            return
        
        # Convert DataFrame to list of dictionaries
        records = df.to_dict('records')
        
        # Insert in batches to avoid conflicts
        for record in records:
            # Check if record exists
            existing = self.session.query(StockPrice).filter_by(
                ticker=record['ticker'],
                date=record['date']
            ).first()
            
            if not existing:
                price = StockPrice(**record)
                self.session.add(price)
        
        self.session.commit()
    
    def _bulk_insert_news(self, df):
        """Bulk insert news data"""
        if not self.session or df.empty:
            return
        
        records = df.to_dict('records')
        
        for record in records:
            # Check for duplicate by link
            existing = self.session.query(StockNews).filter_by(link=record['link']).first()
            if not existing:
                news = StockNews(**record)
                self.session.add(news)
        
        self.session.commit()
    
    def _bulk_insert_earnings(self, df):
        """Bulk insert earnings data"""
        if not self.session or df.empty:
            return
        
        records = df.to_dict('records')
        
        for record in records:
            # Clean the record
            clean_record = {k: v for k, v in record.items() if pd.notna(v)}
            
            # Check for existing record
            if 'earnings_date' in clean_record:
                existing = self.session.query(Earnings).filter_by(
                    ticker=clean_record['ticker'],
                    earnings_date=clean_record['earnings_date']
                ).first()
                
                if not existing:
                    earnings = Earnings(**clean_record)
                    self.session.add(earnings)
        
        self.session.commit()
    
    def _process_and_store_financials(self, df):
        """Process and store financial statements"""
        if not self.session or df.empty:
            return
        
        # This would need more processing based on actual column names
        # For now, storing raw data
        pass
    
    def _bulk_insert_dividends(self, df):
        """Bulk insert dividend data"""
        if not self.session or df.empty:
            return
        
        records = df.to_dict('records')
        
        for record in records:
            existing = self.session.query(DividendHistory).filter_by(
                ticker=record['ticker'],
                ex_date=record['ex_date']
            ).first()
            
            if not existing:
                dividend = DividendHistory(**record)
                self.session.add(dividend)
        
        self.session.commit()
    
    def _bulk_insert_splits(self, df):
        """Bulk insert split data"""
        if not self.session or df.empty:
            return
        
        records = df.to_dict('records')
        
        for record in records:
            existing = self.session.query(StockSplit).filter_by(
                ticker=record['ticker'],
                split_date=record['split_date']
            ).first()
            
            if not existing:
                split = StockSplit(**record)
                self.session.add(split)
        
        self.session.commit()
    
    def _upsert_analyst_rating(self, data):
        """Upsert analyst rating data"""
        if not self.session:
            return
        
        existing = self.session.query(AnalystRating).filter_by(ticker=data['ticker']).first()
        if existing:
            for key, value in data.items():
                if value is not None:
                    setattr(existing, key, value)
        else:
            rating = AnalystRating(**data)
            self.session.add(rating)
        
        self.session.commit()


# Example usage and testing
if __name__ == "__main__":
    # Example without database connection (returns DataFrames/dicts)
    collector = YFinanceCollector()
    
    # Test individual collection methods
    ticker = "AAPL"
    
    print(f"\nCollecting data for {ticker}...")
    
    # Collect stock info
    info = collector.collect_stock_info(ticker)
    print(f"\nStock Info: {info.get('name')} ({info.get('ticker')})")
    print(f"Sector: {info.get('sector')}, Industry: {info.get('industry')}")
    
    # Collect recent prices
    prices = collector.collect_price_history(ticker, period="1mo")
    if not prices.empty:
        print(f"\nPrice History: {len(prices)} days collected")
        print(f"Latest close: ${prices.iloc[-1]['close']:.2f}")
    
    # Collect news
    news = collector.collect_news(ticker, max_news=10)
    if not news.empty:
        print(f"\nNews: {len(news)} articles collected")
        print(f"Latest: {news.iloc[0]['title'][:80]}...")
    
    # Collect all data at once
    all_data = collector.collect_all_data(ticker, price_period="3mo")
    print(f"\nSuccessfully collected: {', '.join(all_data['success'])}")
    
    # Example with database connection
    # from sqlalchemy import create_engine
    # from sqlalchemy.orm import sessionmaker
    # 
    # engine = create_engine('postgresql://username:password@localhost/finance_db')
    # Base.metadata.create_all(engine)
    # Session = sessionmaker(bind=engine)
    # session = Session()
    # 
    # collector_with_db = YFinanceCollector(db_session=session)
    # collector_with_db.collect_all_data("AAPL")