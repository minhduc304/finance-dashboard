# models/social_sentiment.py

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

# Import shared Base from backend
import sys
import os
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
sys.path.insert(0, backend_path)
from app.core.database import Base

class RedditPost(Base):
    __tablename__ = "reddit_posts"
    
    id = Column(Integer, primary_key=True)
    reddit_id = Column(String(20), unique=True)  # Reddit's post ID
    
    # Basic post info
    subreddit = Column(String(50))
    title = Column(String(500))
    content = Column(Text)
    author = Column(String(50))
    
    # Reddit metrics
    score = Column(Integer, default=0)  # Upvotes - downvotes
    num_comments = Column(Integer, default=0)
    
    # Stock mentions - just store as JSON array
    mentioned_tickers = Column(JSON)  # ["AAPL", "MSFT", "GOOGL"]
    
    # Sentiment scores
    sentiment_score = Column(Float)  # -1.0 to 1.0
    sentiment_label = Column(String(10))  # "positive", "negative", "neutral"
    
    # Timestamps
    created_utc = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.now(timezone.utc))


class RedditComment(Base):
    __tablename__ = "reddit_comments"
    
    id = Column(Integer, primary_key=True)
    reddit_id = Column(String(20), unique=True)
    post_id = Column(Integer, ForeignKey("reddit_posts.id"))
    
    # Comment data
    author = Column(String(50))
    content = Column(Text)
    score = Column(Integer, default=0)
    
    # Stock mentions and sentiment
    mentioned_tickers = Column(JSON)  # ["AAPL", "MSFT"]
    sentiment_score = Column(Float)
    sentiment_label = Column(String(10))
    
    # Timestamps
    created_utc = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    # Relationship to post
    post = relationship("RedditPost")


class StockSentiment(Base):
    """Daily sentiment summary per stock"""
    __tablename__ = "stock_sentiment"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10))  # AAPL, MSFT, etc.
    date = Column(DateTime)

    # Counts
    total_mentions = Column(Integer, default=0)
    total_posts = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)

    # Sentiment averages
    avg_sentiment = Column(Float)  # Average of all sentiment scores
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class SentimentValidationSample(Base):
    """Manually labeled samples for accuracy validation"""
    __tablename__ = "sentiment_validation_samples"

    id = Column(Integer, primary_key=True)

    # Text content
    text = Column(Text, nullable=False)
    source_type = Column(String(20))  # "reddit_post", "reddit_comment", "synthetic"
    source_id = Column(String(50))  # Reddit ID if applicable
    subreddit = Column(String(50))  # Subreddit context if applicable

    # Ground truth label (manually verified)
    true_label = Column(String(10), nullable=False)  # "positive", "negative", "neutral"
    true_score = Column(Float)  # Optional: manual score estimate (-1.0 to 1.0)

    # Model prediction (calculated on-demand)
    predicted_label = Column(String(10))
    predicted_score = Column(Float)
    prediction_confidence = Column(Float)

    # Metadata
    labeled_by = Column(String(50), default="manual")  # Who labeled this
    notes = Column(Text)  # Any notes about this sample
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    validated_at = Column(DateTime)  # When prediction was last validated