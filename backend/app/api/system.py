"""
System and cache management API endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from app.core.cache import (
    get_cache_stats,
    invalidate_cache_pattern,
    invalidate_ticker_cache,
    clear_all_cache
)

router = APIRouter()


class CacheStatsResponse(BaseModel):
    status: str
    total_connections: Optional[int] = None
    total_commands: Optional[int] = None
    keyspace_hits: Optional[int] = None
    keyspace_misses: Optional[int] = None
    hit_rate_percent: Optional[float] = None
    total_keys: Optional[int] = None
    memory_used_mb: Optional[float] = None
    memory_peak_mb: Optional[float] = None
    evicted_keys: Optional[int] = None
    error: Optional[str] = None


class CacheInvalidateResponse(BaseModel):
    status: str
    keys_deleted: int
    pattern: Optional[str] = None
    ticker: Optional[str] = None


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def cache_stats():
    """
    Get Redis cache statistics

    Returns hit rates, memory usage, and performance metrics
    """
    stats = get_cache_stats()
    return stats


@router.post("/cache/invalidate", response_model=CacheInvalidateResponse)
async def invalidate_cache(
    pattern: Optional[str] = Query(None, description="Redis key pattern to delete (e.g., 'stock_*:AAPL*')"),
    ticker: Optional[str] = Query(None, description="Ticker symbol to invalidate all cache for")
):
    """
    Invalidate cache entries by pattern or ticker

    - **pattern**: Redis key pattern (e.g., "stock_*:AAPL*")
    - **ticker**: Stock ticker (invalidates all cache entries for this ticker)

    Requires either pattern or ticker parameter.
    """
    if not pattern and not ticker:
        raise HTTPException(
            status_code=400,
            detail="Must provide either 'pattern' or 'ticker' parameter"
        )

    if ticker:
        keys_deleted = invalidate_ticker_cache(ticker.upper())
        return CacheInvalidateResponse(
            status="success",
            keys_deleted=keys_deleted,
            ticker=ticker.upper()
        )

    if pattern:
        keys_deleted = invalidate_cache_pattern(pattern)
        return CacheInvalidateResponse(
            status="success",
            keys_deleted=keys_deleted,
            pattern=pattern
        )


@router.post("/cache/clear")
async def clear_cache():
    """
    Clear ALL cache entries

    ⚠️ WARNING: This will clear all cached data. Use with caution!
    """
    keys_deleted = clear_all_cache()
    return {
        "status": "success",
        "message": "All cache entries cleared",
        "keys_deleted": keys_deleted
    }


@router.get("/health")
async def health_check():
    """
    System health check

    Checks status of cache and other services
    """
    cache_stats_data = get_cache_stats()

    return {
        "status": "healthy",
        "services": {
            "api": "healthy",
            "cache": cache_stats_data.get("status", "unknown")
        },
        "cache_hit_rate": cache_stats_data.get("hit_rate_percent", 0)
    }
