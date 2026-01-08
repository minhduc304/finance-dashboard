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
        import os

        collector = WealthsimpleCollector()
        db = SessionLocal()

        # Authenticate using saved session token (from ws_session.json)
        # If no valid session exists, this will fail and skip the sync
        # To authenticate initially, run: python scripts/wealthsimple_login.py
        try:
            if not collector.authenticate():
                logger.warning("Wealthsimple authentication failed - no valid session token")
                db.close()
                return {"status": "skipped", "error": "No valid session. Run interactive login first."}
        except Exception as auth_error:
            logger.warning(f"Wealthsimple authentication error: {auth_error}")
            db.close()
            return {"status": "skipped", "error": "Authentication failed. Run interactive login first."}

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

            # Don't overwrite total_value and cash_balance here
            # They will be calculated by update_portfolio_values task
            portfolio.updated_at = datetime.now(timezone.utc)

            db.commit()

            # Update existing holdings or create new ones (don't delete)
            # This preserves current_price calculated from market data
            for holding_data in portfolio_data['holdings']:
                if holding_data['account_id'] == account_data['id']:
                    # Find existing holding
                    holding = db.query(Holding).filter_by(
                        portfolio_id=portfolio.id,
                        ticker=holding_data['symbol']
                    ).first()

                    if holding:
                        # Update existing holding - preserve current_price if WS doesn't have it
                        holding.name = holding_data.get('name') or holding.name
                        holding.quantity = holding_data['quantity']
                        holding.average_cost = holding_data['average_cost']
                        # Only update price if WS has a valid one
                        if holding_data['current_price'] > 0:
                            holding.current_price = holding_data['current_price']
                            holding.market_value = holding_data['market_value']
                    else:
                        # Create new holding
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
        try:
            db.close()
        except:
            pass
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
            # List of cash/money market symbols to exclude
            cash_symbols = ['SEC-C-CAD', 'CASH', 'CAD', 'USD']
            for holding in holdings:
                if holding.ticker:
                    ticker_upper = holding.ticker.upper()
                    # Skip cash accounts and money market funds
                    if ticker_upper not in cash_symbols and not ticker_upper.startswith('SEC-'):
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
                            # Remove fields that don't exist in StockPrice model
                            price_data.pop('dividends', None)
                            price_data.pop('stock splits', None)  # Note: space in column name
                            price_data.pop('stock_splits', None)  # Just in case
                            price_data.pop('capital gains', None)  # ETF distributions
                            price_data.pop('capital_gains', None)  # Alternative format
                            price = StockPrice(**price_data)
                            db.add(price)

                db.commit()
                results.append(ticker)

                # Invalidate cache for this ticker
                try:
                    from backend.app.core.cache import invalidate_ticker_cache
                    invalidate_ticker_cache(ticker)
                except Exception as cache_error:
                    logger.warning(f"Cache invalidation failed for {ticker}: {cache_error}")

            except Exception as e:
                logger.error(f"Failed to update {ticker}: {e}")
                db.rollback()

        db.close()
        return {"status": "success", "tickers_updated": results}

    except Exception as e:
        logger.error(f"Market data collection failed: {e}")
        try:
            db.close()
        except:
            pass
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
                        # Check if comment already exists
                        existing_comment = db.query(RedditComment).filter_by(
                            reddit_id=comment_data.get('reddit_id')
                        ).first()

                        if existing_comment:
                            continue  # Skip if comment already exists

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
        try:
            db.close()
        except:
            pass
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
                transaction_date=trade_data.get('trade_date')  # Use actual trade_date (when trade occurred)
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
                    transaction_date=trade_data.get('trade_date'),  # Use actual trade_date (when trade occurred)
                    trade_date=trade_data.get('trade_date')  # Use trade_date (when trade occurred, not filed)
                )
                db.add(trade)
                saved_count += 1

        db.commit()
        db.close()

        return {"status": "success", "trades_saved": saved_count}

    except Exception as e:
        logger.error(f"Insider trading collection failed: {e}")
        try:
            db.close()
        except:
            pass
        raise self.retry(exc=e, countdown=600)




@shared_task(bind=True, max_retries=3)
def collect_stock_news(self):
    """Collect news articles for portfolio holdings"""
    try:
        from collectors.yfinance_collector import YFinanceCollector
        from backend.app.core.database import SessionLocal
        from backend.app.models import StockNews, Holding

        collector = YFinanceCollector()
        db = SessionLocal()

        # Get unique tickers from holdings
        holdings = db.query(Holding).all()
        tickers = set()
        cash_symbols = ['SEC-C-CAD', 'CASH', 'CAD', 'USD']

        for holding in holdings:
            if holding.ticker:
                ticker_upper = holding.ticker.upper()
                if ticker_upper not in cash_symbols and not ticker_upper.startswith('SEC-'):
                    tickers.add(holding.ticker)

        if not tickers:
            logger.info("No tickers found for news collection")
            db.close()
            return {"status": "no_tickers"}

        news_collected = 0

        for ticker in tickers:
            try:
                # Collect news for this ticker
                news_items = collector.collect_news(ticker, max_items=5)

                for news_item in news_items:
                    # Check if news already exists (by link)
                    existing = db.query(StockNews).filter_by(
                        link=news_item.get('link')
                    ).first()

                    if not existing:
                        news = StockNews(
                            title=news_item.get('title'),
                            link=news_item.get('link'),
                            publisher=news_item.get('publisher'),
                            primary_ticker=ticker.upper(),
                            publish_time=news_item.get('publish_time'),
                            provider_publish_time=news_item.get('publish_time')
                        )
                        db.add(news)
                        news_collected += 1

                db.commit()

            except Exception as e:
                logger.error(f"Failed to collect news for {ticker}: {e}")
                db.rollback()
                continue

        db.close()

        return {
            "status": "success",
            "tickers_processed": len(tickers),
            "news_collected": news_collected
        }

    except Exception as e:
        logger.error(f"Stock news collection failed: {e}")
        try:
            db.close()
        except:
            pass
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
            cash_balance = 0
            total_holdings_value = 0

            # Cash symbols to identify cash holdings
            cash_symbols = ['SEC-C-CAD', 'SEC-C-USD', 'CASH', 'CAD', 'USD']

            for holding in portfolio.holdings:
                ticker_upper = holding.ticker.upper() if holding.ticker else ''

                # Check if this is a cash holding
                is_cash = (ticker_upper in cash_symbols or
                          ticker_upper.startswith('SEC-') and 'CAD' in ticker_upper or
                          ticker_upper.startswith('SEC-') and 'USD' in ticker_upper)

                if is_cash:
                    # For cash holdings, market value is just quantity * 1
                    holding.current_price = 1.0
                    holding.market_value = float(holding.quantity)
                    cash_balance += holding.market_value
                else:
                    # Get latest price for non-cash holdings
                    latest_price = db.query(StockPrice).filter(
                        StockPrice.ticker == holding.ticker
                    ).order_by(StockPrice.date.desc()).first()

                    if latest_price:
                        holding.current_price = float(latest_price.close)
                        holding.market_value = float(holding.quantity) * float(latest_price.close)
                        holding.unrealized_gain = holding.market_value - (float(holding.quantity) * float(holding.average_cost))
                        total_holdings_value += holding.market_value

            portfolio.cash_balance = cash_balance
            portfolio.total_value = cash_balance + total_holdings_value
            portfolio.total_gain_loss = portfolio.total_value - portfolio.total_cost
            portfolio.updated_at = datetime.now(timezone.utc)
            updated_count += 1

        db.commit()
        db.close()

        return {"status": "success", "portfolios_updated": updated_count}

    except Exception as e:
        logger.error(f"Portfolio update failed: {e}")
        try:
            db.close()
        except:
            pass
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
        # List of cash/money market symbols to exclude
        cash_symbols = ['SEC-C-CAD', 'CASH', 'CAD', 'USD']
        for holding in holdings:
            if holding.ticker:
                ticker_upper = holding.ticker.upper()
                # Skip cash accounts and money market funds
                if ticker_upper not in cash_symbols and not ticker_upper.startswith('SEC-'):
                    tickers.add(ticker_upper)

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
        try:
            db.close()
        except:
            pass
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
            StockNews.publish_time < news_cutoff
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
        try:
            db.close()
        except:
            pass
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
        try:
            db.close()
        except:
            pass
        raise self.retry(exc=e, countdown=120)


@shared_task(bind=True, max_retries=3)
def collect_alphavantage_data(self):
    """Collect technical indicators and fundamentals from Alpha Vantage for portfolio holdings"""
    try:
        from collectors.alphavantage_collector import AlphaVantageCollector
        from backend.app.core.database import SessionLocal
        from backend.app.core.config import settings
        from backend.app.models import TechnicalIndicator, CompanyFundamentals, Holding

        collector = AlphaVantageCollector(api_key=settings.ALPHA_VANTAGE_API_KEY)
        db = SessionLocal()

        # Get unique tickers from holdings (limit to avoid hitting API limit)
        # Free tier: 25 requests/day
        holdings = db.query(Holding).distinct(Holding.ticker).limit(5).all()
        tickers = []
        cash_symbols = ['SEC-C-CAD', 'CASH', 'CAD', 'USD']

        for holding in holdings:
            if holding.ticker:
                ticker_upper = holding.ticker.upper()
                if ticker_upper not in cash_symbols and not ticker_upper.startswith('SEC-'):
                    tickers.append(ticker_upper)

        if not tickers:
            logger.info("No valid tickers found for Alpha Vantage collection")
            db.close()
            return {"status": "no_tickers"}

        collected_fundamentals = 0
        collected_indicators = 0

        for ticker in tickers[:5]:  # Limit to 5 tickers to stay within free tier
            try:
                logger.info(f"Collecting Alpha Vantage data for {ticker}")

                # Get company fundamentals
                overview = collector.get_company_overview(ticker)

                if overview and overview.get('ticker'):
                    fundamental = db.query(CompanyFundamentals).filter_by(ticker=ticker).first()
                    if not fundamental:
                        fundamental = CompanyFundamentals(ticker=ticker)
                        db.add(fundamental)

                    # Update fundamental data
                    fundamental.name = overview.get('name')
                    fundamental.description = overview.get('description')
                    fundamental.peg_ratio = overview.get('peg_ratio')
                    fundamental.book_value = overview.get('book_value')
                    fundamental.profit_margin = overview.get('profit_margin')
                    fundamental.operating_margin = overview.get('operating_margin')
                    fundamental.return_on_equity = overview.get('return_on_equity')
                    fundamental.return_on_assets = overview.get('return_on_assets')
                    fundamental.revenue_ttm = overview.get('revenue_ttm')
                    fundamental.gross_profit_ttm = overview.get('gross_profit_ttm')
                    fundamental.ebitda = overview.get('ebitda')
                    fundamental.analyst_target_price = overview.get('analyst_target_price')
                    fundamental.moving_avg_50_day = overview.get('50_day_ma')
                    fundamental.moving_avg_200_day = overview.get('200_day_ma')
                    fundamental.week_52_high = overview.get('52_week_high')
                    fundamental.week_52_low = overview.get('52_week_low')
                    fundamental.revenue_per_share = overview.get('revenue_per_share')

                    db.commit()
                    collected_fundamentals += 1
                    logger.info(f"Saved fundamentals for {ticker}")

                # Get RSI indicator (popular technical indicator)
                rsi_data = collector.get_rsi(ticker)

                if not rsi_data.empty:
                    # Save latest 30 days of RSI data
                    for date, row in rsi_data.tail(30).iterrows():
                        indicator = db.query(TechnicalIndicator).filter_by(
                            ticker=ticker,
                            indicator_type='RSI',
                            date=date
                        ).first()

                        if not indicator:
                            indicator = TechnicalIndicator(
                                ticker=ticker,
                                indicator_type='RSI',
                                date=date,
                                value=float(row['RSI']) if 'RSI' in row else float(row.iloc[0])
                            )
                            db.add(indicator)

                    db.commit()
                    collected_indicators += 1
                    logger.info(f"Saved RSI indicators for {ticker}")

            except Exception as e:
                logger.error(f"Error collecting Alpha Vantage data for {ticker}: {e}")
                db.rollback()
                continue

        db.close()

        return {
            "status": "success",
            "tickers_processed": len(tickers),
            "fundamentals_collected": collected_fundamentals,
            "indicators_collected": collected_indicators
        }

    except Exception as exc:
        logger.error(f"Alpha Vantage collection failed: {exc}")
        try:
            db.close()
        except:
            pass
        raise self.retry(exc=exc, countdown=600)