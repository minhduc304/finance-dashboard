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