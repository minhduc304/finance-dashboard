"""
Insider trading API endpoints - Enhanced version
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

from app.core.database import get_db
from app.models import InsiderTrade, InsiderAlert, InsiderSummary, TopInsider

router = APIRouter()

# Response models
class InsiderTradeResponse(BaseModel):
    ticker: Optional[str]
    transaction_date: Optional[datetime]
    trade_date: Optional[datetime]
    company_name: Optional[str]
    owner_name: Optional[str]
    title: Optional[str]
    transaction_type: Optional[str]
    last_price: Optional[float]
    quantity: Optional[int]
    shares_held: Optional[int]
    ownership_percentage: Optional[float]
    value: Optional[float]

class StockInsiderTradesResponse(BaseModel):
    ticker: str
    period_days: int
    transaction_type_filter: Optional[str]
    total_trades: int
    trades: List[InsiderTradeResponse]

class InsiderAlertResponse(BaseModel):
    alert_type: Optional[str]
    ticker: Optional[str]
    company_name: Optional[str]
    severity: Optional[str]
    description: Optional[str]
    total_value: Optional[float]
    num_insiders: Optional[int]
    alert_date: Optional[datetime]

class InsiderAlertsResponse(BaseModel):
    count: int
    severity_filter: Optional[str]
    alerts: List[InsiderAlertResponse]

class PurchaseData(BaseModel):
    total_purchases: Optional[int]
    total_purchase_value: Optional[float]
    total_purchase_shares: Optional[int]
    avg_purchase_price: Optional[float]
    last_purchase_date: Optional[datetime]

class SaleData(BaseModel):
    total_sales: Optional[int]
    total_sale_value: Optional[float]
    total_sale_shares: Optional[int]
    avg_sale_price: Optional[float]
    last_sale_date: Optional[datetime]

class NetActivityData(BaseModel):
    net_insider_activity: Optional[float]
    net_shares_traded: Optional[int]
    last_activity_date: Optional[datetime]

class ParticipantData(BaseModel):
    unique_buyers: Optional[int]
    unique_sellers: Optional[int]

class InsiderSummaryResponse(BaseModel):
    ticker: str
    summary_exists: bool
    company_name: Optional[str] = None
    purchases: Optional[PurchaseData] = None
    sales: Optional[SaleData] = None
    net_activity: Optional[NetActivityData] = None
    participants: Optional[ParticipantData] = None
    updated_at: Optional[datetime] = None

class TraderPerformance(BaseModel):
    avg_return_30d: Optional[float]
    avg_return_90d: Optional[float]
    win_rate: Optional[float]

class TopTraderResponse(BaseModel):
    owner_name: Optional[str]
    most_common_title: Optional[str]
    total_trades: Optional[int]
    total_purchases: Optional[int]
    total_sales: Optional[int]
    total_value_traded: Optional[float]
    total_purchase_value: Optional[float]
    total_sale_value: Optional[float]
    primary_company: Optional[str]
    last_trade_date: Optional[datetime]
    last_trade_ticker: Optional[str]
    last_trade_type: Optional[str]
    performance: Optional[TraderPerformance]

class TopTradersResponse(BaseModel):
    count: int
    sort_by: str
    traders: List[TopTraderResponse]

class AllInsiderTradesResponse(BaseModel):
    total_trades: int
    period_days: int
    trades: List[InsiderTradeResponse]


@router.get("/recent", response_model=AllInsiderTradesResponse)
async def get_recent_insider_trades(
    days: int = Query(default=30, description="Number of days of insider trading history"),
    limit: int = Query(default=100, description="Maximum number of trades to return"),
    transaction_type: Optional[str] = Query(default=None, description="Filter by transaction type (P=Purchase, S=Sale)"),
    db: Session = Depends(get_db)
):
    """Get recent insider trading data across all stocks"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(InsiderTrade).filter(
        InsiderTrade.transaction_date >= cutoff_date
    )

    if transaction_type:
        query = query.filter(InsiderTrade.transaction_type.like(f"{transaction_type}%"))

    trades = query.order_by(InsiderTrade.transaction_date.desc()).limit(limit).all()

    # Convert SQLAlchemy models to Pydantic response models
    trade_responses = []
    for trade in trades:
        trade_responses.append(InsiderTradeResponse(
            ticker=trade.ticker,
            transaction_date=trade.transaction_date,
            trade_date=trade.trade_date,
            company_name=trade.company_name,
            owner_name=trade.owner_name,
            title=trade.title,
            transaction_type=trade.transaction_type,
            last_price=trade.last_price,
            quantity=trade.quantity,
            shares_held=trade.shares_held,
            ownership_percentage=trade.ownership_percentage,
            value=trade.value
        ))

    return AllInsiderTradesResponse(
        total_trades=len(trades),
        period_days=days,
        trades=trade_responses
    )


@router.get("/stock/{ticker}", response_model=StockInsiderTradesResponse)
async def get_insider_trades(
    ticker: str,
    days: int = Query(default=30, description="Number of days of insider trading history"),
    transaction_type: Optional[str] = Query(default=None, description="Filter by transaction type (P=Purchase, S=Sale)"),
    db: Session = Depends(get_db)
):
    """Get insider trading data for a specific stock"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(InsiderTrade).filter(
        InsiderTrade.ticker == ticker.upper(),
        InsiderTrade.transaction_date >= cutoff_date
    )

    if transaction_type:
        query = query.filter(InsiderTrade.transaction_type == transaction_type)

    trades = query.order_by(InsiderTrade.transaction_date.desc()).all()

    # Convert SQLAlchemy models to Pydantic response models
    trade_responses = []
    for trade in trades:
        trade_responses.append(InsiderTradeResponse(
            transaction_date=trade.transaction_date,
            trade_date=trade.trade_date,
            company_name=trade.company_name,
            owner_name=trade.owner_name,
            title=trade.title,
            transaction_type=trade.transaction_type,
            last_price=trade.last_price,
            quantity=trade.quantity,
            shares_held=trade.shares_held,
            ownership_percentage=trade.ownership_percentage,
            value=trade.value
        ))

    return StockInsiderTradesResponse(
        ticker=ticker.upper(),
        period_days=days,
        transaction_type_filter=transaction_type,
        total_trades=len(trades),
        trades=trade_responses
    )


@router.get("/alerts", response_model=InsiderAlertsResponse)
async def get_insider_alerts(
    limit: int = Query(default=20, description="Number of alerts to return"),
    severity: Optional[str] = Query(default=None, description="Filter by severity: low, medium, high"),
    db: Session = Depends(get_db)
):
    """Get notable insider trading alerts and patterns"""
    try:
        query = db.query(InsiderAlert).filter(InsiderAlert.is_active == 1)

        if severity:
            query = query.filter(InsiderAlert.severity == severity)

        alerts = query.order_by(InsiderAlert.alert_date.desc()).limit(limit).all()

        # Convert SQLAlchemy models to Pydantic response models
        alert_responses = []
        for alert in alerts:
            alert_responses.append(InsiderAlertResponse(
                alert_type=alert.alert_type,
                ticker=alert.ticker,
                company_name=alert.company_name,
                message=alert.message,
                severity=alert.severity,
                alert_date=alert.alert_date,
                details=alert.details
            ))

        return InsiderAlertsResponse(
            count=len(alerts),
            severity_filter=severity,
            alerts=alert_responses
        )

    except Exception:
        return InsiderAlertsResponse(
            count=0,
            severity_filter=severity,
            alerts=[]
        )


@router.get("/summary/{ticker}", response_model=InsiderSummaryResponse)
async def get_insider_summary(
    ticker: str,
    db: Session = Depends(get_db)
):
    """Get insider trading summary for a specific stock"""
    summary = db.query(InsiderSummary).filter(InsiderSummary.ticker == ticker.upper()).first()

    if not summary:
        return InsiderSummaryResponse(
            ticker=ticker.upper(),
            summary_exists=False
        )

    return InsiderSummaryResponse(
        ticker=ticker.upper(),
        summary_exists=True,
        company_name=summary.company_name,
        purchases=PurchaseData(
            total_purchases=summary.total_purchases,
            total_purchase_value=summary.total_purchase_value,
            total_purchase_shares=summary.total_purchase_shares,
            avg_purchase_price=summary.avg_purchase_price,
            last_purchase_date=summary.last_purchase_date
        ),
        sales=SaleData(
            total_sales=summary.total_sales,
            total_sale_value=summary.total_sale_value,
            total_sale_shares=summary.total_sale_shares,
            avg_sale_price=summary.avg_sale_price,
            last_sale_date=summary.last_sale_date
        ),
        net_activity=NetActivityData(
            net_insider_activity=summary.net_insider_activity,
            net_shares_traded=summary.net_shares_traded,
            last_activity_date=summary.last_activity_date
        ),
        participants=ParticipantData(
            unique_buyers=summary.unique_buyers,
            unique_sellers=summary.unique_sellers
        ),
        updated_at=summary.updated_at
    )


@router.get("/top_traders", response_model=TopTradersResponse)
async def get_top_insider_traders(
    limit: int = Query(default=10, description="Number of top traders to return"),
    sort_by: str = Query(default="volume", description="Sort by: volume, trades, recent"),
    db: Session = Depends(get_db)
):
    """Get top insider traders by volume or activity"""
    try:
        if sort_by == "volume":
            query = db.query(TopInsider).order_by(TopInsider.total_value_traded.desc())
        elif sort_by == "trades":
            query = db.query(TopInsider).order_by(TopInsider.total_trades.desc())
        elif sort_by == "recent":
            query = db.query(TopInsider).order_by(TopInsider.last_trade_date.desc())
        else:
            query = db.query(TopInsider).order_by(TopInsider.total_value_traded.desc())

        traders = query.limit(limit).all()

        trader_responses = [
            TopTraderResponse(
                owner_name=trader.owner_name,
                most_common_title=trader.most_common_title,
                total_trades=trader.total_trades,
                total_purchases=trader.total_purchases,
                total_sales=trader.total_sales,
                total_value_traded=trader.total_value_traded,
                total_purchase_value=trader.total_purchase_value,
                total_sale_value=trader.total_sale_value,
                primary_company=trader.primary_company,
                last_trade_date=trader.last_trade_date,
                last_trade_ticker=trader.last_trade_ticker,
                last_trade_type=trader.last_trade_type,
                performance=TraderPerformance(
                    avg_return_30d=trader.avg_return_30d,
                    avg_return_90d=trader.avg_return_90d,
                    win_rate=trader.win_rate
                )
            )
            for trader in traders
        ]

        return TopTradersResponse(
            count=len(traders),
            sort_by=sort_by,
            traders=trader_responses
        )

    except Exception:
        return TopTradersResponse(
            count=0,
            sort_by=sort_by,
            traders=[]
        )