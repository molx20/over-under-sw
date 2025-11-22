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
from contextlib import contextmanager
from typing import Literal
from queue import Queue, Empty


class ConnectionPool:
    """Thread-safe connection pool for SQLite databases."""

    def __init__(self, db_path: str, pool_size: int = 5, timeout: float = 30.0):
        """
        Initialize connection pool.

        Args:
            db_path: Path to SQLite database file
            pool_size: Maximum number of connections to maintain
            timeout: Maximum time to wait for available connection (seconds)
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._created_connections = 0

        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Pre-create initial connections
        self._initialize_pool()

    def _initialize_pool(self):
        """Pre-create connections to fill the pool."""
        for _ in range(self.pool_size):
            conn = self._create_connection()
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
            timeout=30.0  # Wait up to 30s for database locks
        )
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries

        # Performance optimizations
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
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
        try:
            # Try to get connection from pool
            try:
                conn = self._pool.get(timeout=self.timeout)
            except Empty:
                # Pool exhausted - create temporary connection
                print(f"[connection_pool] WARNING: Pool exhausted, creating temporary connection")
                conn = self._create_connection()

            # Verify connection is healthy
            if not self._is_connection_healthy(conn):
                print(f"[connection_pool] Unhealthy connection detected, creating new one")
                conn.close()
                conn = self._create_connection()

            yield conn

        finally:
            if conn:
                # Try to return connection to pool
                try:
                    self._pool.put_nowait(conn)
                except:
                    # Pool is full (temporary connection), close it
                    conn.close()

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
            # Determine database path
            if db_name == 'predictions':
                db_path = os.path.join(
                    os.path.dirname(__file__), '..', 'data', 'predictions.db'
                )
            elif db_name == 'team_rankings':
                db_path = os.path.join(
                    os.path.dirname(__file__), '..', 'data', 'team_rankings.db'
                )
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
