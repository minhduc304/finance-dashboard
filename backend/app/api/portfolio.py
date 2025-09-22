"""
Portfolio API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Portfolio, Holding, Transaction

router = APIRouter()

# Response models
class PortfolioSummary(BaseModel):
    id: int
    name: str
    total_value: float
    total_cost: float
    total_gain_loss: float
    cash_balance: float
    updated_at: datetime

class HoldingResponse(BaseModel):
    id: int
    ticker: str
    name: Optional[str]
    quantity: float
    average_cost: float
    current_price: Optional[float]
    market_value: Optional[float]
    unrealized_gain: Optional[float]

class TransactionResponse(BaseModel):
    id: int
    type: str
    symbol: Optional[str]
    quantity: Optional[float]
    price: Optional[float]
    total_amount: float
    transaction_date: datetime

@router.get("/", response_model=List[PortfolioSummary])
async def get_portfolios(db: Session = Depends(get_db)):
    """Get all portfolios"""
    portfolios = db.query(Portfolio).all()
    return portfolios

@router.get("/{portfolio_id}", response_model=PortfolioSummary)
async def get_portfolio_details(
    portfolio_id: int,
    db: Session = Depends(get_db)
):
    """Get specific portfolio details"""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    return portfolio

@router.get("/{portfolio_id}/holdings", response_model=List[HoldingResponse])
async def get_portfolio_holdings(
    portfolio_id: int,
    db: Session = Depends(get_db)
):
    """Get all holdings for a specific portfolio"""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio_id).all()
    return holdings

@router.get("/{portfolio_id}/transactions", response_model=List[TransactionResponse])
async def get_portfolio_transactions(
    portfolio_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=1000)
):
    """Get transaction history for a specific portfolio"""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    transactions = (
        db.query(Transaction)
        .filter(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.transaction_date.desc())
        .limit(limit)
        .all()
    )
    return transactions

@router.get("/{portfolio_id}/performance")
async def get_portfolio_performance(
    portfolio_id: int,
    db: Session = Depends(get_db)
):
    """Get performance metrics for a specific portfolio"""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio_id).all()

    # Calculate performance metrics
    total_cost = sum(h.average_cost * h.quantity for h in holdings if h.average_cost and h.quantity)
    total_market_value = sum(h.market_value for h in holdings if h.market_value)
    total_unrealized_gain = sum(h.unrealized_gain for h in holdings if h.unrealized_gain)

    return {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio.name,
        "total_cost": total_cost,
        "total_market_value": total_market_value,
        "total_unrealized_gain": total_unrealized_gain,
        "total_gain_loss_percent": (total_unrealized_gain / total_cost * 100) if total_cost > 0 else 0,
        "holdings_count": len(holdings),
        "cash_balance": portfolio.cash_balance
    }

@router.get("/aggregated/overview")
async def get_aggregated_portfolio_overview(db: Session = Depends(get_db)):
    """Get aggregated overview across all portfolios"""
    portfolios = db.query(Portfolio).all()

    total_value = sum(p.total_value for p in portfolios if p.total_value)
    total_cost = sum(p.total_cost for p in portfolios if p.total_cost)
    total_gain_loss = sum(p.total_gain_loss for p in portfolios if p.total_gain_loss)
    total_cash = sum(p.cash_balance for p in portfolios if p.cash_balance)

    return {
        "total_portfolios": len(portfolios),
        "total_value": total_value,
        "total_cost": total_cost,
        "total_gain_loss": total_gain_loss,
        "total_gain_loss_percent": (total_gain_loss / total_cost * 100) if total_cost > 0 else 0,
        "total_cash_balance": total_cash,
        "portfolios": [
            {
                "id": p.id,
                "name": p.name,
                "value": p.total_value,
                "gain_loss": p.total_gain_loss,
                "updated_at": p.updated_at
            }
            for p in portfolios
        ]
    }

@router.post("/sync")
async def sync_portfolios(db: Session = Depends(get_db)):
    """Trigger portfolio synchronization with Wealthsimple"""

    # Trigger background sync task
    try:
        from app.tasks import sync_wealthsimple_portfolios
        task = sync_wealthsimple_portfolios.delay()

        return {
            "message": "Portfolio sync initiated",
            "task_id": task.id,
            "status": "pending"
        }

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background task system not available"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate sync: {str(e)}"
        )