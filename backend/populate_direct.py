#!/usr/bin/env python3
"""
Fixed direct data population script with proper error handling and rate limiting
"""

import sys
import os
import time
from datetime import datetime, timezone

# Add project paths
project_root = os.path.dirname(os.path.dirname(__file__))
backend_path = os.path.dirname(__file__)
sys.path.insert(0, project_root)
sys.path.insert(0, backend_path)

def populate_database_direct():
    """Call task functions directly with fixes for all errors"""

    print("Populating database with data...")
    print("=" * 50)

    # 1. Sync Wealthsimple portfolios first to populate holdings for watchlist
    print(f"\nSyncing Wealthsimple portfolios...")
    try:
        from collectors.wealthsimple_collector import WealthsimpleCollector
        from backend.app.core.database import SessionLocal
        from backend.app.models import Portfolio, Holding, Transaction

        collector = WealthsimpleCollector()
        db = SessionLocal()

        # Try to authenticate with Wealthsimple
        print("   Authenticating with Wealthsimple...")
        print("   (Will use saved session if available, otherwise prompt for credentials)")

        try:
            if not collector.authenticate():
                print("   ✗ Authentication failed")
                print("   Note: Skipping Wealthsimple sync")
            else:
                print("   ✓ Authenticated successfully")

                # Collect all data from Wealthsimple
                print("   Collecting portfolio data...")
                portfolio_data = collector.collect_all_data()

                portfolios_updated = 0
                holdings_saved = 0
                transactions_saved = 0

                # Save portfolio summary
                for account_data in portfolio_data['portfolio_summary']['accounts']:
                    portfolio = db.query(Portfolio).filter_by(
                        name=account_data['description']
                    ).first()

                    if not portfolio:
                        portfolio = Portfolio(
                            name=account_data['description'],
                            created_at=datetime.now(timezone.utc))
                        db.add(portfolio)
                        db.commit()
                        db.refresh(portfolio)
                        print(f"      ✓ Created portfolio: {account_data['description']}")
                    else:
                        print(f"      • Updating portfolio: {account_data['description']}")

                    portfolio.total_value = account_data['value']
                    portfolio.cash_balance = account_data['cash_balance']
                    portfolio.updated_at = datetime.now(timezone.utc)
                    portfolios_updated += 1

                    # Clear existing holdings for fresh update
                    db.query(Holding).filter_by(portfolio_id=portfolio.id).delete()

                    # Save holdings for this account
                    for holding_data in portfolio_data['holdings']:
                        if holding_data['account_id'] == account_data['id']:
                            holding = Holding(
                                portfolio_id=portfolio.id,
                                ticker=holding_data['symbol'],
                                name=holding_data['name'],
                                quantity=holding_data['quantity'],
                                average_cost=holding_data['average_cost'],
                                current_price=holding_data['current_price'],
                                market_value=holding_data['market_value'],
                                unrealized_gain=holding_data.get('gain_loss', 0)
                            )
                            db.add(holding)
                            holdings_saved += 1

                    # Save transactions for this account
                    for trans_data in portfolio_data['transactions']:
                        if trans_data['account_id'] == account_data['id']:
                            # Check if transaction already exists
                            existing = db.query(Transaction).filter_by(
                                portfolio_id=portfolio.id,
                                transaction_date=trans_data['transaction_date']
                            ).first()

                            if not existing:
                                transaction = Transaction(
                                    portfolio_id=portfolio.id,
                                    type=trans_data['type'],
                                    symbol=trans_data.get('symbol'),
                                    quantity=trans_data.get('quantity'),
                                    price=trans_data.get('price'),
                                    total_amount=trans_data['total_amount'],
                                    transaction_date=trans_data['transaction_date']
                                )
                                db.add(transaction)
                                transactions_saved += 1

                db.commit()
                print(f"   Result: {portfolios_updated} portfolios updated")
                print(f"           {holdings_saved} holdings saved")
                print(f"           {transactions_saved} new transactions saved")

        except Exception as e:
            print(f"   Error during Wealthsimple sync: {e}")
            db.rollback()

        db.close()

    except Exception as e:
        print(f"   Error: {e}")

    # 2. Update watchlist based on portfolio holdings
    print(f"\nUpdating watchlist from portfolio holdings...")
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
            print("   No holdings found, skipping watchlist update")
        else:
            print(f"   Found {len(tickers)} unique tickers in holdings: {', '.join(sorted(tickers))}")

            # Find or create default watchlist
            watchlist = db.query(Watchlist).filter_by(is_default=True).first()
            if not watchlist:
                watchlist = Watchlist(
                    name="Portfolio Holdings",
                    description="Auto-generated from current portfolio holdings",
                    tickers=list(tickers),
                    is_default=True,
                    is_public=False,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(watchlist)
                print("   ✓ Created new default watchlist")
            else:
                # Update existing watchlist
                watchlist.tickers = list(tickers)
                watchlist.updated_at = datetime.now(timezone.utc)
                print("   ✓ Updated existing default watchlist")

            db.commit()
            print(f"   Result: Watchlist updated with {len(tickers)} tickers")

        db.close()

    except Exception as e:
        print(f"   Error: {e}")

    # 3. Collect market data using portfolio holdings as watchlist
    print(f"\nCollecting market data for portfolio holdings...")
    try:
        from app.tasks import collect_market_data
        from collectors.yfinance_collector import YFinanceCollector
        from backend.app.core.database import SessionLocal
        from backend.app.models import StockInfo, StockPrice, Holding

        collector = YFinanceCollector()
        db = SessionLocal()
        results = []

        # Get tickers from portfolio holdings first
        holdings = db.query(Holding).all()
        tickers = set()
        for holding in holdings:
            if holding.ticker:
                tickers.add(holding.ticker)

        # If no holdings, use default popular tickers
        if not tickers:
            tickers = ["AAPL", "MSFT", "GOOGL"]
            print(f"   No portfolio holdings found, using default tickers: {', '.join(tickers)}")
        else:
            print(f"   Using portfolio holdings: {', '.join(tickers)}")

        for ticker in tickers:
            try:
                print(f"   Collecting {ticker}...")
                # Add delay to avoid rate limiting
                time.sleep(2)  # Wait 2 seconds between requests

                # Collect data with error handling
                info = collector.collect_stock_info(ticker)
                if info:
                    # Save stock info
                    existing = db.query(StockInfo).filter_by(ticker=ticker.upper()).first()
                    if existing:
                        for key, value in info.items():
                            if value is not None and hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        stock = StockInfo(**info)
                        db.add(stock)
                    db.commit()
                    results.append(ticker)
                    print(f"      ✓ {ticker} collected successfully")
                else:
                    print(f"      ⚠ No data returned for {ticker}")

            except Exception as e:
                print(f"      ✗ Error collecting {ticker}: {e}")
                db.rollback()

        db.close()
        print(f"   Result: {len(results)} tickers updated successfully")

    except Exception as e:
        print(f"   Error: {e}")

    # 4. Collect Reddit sentiment - Fixed
    print(f"\nCollecting Reddit sentiment...")
    try:
        from collectors.reddit_collector import RedditCollector
        from backend.app.core.database import SessionLocal
        from backend.app.models import RedditPost, RedditComment, StockSentiment

        collector = RedditCollector()
        db = SessionLocal()

        # First, collect some posts
        subreddit = "stocks"
        print(f"   Attempting to collect posts from r/{subreddit}...")
        posts = collector.collect_posts(subreddit, limit=5)
        print(f"   Collected {len(posts)} posts from Reddit API")
        saved_posts = 0

        for post_data in posts:
            try:
                print(f"      Processing post: {post_data.get('title', 'No title')[:50]}...")
                # Check if post exists
                existing_post = db.query(RedditPost).filter_by(
                    reddit_id=post_data['reddit_id']
                ).first()

                if not existing_post:
                    post = RedditPost(**post_data)
                    db.add(post)
                    db.commit()
                    db.refresh(post)
                    saved_posts += 1
                    print(f"         ✓ Saved new post")

                    # Collect comments for this post
                    comments = collector.collect_comments(post_data['reddit_id'], limit=3)
                    for comment_data in comments:
                        # Remove the incorrect field
                        if 'post_reddit_id' in comment_data:
                            del comment_data['post_reddit_id']

                        # Create comment with correct foreign key
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
                            scraped_at=comment_data.get('scraped_at', datetime.now(timezone.utc))
                        )
                        db.add(comment)
                else:
                    print(f"         - Post already exists in database")

            except Exception as e:
                print(f"      Error saving post: {e}")
                db.rollback()
                continue

        db.commit()
        db.close()
        print(f"   Result: {saved_posts} posts saved successfully")

    except Exception as e:
        print(f"   Error: {e}")

    # 5. Collect insider trading - Fixed
    print(f"\nCollecting insider trading data...")
    try:
        from collectors.openinsider_collector import OpenInsiderCollector
        from backend.app.core.database import SessionLocal
        from backend.app.models import InsiderTrade

        collector = OpenInsiderCollector()
        db = SessionLocal()

        # Collect latest trades
        print("   Attempting to scrape OpenInsider website...")
        trades = collector.scrape_latest_trades(pages=1)  # Reduced to 1 page
        print(f"   Collected {len(trades)} trades from OpenInsider")

        saved_count = 0
        for trade_data in trades:
            try:
                print(f"      Processing trade: {trade_data.get('ticker', 'N/A')} - {trade_data.get('insider_name', 'Unknown')[:30]}")
                # Map the correct field names
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

                # Check if trade already exists
                existing = db.query(InsiderTrade).filter_by(
                    ticker=trade.ticker,
                    owner_name=trade.owner_name,
                    transaction_date=trade.transaction_date
                ).first()

                if not existing:
                    db.add(trade)
                    saved_count += 1
                    print(f"         ✓ Saved new trade")
                else:
                    print(f"         - Trade already exists in database")

            except Exception as e:
                print(f"      Error saving trade: {e}")
                db.rollback()
                continue

        db.commit()
        db.close()
        print(f"   Result: {saved_count} trades saved successfully")

    except Exception as e:
        print(f"   Error: {e}")

    print("\n" + "=" * 50)
    print("Data population complete!")
    print("\nYou can now check your database for:")
    print("  - Stock info and prices")
    print("  - Reddit posts and sentiment")
    print("  - Insider trading data")
    print("  - Wealthsimple portfolios and holdings")
    print("\nNote: Some data collection may be limited due to:")
    print("  - Rate limiting (Yahoo Finance)")
    print("  - Authentication requirements (Wealthsimple)")
    print("  - API availability (Reddit)")

if __name__ == "__main__":
    populate_database_direct()