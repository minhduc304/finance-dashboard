#!/usr/bin/env python3
"""
Direct data population script - calls task functions directly instead of queueing
"""

import sys
import os

# Add project paths
project_root = os.path.dirname(os.path.dirname(__file__))
backend_path = os.path.dirname(__file__)
sys.path.insert(0, project_root)
sys.path.insert(0, backend_path)

def populate_database_direct():
    """Call task functions directly"""

    print("Populating database with data...")
    print("=" * 50)

    # Popular tickers to collect
    popular_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA"]

    # 1. Collect market data
    print(f"\n📈 Collecting market data for: {', '.join(popular_tickers)}")
    try:
        from app.tasks import collect_market_data
        result = collect_market_data(tickers=popular_tickers)
        print(f"   ✅ Result: {result}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 2. Collect Reddit sentiment
    print(f"\n💬 Collecting Reddit sentiment...")
    try:
        from app.tasks import collect_reddit_sentiment
        result = collect_reddit_sentiment()
        print(f"   ✅ Result: {result}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 3. Collect insider trading
    print(f"\n👔 Collecting insider trading data...")
    try:
        from app.tasks import collect_insider_trading
        result = collect_insider_trading()
        print(f"   ✅ Result: {result}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 50)
    print("✅ Data population complete!")
    print("\nYou can now check your database for:")
    print("  - Stock info and prices")
    print("  - Reddit posts and sentiment")
    print("  - Insider trading data")

if __name__ == "__main__":
    populate_database_direct()