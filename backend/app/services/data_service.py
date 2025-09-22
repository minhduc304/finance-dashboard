"""
Data service layer - orchestrates collectors and database operations
Provides clean interface for API endpoints
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone, date
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)


class DataService:
    """Service layer for data operations"""

    @staticmethod
    def get_stock_data(ticker: str, db_session) -> Dict[str, Any]:
        """Get stock data from database or fetch if needed"""
        from backend.app.models import StockInfo, StockPrice
        from collectors.yfinance_collector import YFinanceCollector

        # Try to get from database first
        stock_info = db_session.query(StockInfo).filter_by(ticker=ticker.upper()).first()

        if not stock_info or (stock_info.updated_at and
                             stock_info.updated_at < datetime.now(timezone.utc) - timedelta(hours=24)):
            # Data is stale or doesn't exist, fetch fresh data
            collector = YFinanceCollector()
            fresh_data = collector.collect_stock_info(ticker)

            if stock_info:
                # Update existing
                for key, value in fresh_data.items():
                    if value is not None:
                        setattr(stock_info, key, value)
            else:
                # Create new
                stock_info = StockInfo(**fresh_data)
                db_session.add(stock_info)

            db_session.commit()

        # Get recent prices
        recent_prices = db_session.query(StockPrice).filter_by(
            ticker=ticker.upper()
        ).order_by(StockPrice.date.desc()).limit(30).all()

        return {
            "info": {
                "ticker": stock_info.ticker,
                "name": stock_info.name,
                "sector": stock_info.sector,
                "market_cap": stock_info.market_cap,
                "pe_ratio": stock_info.pe_ratio,
                "dividend_yield": stock_info.dividend_yield
            },
            "prices": [
                {
                    "date": p.date,
                    "open": p.open,
                    "high": p.high,
                    "low": p.low,
                    "close": p.close,
                    "volume": p.volume
                } for p in recent_prices
            ]
        }

    @staticmethod
    def get_trending_stocks(db_session) -> Dict[str, Any]:
        """Get trending stocks from Reddit sentiment"""
        from backend.app.models import StockSentiment

        # Get today's sentiment data
        today_sentiment = db_session.query(StockSentiment).filter(
            StockSentiment.date == date.today()
        ).order_by(StockSentiment.mentions_count.desc()).limit(20).all()

        if not today_sentiment:
            # No data for today, trigger collection
            from backend.app.tasks import collect_reddit_sentiment
            collect_reddit_sentiment.delay()
            return {"message": "Data collection initiated, check back soon"}

        return {
            "trending": [
                {
                    "ticker": s.ticker,
                    "mentions": s.mentions_count,
                    "sentiment_score": s.sentiment_score,
                    "source": s.source
                } for s in today_sentiment
            ],
            "updated_at": datetime.now(timezone.utc)
        }

    @staticmethod
    def get_insider_trades(ticker: Optional[str], db_session) -> List[Dict]:
        """Get insider trading data"""
        from backend.app.models import InsiderTrade

        query = db_session.query(InsiderTrade)
        if ticker:
            query = query.filter_by(ticker=ticker.upper())

        trades = query.order_by(InsiderTrade.filing_date.desc()).limit(100).all()

        return [
            {
                "ticker": t.ticker,
                "company": t.company_name,
                "insider": t.insider_name,
                "title": t.insider_title,
                "type": t.trade_type,
                "price": t.price,
                "quantity": t.quantity,
                "value": t.value,
                "filing_date": t.filing_date
            } for t in trades
        ]

    @staticmethod
    def collect_fresh_data(ticker: str) -> Dict[str, Any]:
        """Collect fresh data for a ticker without saving to DB"""
        from collectors.yfinance_collector import YFinanceCollector
        from collectors.reddit_collector import RedditCollector

        results = {}

        # Collect market data
        try:
            yf_collector = YFinanceCollector()
            results['market'] = yf_collector.collect_all(ticker)
        except Exception as e:
            results['market_error'] = str(e)

        # Collect Reddit sentiment
        try:
            reddit_collector = RedditCollector()
            posts = []
            for subreddit in reddit_collector.subreddits[:3]:
                subreddit_posts = reddit_collector.collect_posts(subreddit, limit=10)
                for post in subreddit_posts:
                    if post['mentioned_tickers'] and ticker.upper() in post['mentioned_tickers']:
                        posts.append(post)

            results['reddit'] = {
                'posts_mentioning': len(posts),
                'average_sentiment': sum(p['sentiment_score'] for p in posts) / len(posts) if posts else 0
            }
        except Exception as e:
            results['reddit_error'] = str(e)

        return results

    @staticmethod
    def update_portfolio(portfolio_id: int, db_session) -> Dict[str, Any]:
        """Update portfolio values with latest prices"""
        from backend.app.models import Portfolio, Holding, StockPrice

        portfolio = db_session.query(Portfolio).get(portfolio_id)
        if not portfolio:
            return {"error": "Portfolio not found"}

        total_value = portfolio.cash_balance or 0
        updated_holdings = []

        for holding in portfolio.holdings:
            # Get latest price
            latest_price = db_session.query(StockPrice).filter(
                StockPrice.ticker == holding.ticker
            ).order_by(StockPrice.date.desc()).first()

            if latest_price:
                holding.current_price = float(latest_price.close)
                holding.market_value = float(holding.quantity) * float(latest_price.close)
                holding.unrealized_gain = holding.market_value - (float(holding.quantity) * float(holding.average_cost))
                total_value += holding.market_value

                updated_holdings.append({
                    "ticker": holding.ticker,
                    "quantity": holding.quantity,
                    "current_price": holding.current_price,
                    "market_value": holding.market_value,
                    "unrealized_gain": holding.unrealized_gain
                })

        portfolio.total_value = total_value
        portfolio.total_gain_loss = total_value - portfolio.total_cost
        portfolio.updated_at = datetime.now(timezone.utc)

        db_session.commit()

        return {
            "portfolio_id": portfolio.id,
            "total_value": portfolio.total_value,
            "total_gain_loss": portfolio.total_gain_loss,
            "holdings": updated_holdings,
            "updated_at": portfolio.updated_at
        }