"""
Portfolio API endpoints - Enhanced version
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models import User, Portfolio, Holding, Transaction
from app.services.data_service import DataService

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
    symbol: str
    quantity: float
    average_cost: float
    current_price: Optional[float]
    market_value: Optional[float]
    gain_loss: Optional[float]

class TransactionResponse(BaseModel):
    id: int
    type: str
    symbol: Optional[str]
    quantity: Optional[float]
    price: Optional[float]
    total_amount: float
    transaction_date: datetime

@router.get("/", response_model=List[PortfolioSummary])
async def get_user_portfolios(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all portfolios for authenticated user"""
    portfolios = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
    return portfolios

@router.get("/{portfolio_id}", response_model=PortfolioSummary)
async def get_portfolio_details(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific portfolio details"""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == current_user.id
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    return portfolio

@router.get("/{portfolio_id}/holdings", response_model=List[HoldingResponse])
async def get_portfolio_holdings(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get holdings for a specific portfolio"""
    # Verify user owns the portfolio
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == current_user.id
    ).first()

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
    limit: int = Query(50, description="Number of transactions to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent transactions for a portfolio"""
    # Verify user owns the portfolio
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == current_user.id
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    transactions = db.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id
    ).order_by(Transaction.transaction_date.desc()).limit(limit).all()

    return transactions

@router.post("/{portfolio_id}/update")
async def update_portfolio_values(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update portfolio with latest market prices"""
    # Verify user owns the portfolio
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == current_user.id
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    # Use data service to update portfolio
    try:
        result = DataService.update_portfolio(portfolio_id, db)
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update portfolio: {str(e)}"
        )

@router.get("/{portfolio_id}/performance")
async def get_portfolio_performance(
    portfolio_id: int,
    days: int = Query(30, description="Number of days for performance calculation"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get portfolio performance metrics"""
    # Verify user owns the portfolio
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == current_user.id
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    # Calculate performance metrics
    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio_id).all()

    total_market_value = sum(h.market_value or 0 for h in holdings)
    total_cost = sum(h.quantity * h.average_cost for h in holdings)
    total_gain_loss = total_market_value - total_cost

    # Get recent transactions for activity analysis
    recent_date = datetime.utcnow() - timedelta(days=days)
    recent_transactions = db.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id,
        Transaction.transaction_date >= recent_date
    ).all()

    return {
        "portfolio_id": portfolio_id,
        "period_days": days,
        "total_market_value": total_market_value,
        "total_cost": total_cost,
        "total_gain_loss": total_gain_loss,
        "total_return_percent": (total_gain_loss / total_cost * 100) if total_cost > 0 else 0,
        "holdings_count": len(holdings),
        "recent_transactions": len(recent_transactions),
        "cash_balance": portfolio.cash_balance,
        "last_updated": portfolio.updated_at
    }

@router.post("/{portfolio_id}/sync")
async def sync_portfolio_with_broker(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger sync with brokerage account (Wealthsimple)"""
    # Verify user owns the portfolio
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == current_user.id
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    # Trigger background sync task
    try:
        from app.tasks import sync_wealthsimple_portfolios
        task = sync_wealthsimple_portfolios.delay(current_user.id)

        return {
            "message": "Portfolio sync initiated",
            "task_id": task.id,
            "status": "pending"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate sync: {str(e)}"
        )