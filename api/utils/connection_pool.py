"""
SQLite Connection Pool Manager

Provides connection pooling and reuse to eliminate:
- File handle exhaustion
- Repeated connection overhead
- Disk I/O on every query

Usage:
    from api.utils.connection_pool import get_db_pool

    pool = get_db_pool('predictions')
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM game_predictions")
        results = cursor.fetchall()
"""

import sqlite3
import os
import threading
import time
from contextlib import contextmanager
from typing import Literal, Callable, Any
from queue import Queue, Empty

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path


class ConnectionPool:
    """Thread-safe connection pool for SQLite databases."""

    def __init__(self, db_path: str, pool_size: int = 5, timeout: float = 30.0, max_idle_time: float = 3600.0):
        """
        Initialize connection pool.

        Args:
            db_path: Path to SQLite database file
            pool_size: Maximum number of connections to maintain
            timeout: Maximum time to wait for available connection (seconds)
            max_idle_time: Maximum time a connection can be idle before refresh (seconds, default 1 hour)
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self.max_idle_time = max_idle_time
        self._pool = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._created_connections = 0
        self._connection_timestamps = {}  # Track last use time for each connection

        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Pre-create initial connections
        self._initialize_pool()

    def _initialize_pool(self):
        """Pre-create connections to fill the pool."""
        for _ in range(self.pool_size):
            conn = self._create_connection()
            self._connection_timestamps[id(conn)] = time.time()
            self._pool.put(conn)

    def _create_connection(self) -> sqlite3.Connection:
        """
        Create a new SQLite connection with optimal settings.

        Returns:
            Configured SQLite connection
        """
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,  # Allow connection reuse across threads
            timeout=60.0  # Wait up to 60s for database locks (increased for idle scenarios)
        )
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries

        # Performance optimizations
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA busy_timeout=60000")  # 60s busy timeout in milliseconds
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety and speed
        conn.execute("PRAGMA cache_size=10000")  # 10MB cache per connection
        conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables

        self._created_connections += 1
        return conn

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool (context manager).

        Yields:
            SQLite connection that is automatically returned to pool

        Example:
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM games")
        """
        conn = None
        conn_id = None
        try:
            # Try to get connection from pool
            try:
                conn = self._pool.get(timeout=self.timeout)
                conn_id = id(conn)
            except Empty:
                # Pool exhausted - create temporary connection
                print(f"[connection_pool] WARNING: Pool exhausted, creating temporary connection")
                conn = self._create_connection()
                conn_id = id(conn)

            # Check if connection is too old (idle too long)
            if conn_id in self._connection_timestamps:
                idle_time = time.time() - self._connection_timestamps[conn_id]
                if idle_time > self.max_idle_time:
                    print(f"[connection_pool] Connection idle for {idle_time:.0f}s, refreshing")
                    conn.close()
                    conn = self._create_connection()
                    conn_id = id(conn)

            # Verify connection is healthy
            if not self._is_connection_healthy(conn):
                print(f"[connection_pool] Unhealthy connection detected, creating new one")
                try:
                    conn.close()
                except:
                    pass
                conn = self._create_connection()
                conn_id = id(conn)

            # Update last use timestamp
            self._connection_timestamps[conn_id] = time.time()

            yield conn

        finally:
            if conn:
                # Update timestamp before returning
                if conn_id:
                    self._connection_timestamps[conn_id] = time.time()

                # Try to return connection to pool
                try:
                    self._pool.put_nowait(conn)
                except:
                    # Pool is full (temporary connection), close it
                    if conn_id in self._connection_timestamps:
                        del self._connection_timestamps[conn_id]
                    try:
                        conn.close()
                    except:
                        pass

    def _is_connection_healthy(self, conn: sqlite3.Connection) -> bool:
        """
        Check if connection is still valid.

        Args:
            conn: Connection to check

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            conn.execute("SELECT 1")
            return True
        except:
            return False

    def close_all(self):
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break

    def get_stats(self) -> dict:
        """
        Get pool statistics.

        Returns:
            Dict with pool metrics
        """
        return {
            "pool_size": self.pool_size,
            "available_connections": self._pool.qsize(),
            "total_created": self._created_connections,
            "db_path": self.db_path
        }


# Global pool instances (singleton pattern)
_pools = {}
_pools_lock = threading.Lock()


def get_db_pool(db_name: Literal['predictions', 'team_rankings']) -> ConnectionPool:
    """
    Get or create a connection pool for the specified database.

    Args:
        db_name: Database name ('predictions' or 'team_rankings')

    Returns:
        ConnectionPool instance (singleton per database)

    Example:
        pool = get_db_pool('predictions')
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM game_predictions LIMIT 10")
            results = cursor.fetchall()
    """
    with _pools_lock:
        if db_name not in _pools:
            # Determine database path using centralized configuration
            if db_name == 'predictions':
                db_path = get_db_path('predictions.db')
            elif db_name == 'team_rankings':
                db_path = get_db_path('team_rankings.db')
            else:
                raise ValueError(f"Unknown database: {db_name}")

            # Create pool
            _pools[db_name] = ConnectionPool(db_path, pool_size=5)
            print(f"[connection_pool] Created pool for {db_name} at {db_path}")

        return _pools[db_name]


def close_all_pools():
    """Close all connection pools (call on app shutdown)."""
    with _pools_lock:
        for name, pool in _pools.items():
            print(f"[connection_pool] Closing pool for {name}")
            pool.close_all()
        _pools.clear()


def retry_on_db_lock(max_retries: int = 5, initial_delay: float = 0.1, backoff_factor: float = 2.0):
    """
    Decorator to retry database operations on lock errors.

    Handles:
    - sqlite3.OperationalError: database is locked
    - Stale connections
    - Transient lock errors

    Args:
        max_retries: Maximum number of retry attempts (default 5)
        initial_delay: Initial delay between retries in seconds (default 0.1s)
        backoff_factor: Multiplier for delay on each retry (default 2.0 = exponential backoff)

    Example:
        @retry_on_db_lock(max_retries=3)
        def save_data():
            with get_connection() as conn:
                conn.execute("INSERT INTO games ...")
                conn.commit()

    Retry schedule with defaults:
        Attempt 1: immediate
        Attempt 2: wait 0.1s
        Attempt 3: wait 0.2s
        Attempt 4: wait 0.4s
        Attempt 5: wait 0.8s
        Total max time: ~1.5s
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    error_msg = str(e).lower()
                    if 'locked' in error_msg or 'busy' in error_msg:
                        last_exception = e
                        if attempt < max_retries - 1:
                            print(f"[retry_on_db_lock] Database locked, retry {attempt + 1}/{max_retries} after {delay:.2f}s")
                            time.sleep(delay)
                            delay *= backoff_factor
                        else:
                            print(f"[retry_on_db_lock] Database locked, max retries ({max_retries}) exceeded")
                    else:
                        # Not a lock error, re-raise immediately
                        raise
                except Exception as e:
                    # Other exceptions, re-raise immediately
                    raise

            # Max retries exceeded, raise the last lock exception
            raise last_exception

        return wrapper
    return decorator
