"""
Redis caching utilities for API responses
"""

import redis
import json
import functools
import hashlib
from typing import Any, Callable, Optional
from datetime import timedelta
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis client
try:
    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        socket_keepalive=True,
        retry_on_timeout=True
    )
    # Test connection
    redis_client.ping()
    logger.info("Redis cache client initialized successfully")
except redis.RedisError as e:
    logger.error(f"Redis connection failed: {e}")
    redis_client = None


def _serialize(obj: Any) -> str:
    """Serialize object to JSON string"""
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError) as e:
        logger.error(f"Serialization error: {e}")
        return None


def _deserialize(data: str) -> Any:
    """Deserialize JSON string to object"""
    try:
        return json.loads(data)
    except (TypeError, ValueError, json.JSONDecodeError) as e:
        logger.error(f"Deserialization error: {e}")
        return None


def _build_cache_key(*args, **kwargs) -> str:
    """Build cache key from function args and kwargs"""
    # Create a stable string representation
    key_parts = []

    # Add positional args
    for arg in args:
        if hasattr(arg, '__dict__'):
            # Skip complex objects like DB sessions
            continue
        key_parts.append(str(arg))

    # Add keyword args
    for k, v in sorted(kwargs.items()):
        if hasattr(v, '__dict__'):
            continue
        key_parts.append(f"{k}={v}")

    # Create hash for long keys
    key_str = ":".join(key_parts)
    if len(key_str) > 200:
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return key_hash

    return key_str


def cache_response(
    ttl: int = 300,  # 5 minutes default
    key_prefix: str = "api",
    key_builder: Optional[Callable] = None
):
    """
    Decorator to cache API endpoint responses in Redis

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        key_builder: Custom function to build cache key from args

    Usage:
        @cache_response(ttl=300, key_prefix="stock_info")
        async def get_stock_info(ticker: str, db: Session):
            # ... fetch data
            return data
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Skip caching if Redis is unavailable
            if redis_client is None:
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                cache_key = f"{key_prefix}:{key_builder(*args, **kwargs)}"
            else:
                # Default: use function name and args
                args_key = _build_cache_key(*args[1:], **kwargs)  # Skip 'self' if present
                cache_key = f"{key_prefix}:{func.__name__}:{args_key}"

            try:
                # Try to get from cache
                cached_value = redis_client.get(cache_key)
                if cached_value:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return _deserialize(cached_value)
                else:
                    logger.debug(f"Cache MISS: {cache_key}")
            except redis.RedisError as e:
                logger.warning(f"Cache read error for {cache_key}: {e}")

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            try:
                serialized = _serialize(result)
                if serialized:
                    redis_client.setex(cache_key, ttl, serialized)
                    logger.debug(f"Cache SET: {cache_key} (TTL: {ttl}s)")
            except redis.RedisError as e:
                logger.warning(f"Cache write error for {cache_key}: {e}")

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Sync version for non-async functions
            if redis_client is None:
                return func(*args, **kwargs)

            if key_builder:
                cache_key = f"{key_prefix}:{key_builder(*args, **kwargs)}"
            else:
                args_key = _build_cache_key(*args[1:], **kwargs)
                cache_key = f"{key_prefix}:{func.__name__}:{args_key}"

            try:
                cached_value = redis_client.get(cache_key)
                if cached_value:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return _deserialize(cached_value)
                else:
                    logger.debug(f"Cache MISS: {cache_key}")
            except redis.RedisError as e:
                logger.warning(f"Cache read error for {cache_key}: {e}")

            result = func(*args, **kwargs)

            try:
                serialized = _serialize(result)
                if serialized:
                    redis_client.setex(cache_key, ttl, serialized)
                    logger.debug(f"Cache SET: {cache_key} (TTL: {ttl}s)")
            except redis.RedisError as e:
                logger.warning(f"Cache write error for {cache_key}: {e}")

            return result

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def invalidate_cache_pattern(pattern: str) -> int:
    """
    Delete all cache keys matching pattern

    Args:
        pattern: Redis key pattern (e.g., "stock_*:AAPL*")

    Returns:
        Number of keys deleted
    """
    if redis_client is None:
        return 0

    try:
        deleted_count = 0
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                deleted_count += redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache keys matching '{pattern}'")
            if cursor == 0:
                break
        return deleted_count
    except redis.RedisError as e:
        logger.error(f"Cache invalidation error: {e}")
        return 0


def invalidate_ticker_cache(ticker: str):
    """Invalidate all cache entries for a specific ticker"""
    patterns = [
        f"stock_*:*:*{ticker}*",  # Matches stock_info:get_stock_info:AAPL
        f"*:*:*{ticker}*",  # Matches any key with ticker in args
        f"*{ticker}*"  # Catch-all for any key containing ticker
    ]
    total_deleted = 0
    for pattern in patterns:
        total_deleted += invalidate_cache_pattern(pattern)
    logger.info(f"Invalidated {total_deleted} cache entries for ticker {ticker}")
    return total_deleted


def clear_all_cache():
    """Clear all cache entries (use with caution!)"""
    if redis_client is None:
        return 0

    try:
        # Only clear keys with our prefixes
        patterns = ['api:*', 'stock_*', 'market:*', 'sentiment:*', 'portfolio:*']
        total_deleted = 0
        for pattern in patterns:
            total_deleted += invalidate_cache_pattern(pattern)
        logger.warning(f"Cleared all cache - {total_deleted} keys deleted")
        return total_deleted
    except redis.RedisError as e:
        logger.error(f"Cache clear error: {e}")
        return 0


def get_cache_stats() -> dict:
    """Get Redis cache statistics"""
    if redis_client is None:
        return {
            "status": "unavailable",
            "error": "Redis client not initialized"
        }

    try:
        info = redis_client.info('stats')
        keyspace = redis_client.info('keyspace')

        # Calculate hit rate
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total_requests = hits + misses
        hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0

        # Get memory info
        memory_info = redis_client.info('memory')

        return {
            "status": "healthy",
            "total_connections": info.get('total_connections_received', 0),
            "total_commands": info.get('total_commands_processed', 0),
            "keyspace_hits": hits,
            "keyspace_misses": misses,
            "hit_rate_percent": round(hit_rate, 2),
            "total_keys": keyspace.get('db0', {}).get('keys', 0) if 'db0' in keyspace else 0,
            "memory_used_mb": round(memory_info.get('used_memory', 0) / 1024 / 1024, 2),
            "memory_peak_mb": round(memory_info.get('used_memory_peak', 0) / 1024 / 1024, 2),
            "evicted_keys": info.get('evicted_keys', 0)
        }
    except redis.RedisError as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def warm_cache(func: Callable, params_list: list):
    """
    Warm up cache by pre-populating with data

    Args:
        func: Function to call
        params_list: List of parameter tuples to call function with

    Usage:
        warm_cache(get_stock_info, [('AAPL',), ('MSFT',), ('GOOGL',)])
    """
    warmed = 0
    for params in params_list:
        try:
            if isinstance(params, tuple):
                func(*params)
            else:
                func(params)
            warmed += 1
        except Exception as e:
            logger.error(f"Cache warming error for {params}: {e}")
            continue

    logger.info(f"Warmed cache with {warmed}/{len(params_list)} entries")
    return warmed
