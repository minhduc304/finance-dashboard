"""
Sentiment analysis API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

from app.core.database import get_db
from app.models import StockSentiment, RedditPost

router = APIRouter()

# Response models
class SentimentData(BaseModel):
    date: datetime
    total_mentions: int
    total_posts: int
    total_comments: int
    avg_sentiment: float
    positive_count: int
    negative_count: int
    neutral_count: int

class StockSentimentResponse(BaseModel):
    ticker: str
    period_days: int
    data_points: int
    sentiment: List[SentimentData]

class TrendingSentimentStock(BaseModel):
    ticker: str
    total_mentions: int
    avg_sentiment: float
    positive_mentions: int
    negative_mentions: int
    sentiment_ratio: Optional[float]

class TrendingSentimentResponse(BaseModel):
    period: str
    count: int
    stocks: List[TrendingSentimentStock]

class RedditPostResponse(BaseModel):
    id: str
    title: str
    subreddit: str
    author: str
    score: int
    num_comments: int
    content_preview: Optional[str]
    mentioned_tickers: Optional[List[str]]
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    created_utc: Optional[datetime]

class StockPostsResponse(BaseModel):
    ticker: str
    count: int
    sentiment_filter: Optional[str]
    posts: List[RedditPostResponse]

class SentimentBreakdown(BaseModel):
    positive: int
    negative: int
    neutral: int

class SentimentSummaryResponse(BaseModel):
    date: str
    total_mentions: int
    total_posts: int
    sentiment_breakdown: SentimentBreakdown
    avg_sentiment: float
    market_mood: str


@router.get("/stock/{ticker}", response_model=StockSentimentResponse)
async def get_stock_sentiment(
    ticker: str,
    days: int = Query(default=7, description="Number of days of sentiment history"),
    db: Session = Depends(get_db)
):
    """Get sentiment data for a specific stock"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    sentiment_data = db.query(StockSentiment).filter(
        StockSentiment.ticker == ticker.upper(),
        StockSentiment.date >= cutoff_date
    ).order_by(StockSentiment.date.desc()).all()

    return StockSentimentResponse(
        ticker=ticker.upper(),
        period_days=days,
        data_points=len(sentiment_data),
        sentiment=sentiment_data
    )


@router.get("/trending", response_model=TrendingSentimentResponse)
async def get_trending_sentiment(
    limit: int = Query(default=10, description="Number of trending stocks to return"),
    period: str = Query(default="24h", description="Time period: 24h, 7d, 30d"),
    db: Session = Depends(get_db)
):
    """Get trending stocks by sentiment mentions"""
    try:
        from sqlalchemy import func, desc

        period_days = {"24h": 1, "7d": 7, "30d": 30}.get(period, 1)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)

        trending = db.query(
            StockSentiment.ticker,
            func.sum(StockSentiment.total_mentions).label('total_mentions'),
            func.avg(StockSentiment.avg_sentiment).label('avg_sentiment'),
            func.sum(StockSentiment.positive_count).label('positive_total'),
            func.sum(StockSentiment.negative_count).label('negative_total')
        ).filter(
            StockSentiment.date >= cutoff_date
        ).group_by(
            StockSentiment.ticker
        ).order_by(
            desc('total_mentions')
        ).limit(limit).all()

        stocks = [
            TrendingSentimentStock(
                ticker=stock.ticker,
                total_mentions=int(stock.total_mentions),
                avg_sentiment=float(stock.avg_sentiment) if stock.avg_sentiment else 0,
                positive_mentions=int(stock.positive_total),
                negative_mentions=int(stock.negative_total),
                sentiment_ratio=(
                    float(stock.positive_total) / float(stock.negative_total)
                    if stock.negative_total and stock.negative_total > 0
                    else None
                )
            )
            for stock in trending
        ]

        return TrendingSentimentResponse(
            period=period,
            count=len(stocks),
            stocks=stocks
        )

    except Exception:
        return TrendingSentimentResponse(
            period=period,
            count=0,
            stocks=[]
        )


@router.get("/posts/{ticker}", response_model=StockPostsResponse)
async def get_stock_posts(
    ticker: str,
    limit: int = Query(default=20, description="Number of posts to return"),
    sentiment_filter: Optional[str] = Query(default=None, description="Filter by sentiment: positive, negative, neutral"),
    db: Session = Depends(get_db)
):
    """Get recent Reddit posts mentioning a specific stock"""
    from sqlalchemy import or_

    query = db.query(RedditPost).filter(
        or_(
            RedditPost.mentioned_tickers.contains([ticker.upper()]),
            RedditPost.title.contains(ticker.upper()),
            RedditPost.content.contains(ticker.upper())
        )
    )

    if sentiment_filter:
        query = query.filter(RedditPost.sentiment_label == sentiment_filter)

    posts = query.order_by(RedditPost.created_utc.desc()).limit(limit).all()

    post_responses = [
        RedditPostResponse(
            id=post.reddit_id,
            title=post.title,
            subreddit=post.subreddit,
            author=post.author,
            score=post.score,
            num_comments=post.num_comments,
            content_preview=post.content[:200] + "..." if post.content and len(post.content) > 200 else post.content,
            mentioned_tickers=post.mentioned_tickers,
            sentiment_score=post.sentiment_score,
            sentiment_label=post.sentiment_label,
            created_utc=post.created_utc
        )
        for post in posts
    ]

    return StockPostsResponse(
        ticker=ticker.upper(),
        count=len(posts),
        sentiment_filter=sentiment_filter,
        posts=post_responses
    )


@router.get("/summary", response_model=SentimentSummaryResponse)
async def get_sentiment_summary(
    db: Session = Depends(get_db)
):
    """Get overall sentiment summary across all stocks"""
    try:
        from sqlalchemy import func

        today = datetime.now(timezone.utc).date()

        today_sentiment = db.query(
            func.sum(StockSentiment.total_mentions).label('total_mentions'),
            func.sum(StockSentiment.positive_count).label('positive'),
            func.sum(StockSentiment.negative_count).label('negative'),
            func.sum(StockSentiment.neutral_count).label('neutral'),
            func.avg(StockSentiment.avg_sentiment).label('avg_sentiment')
        ).filter(
            func.date(StockSentiment.date) == today
        ).first()

        posts_today = db.query(func.count(RedditPost.id)).filter(
            func.date(RedditPost.created_utc) == today
        ).scalar() or 0

        avg_sentiment = float(today_sentiment.avg_sentiment) if today_sentiment.avg_sentiment else 0

        return SentimentSummaryResponse(
            date=today.isoformat(),
            total_mentions=int(today_sentiment.total_mentions) if today_sentiment.total_mentions else 0,
            total_posts=posts_today,
            sentiment_breakdown=SentimentBreakdown(
                positive=int(today_sentiment.positive) if today_sentiment.positive else 0,
                negative=int(today_sentiment.negative) if today_sentiment.negative else 0,
                neutral=int(today_sentiment.neutral) if today_sentiment.neutral else 0
            ),
            avg_sentiment=avg_sentiment,
            market_mood=(
                "bullish" if avg_sentiment > 0.1
                else "bearish" if avg_sentiment < -0.1
                else "neutral"
            )
        )

    except Exception:
        return SentimentSummaryResponse(
            date=datetime.now(timezone.utc).date().isoformat(),
            total_mentions=0,
            total_posts=0,
            sentiment_breakdown=SentimentBreakdown(positive=0, negative=0, neutral=0),
            avg_sentiment=0,
            market_mood="neutral"
        )