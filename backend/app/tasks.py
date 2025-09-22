"""
Background tasks for data collection and processing
Handles database persistence for pure data collectors
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta, timezone
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=2)
def sync_wealthsimple_portfolios(self):
    """Sync Wealthsimple portfolio data and save to database"""
    try:
        from collectors.wealthsimple_collector import WealthsimpleCollector
        from backend.app.core.database import SessionLocal
        from backend.app.models import Portfolio, Holding, Transaction

        collector = WealthsimpleCollector()
        db = SessionLocal()

        # Authenticate with Wealthsimple (credentials from environment/config)
        if not collector.authenticate():
            return {"status": "failed", "error": "Authentication failed"}

        # Collect portfolio data
        portfolio_data = collector.collect_all_data()

        # Save portfolio summary
        for account_data in portfolio_data['portfolio_summary']['accounts']:
            portfolio = db.query(Portfolio).filter_by(
                name=account_data['description']
            ).first()

            if not portfolio:
                portfolio = Portfolio(
                    name=account_data['description']
                )
                db.add(portfolio)

            portfolio.total_value = account_data['value']
            portfolio.cash_balance = account_data['cash_balance']
            portfolio.updated_at = datetime.now(timezone.utc)

            db.commit()

            # Clear existing holdings for fresh update
            db.query(Holding).filter_by(portfolio_id=portfolio.id).delete()

            # Save holdings
            for holding_data in portfolio_data['holdings']:
                if holding_data['account_id'] == account_data['id']:
                    holding = Holding(
                        portfolio_id=portfolio.id,
                        ticker=holding_data['symbol'],
                        name=holding_data.get('name'),
                        quantity=holding_data['quantity'],
                        average_cost=holding_data['average_cost'],
                        current_price=holding_data['current_price'],
                        market_value=holding_data['market_value'],
                        unrealized_gain=holding_data.get('gain_loss', 0)
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
def collect_market_data(self, tickers=None):
    """Collect market data and save to database"""
    try:
        from collectors.yfinance_collector import YFinanceCollector
        from backend.app.core.database import SessionLocal
        from backend.app.models import StockInfo, StockPrice, Watchlist, Holding

        collector = YFinanceCollector()
        db = SessionLocal()

        # Get tickers to update - prioritize portfolio holdings over watchlists
        if not tickers:
            # First try to get tickers from portfolio holdings
            holdings = db.query(Holding).all()
            tickers = set()
            for holding in holdings:
                if holding.ticker:
                    tickers.add(holding.ticker)

            # If no holdings, fall back to watchlists
            if not tickers:
                watchlists = db.query(Watchlist).all()
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
                        # Remove invalid field and create comment with correct mapping
                        if 'post_reddit_id' in comment_data:
                            del comment_data['post_reddit_id']

                        comment = RedditComment(
                            post_id=post.id,
                            reddit_id=comment_data.get('reddit_id'),
                            author=comment_data.get('author'),
                            content=comment_data.get('content'),
                            score=comment_data.get('score', 0),
                            mentioned_tickers=comment_data.get('mentioned_tickers'),
                            sentiment_score=comment_data.get('sentiment_score'),
                            sentiment_label=comment_data.get('sentiment_label'),
                            created_utc=comment_data.get('created_utc'),
                            scraped_at=comment_data.get('scraped_at', )
                        )
                        db.add(comment)

        # Save sentiment summary by ticker
        for ticker, sentiment_avg in trending_data['ticker_sentiment'].items():
            sentiment_summary = StockSentiment(
                ticker=ticker,
                avg_sentiment=sentiment_avg,  # Use correct field name
                total_mentions=trending_data['trending_tickers'].get(ticker, 0),  # Use correct field name
                date=datetime.now(timezone.utc).date()  # Should be date, not datetime
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
            # Check if trade exists (use correct field mapping)
            existing = db.query(InsiderTrade).filter_by(
                ticker=trade_data.get('ticker'),
                owner_name=trade_data.get('insider_name'),  # Map insider_name to owner_name
                transaction_date=trade_data.get('filing_date')  # Map filing_date to transaction_date
            ).first()

            if not existing:
                trade = InsiderTrade(
                    ticker=trade_data.get('ticker'),
                    company_name=trade_data.get('company_name'),
                    owner_name=trade_data.get('insider_name'),  # Map insider_name to owner_name
                    title=trade_data.get('insider_title'),  # Map insider_title to title
                    transaction_type=trade_data.get('trade_type'),  # Map trade_type to transaction_type
                    last_price=trade_data.get('price'),  # Map price to last_price
                    quantity=trade_data.get('quantity'),
                    value=trade_data.get('value'),
                    transaction_date=trade_data.get('filing_date'),  # Map filing_date to transaction_date
                    trade_date=trade_data.get('filing_date')  # Use filing_date for trade_date too
                )
                db.add(trade)
                saved_count += 1

        db.commit()
        db.close()

        return {"status": "success", "trades_saved": saved_count}

    except Exception as e:
        logger.error(f"Insider trading collection failed: {e}")
        raise self.retry(exc=e, countdown=600)




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
            portfolio.updated_at = datetime.now(timezone.utc)
            updated_count += 1

        db.commit()
        db.close()

        return {"status": "success", "portfolios_updated": updated_count}

    except Exception as e:
        logger.error(f"Portfolio update failed: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=2)
def populate_watchlist_from_holdings(self):
    """Create or update watchlist based on current portfolio holdings"""
    try:
        from backend.app.core.database import SessionLocal
        from backend.app.models import Holding, Watchlist

        db = SessionLocal()

        # Get all unique tickers from holdings
        holdings = db.query(Holding).all()
        tickers = set()
        for holding in holdings:
            if holding.ticker:
                tickers.add(holding.ticker.upper())

        if not tickers:
            logger.info("No holdings found, skipping watchlist update")
            db.close()
            return {"status": "no_data", "message": "No holdings found"}

        # Find or create default watchlist
        watchlist = db.query(Watchlist).filter_by(is_default=True).first()
        if not watchlist:
            watchlist = Watchlist(
                name="Portfolio Holdings",
                description="Auto-generated from current portfolio holdings",
                tickers=list(tickers),
                is_default=True,
                is_public=False
            )
            db.add(watchlist)
        else:
            # Update existing watchlist
            watchlist.tickers = list(tickers)
            watchlist.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.close()

        return {
            "status": "success",
            "watchlist_name": watchlist.name,
            "tickers_count": len(tickers),
            "tickers": list(tickers)
        }

    except Exception as e:
        logger.error(f"Watchlist population failed: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task
def cleanup_old_data():
    """Clean up old data from database"""
    try:
        from backend.app.core.database import SessionLocal
        from backend.app.models import StockPrice, StockNews, RedditPost

        db = SessionLocal()
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)

        # Delete old price data
        deleted_prices = db.query(StockPrice).filter(
            StockPrice.date < cutoff_date
        ).delete()

        # Delete old news
        news_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        deleted_news = db.query(StockNews).filter(
            StockNews.published_at < news_cutoff
        ).delete()

        # Delete old reddit posts
        reddit_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
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
                avg_sentiment=avg_sentiment, 
                positive_count=positive_count,  
                negative_count=negative_count,  
                total_mentions=len(all_sentiments),  
                date=datetime.now(timezone.utc).date()
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