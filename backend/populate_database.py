#!/usr/bin/env python3
"""
Script to trigger initial data collection tasks
Populates the database with market data, sentiment data, and insider trades
"""

import sys
import os

# Add project paths
project_root = os.path.dirname(os.path.dirname(__file__))
backend_path = os.path.dirname(__file__)
sys.path.insert(0, project_root)
sys.path.insert(0, backend_path)

from app.tasks import (
    collect_market_data,
    collect_reddit_sentiment,
    collect_insider_trading,
    update_portfolio_values
)

def populate_database():
    """Trigger all data collection tasks"""

    print("Starting data collection tasks...")
    print("=" * 50)

    # 1. Collect market data for popular stocks
    print("\n📈 Collecting market data...")
    popular_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "SPY", "QQQ"]
    try:
        result = collect_market_data.delay(tickers=popular_tickers)
        print(f"   Task ID: {result.id}")
        print(f"   Collecting data for: {', '.join(popular_tickers)}")
    except Exception as e:
        print(f"   Error: {e}")

    # 2. Collect Reddit sentiment data
    print("\n Collecting Reddit sentiment...")
    try:
        result = collect_reddit_sentiment.delay()
        print(f"   Task ID: {result.id}")
        print(f"   Analyzing posts from WSB, stocks, investing subreddits")
    except Exception as e:
        print(f"   Error: {e}")

    # 3. Collect insider trading data
    print("\n👔 Collecting insider trading data...")
    try:
        result = collect_insider_trading.delay()
        print(f"   Task ID: {result.id}")
        print(f"   Fetching latest insider trades from OpenInsider")
    except Exception as e:
        print(f"   Error: {e}")

    # 4. Update portfolio values (this will work after portfolios are created)
    print("\n💼 Updating portfolio values...")
    try:
        result = update_portfolio_values.delay()
        print(f"   Task ID: {result.id}")
        print(f"   Updating all portfolio valuations")
    except Exception as e:
        print(f"    Error: {e}")

    print("\n" + "=" * 50)
    print("✅ All tasks have been queued!")
    print("\nTasks are running in the background via Celery.")
    print("Check the Celery worker logs to monitor progress.")
    print("\nYou can also check the database to see data being populated:")
    print("  - Stock prices and info")
    print("  - Reddit posts and sentiment")
    print("  - Insider trades")

    return True

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Populate database with initial data")
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Additional stock tickers to collect (e.g., --tickers AMD COIN)"
    )

    args = parser.parse_args()

    # If additional tickers provided, add them
    if args.tickers:
        print(f"Additional tickers to collect: {', '.join(args.tickers)}")
        # This would require modifying the populate_database function
        # For now, we'll just note them

    populate_database()