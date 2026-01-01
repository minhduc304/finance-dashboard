"""
Alpha Vantage API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

from app.core.database import get_db
from app.models import TechnicalIndicator, CompanyFundamentals

router = APIRouter()


# Response models
class TechnicalIndicatorResponse(BaseModel):
    ticker: str
    indicator_type: str
    date: datetime
    value: float
    value_2: Optional[float] = None
    value_3: Optional[float] = None

    class Config:
        from_attributes = True


class CompanyFundamentalsResponse(BaseModel):
    ticker: str
    name: Optional[str] = None
    description: Optional[str] = None
    peg_ratio: Optional[float] = None
    return_on_equity: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    return_on_assets: Optional[float] = None
    revenue_ttm: Optional[float] = None
    gross_profit_ttm: Optional[float] = None
    ebitda: Optional[float] = None
    analyst_target_price: Optional[float] = None
    moving_avg_50_day: Optional[float] = None
    moving_avg_200_day: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    book_value: Optional[float] = None
    revenue_per_share: Optional[float] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("/stocks/{ticker}/indicators", response_model=List[TechnicalIndicatorResponse])
async def get_technical_indicators(
    ticker: str,
    indicator_type: Optional[str] = Query(None, description="Filter by indicator type (RSI, MACD, SMA, etc.)"),
    days: int = Query(30, le=365, description="Number of days of historical data"),
    db: Session = Depends(get_db)
):
    """
    Get technical indicators for a stock

    Available indicator types: RSI, MACD, SMA, EMA, BBANDS, ADX, CCI, STOCH
    """
    query = db.query(TechnicalIndicator).filter(TechnicalIndicator.ticker == ticker.upper())

    if indicator_type:
        query = query.filter(TechnicalIndicator.indicator_type == indicator_type.upper())

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    query = query.filter(TechnicalIndicator.date >= cutoff_date)

    indicators = query.order_by(TechnicalIndicator.date.desc()).all()

    if not indicators:
        raise HTTPException(
            status_code=404,
            detail=f"No technical indicators found for {ticker}"
        )

    return indicators


@router.get("/stocks/{ticker}/fundamentals", response_model=CompanyFundamentalsResponse)
async def get_company_fundamentals(
    ticker: str,
    db: Session = Depends(get_db)
):
    """
    Get company fundamental data from Alpha Vantage

    Includes metrics like PEG ratio, profit margin, ROE, analyst targets, etc.
    """
    fundamental = db.query(CompanyFundamentals).filter_by(ticker=ticker.upper()).first()

    if not fundamental:
        raise HTTPException(
            status_code=404,
            detail=f"Fundamentals not found for {ticker}. Data may not be collected yet."
        )

    return fundamental


@router.get("/indicators/available")
async def get_available_indicators(db: Session = Depends(get_db)):
    """
    Get list of available indicator types and tickers in the database
    """
    from sqlalchemy import func, distinct

    # Get unique indicator types
    indicator_types = db.query(distinct(TechnicalIndicator.indicator_type)).all()
    indicator_types = [it[0] for it in indicator_types]

    # Get unique tickers with indicators
    tickers = db.query(distinct(TechnicalIndicator.ticker)).all()
    tickers = [t[0] for t in tickers]

    # Get count by indicator type
    counts = db.query(
        TechnicalIndicator.indicator_type,
        func.count(TechnicalIndicator.id).label('count')
    ).group_by(TechnicalIndicator.indicator_type).all()

    return {
        "indicator_types": indicator_types,
        "tickers_with_indicators": tickers,
        "counts": {c[0]: c[1] for c in counts}
    }


@router.get("/fundamentals/available")
async def get_available_fundamentals(db: Session = Depends(get_db)):
    """
    Get list of tickers with fundamental data available
    """
    from sqlalchemy import func

    fundamentals = db.query(
        CompanyFundamentals.ticker,
        CompanyFundamentals.name,
        CompanyFundamentals.updated_at
    ).all()

    return {
        "count": len(fundamentals),
        "tickers": [{
            "ticker": f.ticker,
            "name": f.name,
            "updated_at": f.updated_at
        } for f in fundamentals]
    }
