"""
Background tasks for data collection and processing
Handles database persistence for pure data collectors
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def collect_market_data(self, tickers=None):
    """Collect market data and save to database"""
    try:
        from collectors.yfinance_collector import YFinanceCollector
        from backend.app.core.database import SessionLocal
        from backend.app.models import StockInfo, StockPrice, Watchlist

        collector = YFinanceCollector()
        db = SessionLocal()

        # Get tickers to update
        if not tickers:
            watchlists = db.query(Watchlist).all()
            tickers = set()
            for watchlist in watchlists:
                if watchlist.tickers:
                    tickers.update(watchlist.tickers)

        if not tickers:
            tickers = ["SPY", "QQQ", "DIA", "AAPL", "MSFT", "GOOGL"]

        results = []
        for ticker in tickers:
            try:
                # Collect data
                info = collector.collect_stock_info(ticker)
                prices = collector.collect_price_history(ticker, period="1d")

                # Save stock info
                existing = db.query(StockInfo).filter_by(ticker=ticker.upper()).first()
                if existing:
                    for key, value in info.items():
                        if value is not None:
                            setattr(existing, key, value)
                else:
                    stock = StockInfo(**info)
                    db.add(stock)

                # Save price data
                if not prices.empty:
                    for _, row in prices.iterrows():
                        existing_price = db.query(StockPrice).filter_by(
                            ticker=ticker.upper(),
                            date=row['date']
                        ).first()

                        if not existing_price:
                            price_data = row.to_dict()
                            price = StockPrice(**price_data)
                            db.add(price)

                db.commit()
                results.append(ticker)

            except Exception as e:
                logger.error(f"Failed to update {ticker}: {e}")
                db.rollback()

        db.close()
        return {"status": "success", "tickers_updated": results}

    except Exception as e:
        logger.error(f"Market data collection failed: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def collect_reddit_sentiment(self):
    """Collect Reddit sentiment data and save to database"""
    try:
        from collectors.reddit_collector import RedditCollector
        from backend.app.core.database import SessionLocal
        from backend.app.models import RedditPost, RedditComment, StockSentiment

        collector = RedditCollector()
        db = SessionLocal()

        # Collect trending data
        trending_data = collector.collect_trending_stocks(posts_per_sub=10)

        # Save posts from trending data collection
        for subreddit in collector.subreddits[:5]:  # Limit to top 5 subreddits
            posts = collector.collect_posts(subreddit, limit=20)

            for post_data in posts:
                # Check if post exists
                existing = db.query(RedditPost).filter_by(
                    reddit_id=post_data['reddit_id']
                ).first()

                if not existing:
                    post = RedditPost(**post_data)
                    db.add(post)
                    db.commit()

                    # Collect and save comments
                    comments = collector.collect_comments(post_data['reddit_id'], limit=10)
                    for comment_data in comments:
                        comment = RedditComment(
                            post_id=post.id,
                            **comment_data
                        )
                        db.add(comment)

        # Save sentiment summary by ticker
        for ticker, sentiment_avg in trending_data['ticker_sentiment'].items():
            sentiment_summary = StockSentiment(
                ticker=ticker,
                source='reddit',
                sentiment_score=sentiment_avg,
                mentions_count=trending_data['trending_tickers'].get(ticker, 0),
                date=datetime.utcnow().date()
            )
            db.add(sentiment_summary)

        db.commit()
        db.close()

        return {
            "status": "success",
            "trending_tickers": list(trending_data['trending_tickers'].keys())[:10],
            "posts_analyzed": trending_data['total_posts_analyzed']
        }

    except Exception as e:
        logger.error(f"Reddit sentiment collection failed: {e}")
        raise self.retry(exc=e, countdown=300)


@shared_task(bind=True, max_retries=3)
def collect_insider_trading(self):
    """Collect insider trading data and save to database"""
    try:
        from collectors.openinsider_collector import OpenInsiderCollector
        from backend.app.core.database import SessionLocal
        from backend.app.models import InsiderTrade

        collector = OpenInsiderCollector()
        db = SessionLocal()

        # Collect latest trades
        trades = collector.scrape_latest_trades(pages=2)

        saved_count = 0
        for trade_data in trades:
            # Check if trade exists
            existing = db.query(InsiderTrade).filter_by(
                ticker=trade_data.get('ticker'),
                insider_name=trade_data.get('insider_name'),
                filing_date=trade_data.get('filing_date')
            ).first()

            if not existing:
                trade = InsiderTrade(
                    ticker=trade_data.get('ticker'),
                    company_name=trade_data.get('company_name'),
                    insider_name=trade_data.get('insider_name'),
                    insider_title=trade_data.get('insider_title'),
                    trade_type=trade_data.get('trade_type'),
                    price=trade_data.get('price'),
                    quantity=trade_data.get('quantity'),
                    value=trade_data.get('value'),
                    filing_date=trade_data.get('filing_date')
                )
                db.add(trade)
                saved_count += 1

        db.commit()
        db.close()

        return {"status": "success", "trades_saved": saved_count}

    except Exception as e:
        logger.error(f"Insider trading collection failed: {e}")
        raise self.retry(exc=e, countdown=600)


@shared_task(bind=True, max_retries=2)
def sync_wealthsimple_portfolios(self, user_id: int = None):
    """Sync Wealthsimple portfolio data and save to database"""
    try:
        from collectors.wealthsimple_collector import WealthsimpleCollector
        from backend.app.core.database import SessionLocal
        from backend.app.models import User, Portfolio, Holding, Transaction

        collector = WealthsimpleCollector()
        db = SessionLocal()

        # Get user credentials (in production, decrypt these)
        if user_id:
            user = db.query(User).get(user_id)
            if not user:
                return {"status": "failed", "error": "User not found"}
        else:
            # Default user for development
            user = db.query(User).first()
            if not user:
                return {"status": "failed", "error": "No user found"}

        # Authenticate (this would use stored credentials in production)
        if not collector.authenticate():
            return {"status": "failed", "error": "Authentication failed"}

        # Collect portfolio data
        portfolio_data = collector.collect_all_data()

        # Save portfolio summary
        for account_data in portfolio_data['portfolio_summary']['accounts']:
            portfolio = db.query(Portfolio).filter_by(
                user_id=user.id,
                name=account_data['description']
            ).first()

            if not portfolio:
                portfolio = Portfolio(
                    user_id=user.id,
                    name=account_data['description']
                )
                db.add(portfolio)

            portfolio.total_value = account_data['value']
            portfolio.cash_balance = account_data['cash_balance']
            portfolio.updated_at = datetime.utcnow()

            db.commit()

            # Clear existing holdings for fresh update
            db.query(Holding).filter_by(portfolio_id=portfolio.id).delete()

            # Save holdings
            for holding_data in portfolio_data['holdings']:
                if holding_data['account_id'] == account_data['id']:
                    holding = Holding(
                        portfolio_id=portfolio.id,
                        symbol=holding_data['symbol'],
                        quantity=holding_data['quantity'],
                        average_cost=holding_data['average_cost'],
                        current_price=holding_data['current_price'],
                        market_value=holding_data['market_value'],
                        gain_loss=holding_data['gain_loss']
                    )
                    db.add(holding)

            # Save transactions
            for trans_data in portfolio_data['transactions']:
                if trans_data['account_id'] == account_data['id']:
                    # Check if transaction exists
                    existing = db.query(Transaction).filter_by(
                        portfolio_id=portfolio.id,
                        transaction_date=trans_data['transaction_date']
                    ).first()

                    if not existing:
                        transaction = Transaction(
                            portfolio_id=portfolio.id,
                            type=trans_data['type'],
                            symbol=trans_data['symbol'],
                            quantity=trans_data['quantity'],
                            price=trans_data['price'],
                            total_amount=trans_data['total_amount'],
                            transaction_date=trans_data['transaction_date']
                        )
                        db.add(transaction)

        db.commit()
        db.close()

        return {
            "status": "success",
            "portfolios_updated": len(portfolio_data['portfolio_summary']['accounts']),
            "holdings_count": len(portfolio_data['holdings']),
            "transactions_count": len(portfolio_data['transactions'])
        }

    except Exception as e:
        logger.error(f"Wealthsimple portfolio sync failed: {e}")
        raise self.retry(exc=e, countdown=300)


@shared_task(bind=True, max_retries=3)
def update_portfolio_values(self):
    """Update all portfolio values with latest market prices"""
    try:
        from backend.app.core.database import SessionLocal
        from backend.app.models import Portfolio, Holding, StockPrice

        db = SessionLocal()

        portfolios = db.query(Portfolio).all()
        updated_count = 0

        for portfolio in portfolios:
            total_value = portfolio.cash_balance or 0

            for holding in portfolio.holdings:
                # Get latest price
                latest_price = db.query(StockPrice).filter(
                    StockPrice.ticker == holding.ticker
                ).order_by(StockPrice.date.desc()).first()

                if latest_price:
                    holding.current_price = float(latest_price.close)
                    holding.market_value = float(holding.quantity) * float(latest_price.close)
                    holding.unrealized_gain = holding.market_value - (float(holding.quantity) * float(holding.average_cost))
                    total_value += holding.market_value

            portfolio.total_value = total_value
            portfolio.total_gain_loss = total_value - portfolio.total_cost
            portfolio.updated_at = datetime.utcnow()
            updated_count += 1

        db.commit()
        db.close()

        return {"status": "success", "portfolios_updated": updated_count}

    except Exception as e:
        logger.error(f"Portfolio update failed: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task
def cleanup_old_data():
    """Clean up old data from database"""
    try:
        from backend.app.core.database import SessionLocal
        from backend.app.models import StockPrice, StockNews, RedditPost

        db = SessionLocal()
        cutoff_date = datetime.utcnow() - timedelta(days=90)

        # Delete old price data
        deleted_prices = db.query(StockPrice).filter(
            StockPrice.date < cutoff_date
        ).delete()

        # Delete old news
        news_cutoff = datetime.utcnow() - timedelta(days=30)
        deleted_news = db.query(StockNews).filter(
            StockNews.published_at < news_cutoff
        ).delete()

        # Delete old reddit posts
        reddit_cutoff = datetime.utcnow() - timedelta(days=7)
        deleted_posts = db.query(RedditPost).filter(
            RedditPost.created_utc < reddit_cutoff
        ).delete()

        db.commit()
        db.close()

        return {
            "status": "success",
            "deleted": {
                "prices": deleted_prices,
                "news": deleted_news,
                "posts": deleted_posts
            }
        }

    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task(bind=True, max_retries=2)
def analyze_ticker_sentiment(self, ticker: str):
    """Analyze sentiment for a specific ticker across all sources"""
    try:
        from collectors.reddit_collector import RedditCollector
        from backend.app.core.database import SessionLocal
        from backend.app.models import StockSentiment

        collector = RedditCollector()
        db = SessionLocal()

        # Collect posts mentioning this ticker
        all_sentiments = []
        for subreddit in collector.subreddits[:3]:
            posts = collector.collect_posts(subreddit, limit=50)
            for post in posts:
                if post['mentioned_tickers'] and ticker.upper() in post['mentioned_tickers']:
                    all_sentiments.append({
                        'score': post['sentiment_score'],
                        'label': post['sentiment_label']
                    })

        if all_sentiments:
            avg_sentiment = sum(s['score'] for s in all_sentiments) / len(all_sentiments)
            positive_count = sum(1 for s in all_sentiments if s['label'] == 'positive')
            negative_count = sum(1 for s in all_sentiments if s['label'] == 'negative')

            # Save to database
            sentiment_record = StockSentiment(
                ticker=ticker.upper(),
                source='reddit_analysis',
                sentiment_score=avg_sentiment,
                positive_mentions=positive_count,
                negative_mentions=negative_count,
                mentions_count=len(all_sentiments),
                date=datetime.utcnow().date()
            )
            db.add(sentiment_record)
            db.commit()
            db.close()

            return {
                "status": "success",
                "ticker": ticker.upper(),
                "sentiment_score": avg_sentiment,
                "total_mentions": len(all_sentiments)
            }

        db.close()
        return {"status": "no_data", "ticker": ticker.upper()}

    except Exception as e:
        logger.error(f"Ticker sentiment analysis failed: {e}")
        raise self.retry(exc=e, countdown=120)