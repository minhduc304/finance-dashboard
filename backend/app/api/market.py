"""
Market data API endpoints - Enhanced version
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

from app.core.database import get_db
from app.models import StockInfo, StockPrice, StockNews, StockSentiment
from app.services.data_service import DataService
from app.core.cache import cache_response

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
    current_price: Optional[float]

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


@router.get("/stocks", response_model=List[StockInfoResponse])
@cache_response(ttl=180, key_prefix="market")  # 3 min cache
async def get_all_stocks(
    db: Session = Depends(get_db)
):
    """Get all available stocks with latest prices"""
    from sqlalchemy import func, and_

    # Subquery to get the latest price date for each ticker
    latest_price_subq = db.query(
        StockPrice.ticker,
        func.max(StockPrice.date).label('latest_date')
    ).group_by(StockPrice.ticker).subquery()

    # Query stocks with their latest prices
    stocks_with_prices = db.query(
        StockInfo,
        StockPrice.close.label('current_price')
    ).outerjoin(
        latest_price_subq,
        StockInfo.ticker == latest_price_subq.c.ticker
    ).outerjoin(
        StockPrice,
        and_(
            StockInfo.ticker == StockPrice.ticker,
            StockPrice.date == latest_price_subq.c.latest_date
        )
    ).filter(
        StockInfo.ticker != 'SEC-C-CAD'  # Exclude cash accounts
    ).all()

    # Transform results to include current_price
    results = []
    for stock_info, current_price in stocks_with_prices:
        stock_dict = {
            'ticker': stock_info.ticker,
            'name': stock_info.name,
            'long_name': stock_info.long_name,
            'sector': stock_info.sector,
            'industry': stock_info.industry,
            'exchange': stock_info.exchange,
            'market_cap': stock_info.market_cap,
            'beta': stock_info.beta,
            'trailing_pe': stock_info.trailing_pe,
            'dividend_yield': stock_info.dividend_yield,
            'updated_at': stock_info.updated_at,
            'current_price': float(current_price) if current_price else None
        }
        results.append(stock_dict)

    return results


@router.get("/stocks/{ticker}", response_model=StockInfoResponse)
@cache_response(ttl=300, key_prefix="stock_info")  # 5 min cache
async def get_stock_info(
    ticker: str,
    db: Session = Depends(get_db)
):
    """Get basic stock information"""
    stock = db.query(StockInfo).filter(StockInfo.ticker == ticker.upper()).first()

    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {ticker} not found"
        )

    # Get latest price
    latest_price = db.query(StockPrice).filter(
        StockPrice.ticker == ticker.upper()
    ).order_by(StockPrice.date.desc()).first()

    return {
        'ticker': stock.ticker,
        'name': stock.name,
        'long_name': stock.long_name,
        'sector': stock.sector,
        'industry': stock.industry,
        'exchange': stock.exchange,
        'market_cap': stock.market_cap,
        'beta': stock.beta,
        'trailing_pe': stock.trailing_pe,
        'dividend_yield': stock.dividend_yield,
        'updated_at': stock.updated_at,
        'current_price': float(latest_price.close) if latest_price else None
    }


@router.get("/stocks/{ticker}/price", response_model=StockPriceResponse)
@cache_response(ttl=60, key_prefix="stock_price")  # 1 min cache
async def get_stock_price(
    ticker: str,
    days: int = Query(default=30, description="Number of days of price history"),
    db: Session = Depends(get_db)
):
    """Get stock price history"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    prices = db.query(StockPrice).filter(
        StockPrice.ticker == ticker.upper(),
        StockPrice.date >= cutoff_date
    ).order_by(StockPrice.date.desc()).all()

    if not prices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data found for {ticker}"
        )

    # Convert SQLAlchemy objects to dicts
    price_points = []
    for price in prices:
        price_points.append({
            'date': price.date,
            'open': price.open,
            'high': price.high,
            'low': price.low,
            'close': price.close,
            'volume': price.volume,
            'daily_return': price.daily_return
        })

    return {
        'ticker': ticker.upper(),
        'period_days': days,
        'data_points': len(prices),
        'prices': price_points
    }


@router.get("/stocks/{ticker}/news", response_model=StockNewsResponse)
@cache_response(ttl=900, key_prefix="stock_news")  # 15 min cache
async def get_stock_news(
    ticker: str,
    limit: int = Query(default=10, description="Number of news articles to return"),
    db: Session = Depends(get_db)
):
    """Get recent news for a stock"""
    news = db.query(StockNews).filter(
        StockNews.primary_ticker == ticker.upper()
    ).order_by(StockNews.publish_time.desc()).limit(limit).all()

    # Convert SQLAlchemy models to dicts
    articles = []
    for article in news:
        articles.append({
            'title': article.title,
            'link': article.link,
            'publisher': article.publisher,
            'publish_time': article.publish_time,
            'related_tickers': article.related_tickers,
            'sentiment_score': article.sentiment_score,
            'sentiment_label': article.sentiment_label
        })

    return {
        'ticker': ticker.upper(),
        'count': len(news),
        'articles': articles
    }


@router.get("/trending", response_model=TrendingResponse)
async def get_trending_stocks(
    limit: int = Query(default=10, description="Number of trending stocks to return"),
    db: Session = Depends(get_db)
):
    """Get trending stocks based on recent activity"""
    try:
        from sqlalchemy import func, desc

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=1)

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