"""
Bounded LRU Cache Manager with Memory Tracking

Replaces unbounded cache dictionary with size-aware LRU eviction.
Prevents memory bloat by limiting total cache size to 100MB.

Usage:
    from api.utils.cache_manager import get_cached, clear_cache

    # Simple caching with TTL
    result = get_cached('my_key', ttl_seconds=300, compute_fn=expensive_function)

    # Or use decorator
    @cached(ttl_seconds=3600)
    def expensive_function(arg1, arg2):
        # ... expensive computation ...
        return result
"""

import time
import sys
import threading
from collections import OrderedDict
from typing import Any, Callable, Optional
from functools import wraps


class LRUCacheManager:
    """
    Thread-safe LRU cache with memory limit and TTL support.

    Features:
    - LRU eviction (least recently used)
    - Memory-aware (tracks approximate size in bytes)
    - TTL expiration per entry
    - Thread-safe operations
    - Automatic eviction when memory limit exceeded
    """

    def __init__(self, max_memory_mb: int = 100):
        """
        Initialize cache manager.

        Args:
            max_memory_mb: Maximum memory usage in megabytes (default 100MB)
        """
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cache = OrderedDict()  # LRU: {key: (value, expiry_time, size_bytes)}
        self._lock = threading.RLock()
        self._current_memory = 0
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, expiry_time, size_bytes = self._cache[key]

            # Check expiration
            if expiry_time and time.time() > expiry_time:
                # Expired - remove entry
                self._cache.pop(key)
                self._current_memory -= size_bytes
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds (None = no expiration)
        """
        with self._lock:
            # Calculate value size
            size_bytes = sys.getsizeof(value)

            # Calculate expiry time
            expiry_time = time.time() + ttl_seconds if ttl_seconds else None

            # Remove old entry if exists
            if key in self._cache:
                _, _, old_size = self._cache.pop(key)
                self._current_memory -= old_size

            # Add new entry
            self._cache[key] = (value, expiry_time, size_bytes)
            self._current_memory += size_bytes

            # Evict entries if memory limit exceeded
            self._evict_if_needed()

    def _evict_if_needed(self):
        """Evict least recently used entries until under memory limit."""
        while self._current_memory > self.max_memory_bytes and self._cache:
            # Remove least recently used (first item)
            key, (value, expiry_time, size_bytes) = self._cache.popitem(last=False)
            self._current_memory -= size_bytes
            print(f'[cache] Evicted key: {key[:50]}... (freed {size_bytes} bytes)')

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._current_memory = 0
            self._hits = 0
            self._misses = 0
            print('[cache] Cache cleared')

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache metrics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                'entries': len(self._cache),
                'memory_mb': round(self._current_memory / 1024 / 1024, 2),
                'max_memory_mb': self.max_memory_bytes / 1024 / 1024,
                'utilization_pct': round(self._current_memory / self.max_memory_bytes * 100, 1),
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate_pct': round(hit_rate, 1)
            }

    def remove_expired(self):
        """Remove all expired entries (useful for cleanup)."""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, (_, expiry_time, _) in self._cache.items()
                if expiry_time and current_time > expiry_time
            ]

            for key in expired_keys:
                _, _, size_bytes = self._cache.pop(key)
                self._current_memory -= size_bytes

            if expired_keys:
                print(f'[cache] Removed {len(expired_keys)} expired entries')


# Global cache instance (singleton)
_global_cache = None
_cache_lock = threading.Lock()


def _get_cache() -> LRUCacheManager:
    """Get or create global cache instance."""
    global _global_cache
    with _cache_lock:
        if _global_cache is None:
            _global_cache = LRUCacheManager(max_memory_mb=100)
            print('[cache] Initialized LRU cache manager (100MB limit)')
        return _global_cache


def get_cached(key: str, ttl_seconds: int, compute_fn: Callable[[], Any]) -> Any:
    """
    Get value from cache or compute if not found.

    Args:
        key: Cache key
        ttl_seconds: Time to live in seconds
        compute_fn: Function to call if cache miss (no arguments)

    Returns:
        Cached or computed value

    Example:
        def fetch_data():
            return expensive_api_call()

        data = get_cached('my_data', 300, fetch_data)
    """
    cache = _get_cache()

    # Try to get from cache
    value = cache.get(key)
    if value is not None:
        return value

    # Cache miss - compute value
    value = compute_fn()

    # Store in cache
    cache.set(key, value, ttl_seconds)

    return value


def cached(ttl_seconds: int):
    """
    Decorator for caching function results with TTL.

    Args:
        ttl_seconds: Time to live in seconds

    Example:
        @cached(ttl_seconds=3600)
        def expensive_function(team_id, season):
            # ... expensive computation ...
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            cache = _get_cache()
            value = cache.get(cache_key)

            if value is not None:
                return value

            # Cache miss - compute value
            value = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, value, ttl_seconds)

            return value

        return wrapper
    return decorator


def clear_cache():
    """Clear all cache entries."""
    cache = _get_cache()
    cache.clear()


def get_cache_stats() -> dict:
    """
    Get cache statistics.

    Returns:
        Dict with cache metrics
    """
    cache = _get_cache()
    return cache.get_stats()


def remove_expired_entries():
    """Remove all expired entries from cache."""
    cache = _get_cache()
    cache.remove_expired()
