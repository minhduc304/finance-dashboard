#!/usr/bin/env python3
"""
Create sentiment_validation_samples table and seed with initial samples
"""

import sys
import os

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
backend_path = os.path.join(project_root, 'backend')
sys.path.insert(0, project_root)
sys.path.insert(0, backend_path)

from app.core.database import engine, SessionLocal, Base
from app.models import SentimentValidationSample

def create_table():
    """Create the validation table"""
    print("Creating sentiment_validation_samples table...")
    Base.metadata.create_all(bind=engine, tables=[SentimentValidationSample.__table__])
    print("✓ Table created successfully")

def seed_validation_samples():
    """Seed database with manually labeled validation samples"""
    print("\nSeeding validation samples...")

    db = SessionLocal()

    # Sample data with clear sentiment labels
    # These are realistic Reddit-style financial posts
    samples = [
        # Positive samples
        {
            "text": "AAPL crushed earnings! Revenue up 20%, raising guidance. Stock going to the moon 🚀🚀",
            "true_label": "positive",
            "source_type": "synthetic",
            "subreddit": "wallstreetbets",
            "notes": "Clear bullish sentiment with rocket emojis"
        },
        {
            "text": "Just bought more TSLA. Fundamentals are strong, delivery numbers exceeded expectations. Bullish long term.",
            "true_label": "positive",
            "source_type": "synthetic",
            "subreddit": "stocks",
            "notes": "Positive fundamental analysis"
        },
        {
            "text": "MSFT breaking out! Great earnings, cloud revenue massive. Calls printing 💎🙌",
            "true_label": "positive",
            "source_type": "synthetic",
            "subreddit": "wallstreetbets",
            "notes": "Bullish with diamond hands emoji"
        },
        {
            "text": "Loaded up on NVDA today. AI is the future and they're dominating. Great long-term hold.",
            "true_label": "positive",
            "source_type": "synthetic",
            "subreddit": "investing",
            "notes": "Bullish on fundamentals"
        },
        {
            "text": "AMD looking strong. New chips outperforming Intel. Undervalued at current price.",
            "true_label": "positive",
            "source_type": "synthetic",
            "subreddit": "stocks",
            "notes": "Positive competitive analysis"
        },

        # Negative samples
        {
            "text": "NFLX is tanking hard. Subscriber growth is dead. This is going to drill 📉",
            "true_label": "negative",
            "source_type": "synthetic",
            "subreddit": "wallstreetbets",
            "notes": "Clear bearish sentiment"
        },
        {
            "text": "Getting crushed on my GME position. Down 40% and no recovery in sight. FML.",
            "true_label": "negative",
            "source_type": "synthetic",
            "subreddit": "wallstreetbets",
            "notes": "Negative personal loss"
        },
        {
            "text": "SNAP earnings were terrible. User growth slowing, competition crushing them. Puts paying off.",
            "true_label": "negative",
            "source_type": "synthetic",
            "subreddit": "stocks",
            "notes": "Bearish fundamental analysis"
        },
        {
            "text": "META continues to bleed. Metaverse was a huge waste of money. Bearish.",
            "true_label": "negative",
            "source_type": "synthetic",
            "subreddit": "investing",
            "notes": "Negative on strategic direction"
        },
        {
            "text": "UBER is overvalued. Still not profitable, competition increasing. This will crash.",
            "true_label": "negative",
            "source_type": "synthetic",
            "subreddit": "stocks",
            "notes": "Bearish valuation analysis"
        },

        # Neutral samples
        {
            "text": "Anyone have thoughts on SPY? Just looking to understand the overall market direction.",
            "true_label": "neutral",
            "source_type": "synthetic",
            "subreddit": "investing",
            "notes": "Question, no clear sentiment"
        },
        {
            "text": "Holding AMZN shares. Waiting to see how Q4 earnings play out before making any moves.",
            "true_label": "neutral",
            "source_type": "synthetic",
            "subreddit": "stocks",
            "notes": "Neutral wait-and-see stance"
        },
        {
            "text": "DIS trading sideways. Park attendance is okay, streaming is growing slowly. No major catalysts.",
            "true_label": "neutral",
            "source_type": "synthetic",
            "subreddit": "investing",
            "notes": "Neutral fundamental assessment"
        },
        {
            "text": "What's your opinion on INTC? Looking for DD before deciding on a position.",
            "true_label": "neutral",
            "source_type": "synthetic",
            "subreddit": "stocks",
            "notes": "Information seeking, no opinion"
        },
        {
            "text": "GOOGL reporting earnings next week. Could go either way depending on ad revenue numbers.",
            "true_label": "neutral",
            "source_type": "synthetic",
            "subreddit": "investing",
            "notes": "Neutral expectation"
        },

        # More positive samples
        {
            "text": "This is the bottom for TSLA. Great entry point, loading up on shares. 🚀",
            "true_label": "positive",
            "source_type": "synthetic",
            "subreddit": "wallstreetbets",
            "notes": "Bullish bottom call"
        },
        {
            "text": "JPM earnings beat expectations. Banking sector looking strong. Bullish on financials.",
            "true_label": "positive",
            "source_type": "synthetic",
            "subreddit": "investing",
            "notes": "Sector-wide bullish sentiment"
        },
        {
            "text": "Finally in the green on my PLTR position. Long term hold paying off. Diamond hands!",
            "true_label": "positive",
            "source_type": "synthetic",
            "subreddit": "wallstreetbets",
            "notes": "Positive personal performance"
        },

        # More negative samples
        {
            "text": "ROKU getting destroyed. Competition from every direction. Avoid this stock.",
            "true_label": "negative",
            "source_type": "synthetic",
            "subreddit": "stocks",
            "notes": "Strong bearish warning"
        },
        {
            "text": "Sold all my COIN. Crypto winter is here and this stock will follow BTC down.",
            "true_label": "negative",
            "source_type": "synthetic",
            "subreddit": "investing",
            "notes": "Bearish macro view"
        },

        # More neutral samples
        {
            "text": "Rate my portfolio: 60% VTI, 30% bonds, 10% cash. Just rebalancing for retirement.",
            "true_label": "neutral",
            "source_type": "synthetic",
            "subreddit": "Bogleheads",
            "notes": "Portfolio discussion, no directional sentiment"
        },
        {
            "text": "When does WMT report earnings? Need to know the date.",
            "true_label": "neutral",
            "source_type": "synthetic",
            "subreddit": "stocks",
            "notes": "Factual question"
        }
    ]

    # Add all samples
    added_count = 0
    for sample_data in samples:
        sample = SentimentValidationSample(**sample_data)
        db.add(sample)
        added_count += 1

    db.commit()
    print(f"✓ Added {added_count} validation samples")

    # Show distribution
    positive = len([s for s in samples if s['true_label'] == 'positive'])
    negative = len([s for s in samples if s['true_label'] == 'negative'])
    neutral = len([s for s in samples if s['true_label'] == 'neutral'])

    print(f"\nLabel distribution:")
    print(f"  Positive: {positive}")
    print(f"  Negative: {negative}")
    print(f"  Neutral: {neutral}")
    print(f"  Total: {added_count}")

    db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Sentiment Validation Table Setup")
    print("=" * 60)

    create_table()
    seed_validation_samples()

    print("\n" + "=" * 60)
    print("Setup complete! ✓")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart FastAPI server to register new endpoints")
    print("2. Run validation: POST /api/v1/sentiment/validation/run")
    print("3. Check accuracy: GET /api/v1/sentiment/validation/accuracy")
    print("=" * 60)
