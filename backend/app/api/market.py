"""
Market data API endpoints - Enhanced version
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models import User, StockInfo, StockPrice, StockNews, StockSentiment
from app.services.data_service import DataService

router = APIRouter()

# Response models
class StockInfoResponse(BaseModel):
    ticker: str
    name: Optional[str]
    long_name: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    exchange: Optional[str]
    market_cap: Optional[float]
    beta: Optional[float]
    trailing_pe: Optional[float]
    dividend_yield: Optional[float]
    updated_at: Optional[datetime]

class PricePoint(BaseModel):
    date: datetime
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: Optional[int]
    daily_return: Optional[float]

class StockPriceResponse(BaseModel):
    ticker: str
    period_days: int
    data_points: int
    prices: List[PricePoint]

class NewsArticle(BaseModel):
    title: str
    link: Optional[str]
    publisher: Optional[str]
    publish_time: Optional[datetime]
    related_tickers: Optional[List[str]]
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]

class StockNewsResponse(BaseModel):
    ticker: str
    count: int
    articles: List[NewsArticle]

class TrendingStock(BaseModel):
    ticker: str
    mentions: int
    avg_sentiment: float

class TrendingResponse(BaseModel):
    period: str
    count: int
    stocks: List[TrendingStock]


@router.get("/stocks/{ticker}", response_model=StockInfoResponse)
async def get_stock_info(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get basic stock information"""
    stock = db.query(StockInfo).filter(StockInfo.ticker == ticker.upper()).first()

    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {ticker} not found"
        )

    return stock


@router.get("/stocks/{ticker}/price", response_model=StockPriceResponse)
async def get_stock_price(
    ticker: str,
    days: int = Query(default=30, description="Number of days of price history"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get stock price history"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    prices = db.query(StockPrice).filter(
        StockPrice.ticker == ticker.upper(),
        StockPrice.date >= cutoff_date
    ).order_by(StockPrice.date.desc()).all()

    if not prices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data found for {ticker}"
        )

    return StockPriceResponse(
        ticker=ticker.upper(),
        period_days=days,
        data_points=len(prices),
        prices=prices
    )


@router.get("/stocks/{ticker}/news", response_model=StockNewsResponse)
async def get_stock_news(
    ticker: str,
    limit: int = Query(default=10, description="Number of news articles to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent news for a stock"""
    news = db.query(StockNews).filter(
        StockNews.primary_ticker == ticker.upper()
    ).order_by(StockNews.publish_time.desc()).limit(limit).all()

    return StockNewsResponse(
        ticker=ticker.upper(),
        count=len(news),
        articles=news
    )


@router.get("/trending", response_model=TrendingResponse)
async def get_trending_stocks(
    limit: int = Query(default=10, description="Number of trending stocks to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get trending stocks based on recent activity"""
    try:
        from sqlalchemy import func, desc

        cutoff_date = datetime.utcnow() - timedelta(days=1)

        trending = db.query(
            StockSentiment.ticker,
            func.sum(StockSentiment.total_mentions).label('total_mentions'),
            func.avg(StockSentiment.avg_sentiment).label('avg_sentiment')
        ).filter(
            StockSentiment.date >= cutoff_date
        ).group_by(
            StockSentiment.ticker
        ).order_by(
            desc('total_mentions')
        ).limit(limit).all()

        stocks = [
            TrendingStock(
                ticker=stock.ticker,
                mentions=int(stock.total_mentions),
                avg_sentiment=float(stock.avg_sentiment) if stock.avg_sentiment else 0
            )
            for stock in trending
        ]

        return TrendingResponse(
            period="24h",
            count=len(stocks),
            stocks=stocks
        )

    except Exception:
        return TrendingResponse(
            period="24h",
            count=0,
            stocks=[]
        )