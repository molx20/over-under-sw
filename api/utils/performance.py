"""
Performance Logging & Monitoring

Provides timing decorators and middleware for tracking slow operations.
Logs endpoint response times and highlights bottlenecks.

Usage:
    from api.utils.performance import timed, log_slow_operation

    # Decorator for functions
    @timed(name="my_function")
    def expensive_function():
        # ... computation ...
        pass

    # Context manager for code blocks
    with log_slow_operation("Fetching team stats", threshold_ms=500):
        # ... operation ...
        pass
"""

import time
import functools
from contextlib import contextmanager
from typing import Optional, Callable


# Configuration
DEFAULT_SLOW_THRESHOLD_MS = 500  # Log operations slower than 500ms


def timed(name: Optional[str] = None, threshold_ms: int = DEFAULT_SLOW_THRESHOLD_MS):
    """
    Decorator to measure and log function execution time.

    Only logs if execution time exceeds threshold.

    Args:
        name: Operation name (defaults to function name)
        threshold_ms: Log threshold in milliseconds (default 500ms)

    Example:
        @timed(name="Fetch team stats", threshold_ms=1000)
        def get_team_stats(team_id):
            # ... expensive operation ...
            return data
    """
    def decorator(func: Callable) -> Callable:
        operation_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.time() - start_time) * 1000
                if elapsed_ms >= threshold_ms:
                    print(f'[performance] SLOW: {operation_name} took {elapsed_ms:.0f}ms')
                else:
                    print(f'[performance] {operation_name} took {elapsed_ms:.0f}ms')

        return wrapper
    return decorator


@contextmanager
def log_slow_operation(operation_name: str, threshold_ms: int = DEFAULT_SLOW_THRESHOLD_MS):
    """
    Context manager to time a block of code.

    Only logs if execution time exceeds threshold.

    Args:
        operation_name: Name of the operation being timed
        threshold_ms: Log threshold in milliseconds (default 500ms)

    Example:
        with log_slow_operation("Database query", threshold_ms=100):
            cursor.execute("SELECT * FROM large_table")
            results = cursor.fetchall()
    """
    start_time = time.time()
    try:
        yield
    finally:
        elapsed_ms = (time.time() - start_time) * 1000
        if elapsed_ms >= threshold_ms:
            print(f'[performance] SLOW: {operation_name} took {elapsed_ms:.0f}ms')
        else:
            print(f'[performance] {operation_name} took {elapsed_ms:.0f}ms')


def create_timing_middleware(app):
    """
    Create Flask middleware to log endpoint response times.

    Args:
        app: Flask application instance

    Example:
        from flask import Flask
        from api.utils.performance import create_timing_middleware

        app = Flask(__name__)
        create_timing_middleware(app)
    """
    @app.before_request
    def before_request():
        from flask import g
        g.start_time = time.time()

    @app.after_request
    def after_request(response):
        from flask import g, request
        if hasattr(g, 'start_time'):
            elapsed_ms = (time.time() - g.start_time) * 1000
            endpoint = request.endpoint or request.path

            # Log slow endpoints
            if elapsed_ms >= DEFAULT_SLOW_THRESHOLD_MS:
                print(f'[performance] SLOW ENDPOINT: {request.method} {endpoint} took {elapsed_ms:.0f}ms')
            else:
                print(f'[performance] {request.method} {endpoint} took {elapsed_ms:.0f}ms')

        return response

    print('[performance] Timing middleware enabled')


class PerformanceTracker:
    """
    Track performance metrics over time.

    Useful for accumulating stats across multiple operations.
    """

    def __init__(self):
        self.operations = []

    def record(self, operation_name: str, duration_ms: float):
        """Record an operation's execution time."""
        self.operations.append({
            'name': operation_name,
            'duration_ms': duration_ms,
            'timestamp': time.time()
        })

    def get_stats(self) -> dict:
        """
        Get performance statistics.

        Returns:
            Dict with min/max/avg durations
        """
        if not self.operations:
            return {
                'total_operations': 0,
                'min_ms': 0,
                'max_ms': 0,
                'avg_ms': 0
            }

        durations = [op['duration_ms'] for op in self.operations]

        return {
            'total_operations': len(self.operations),
            'min_ms': round(min(durations), 1),
            'max_ms': round(max(durations), 1),
            'avg_ms': round(sum(durations) / len(durations), 1)
        }

    def get_slow_operations(self, threshold_ms: int = DEFAULT_SLOW_THRESHOLD_MS) -> list:
        """
        Get list of operations that exceeded threshold.

        Args:
            threshold_ms: Threshold in milliseconds

        Returns:
            List of slow operations sorted by duration (slowest first)
        """
        slow_ops = [op for op in self.operations if op['duration_ms'] >= threshold_ms]
        return sorted(slow_ops, key=lambda x: x['duration_ms'], reverse=True)

    def clear(self):
        """Clear all recorded operations."""
        self.operations.clear()


# Global tracker instance
_global_tracker = PerformanceTracker()


def get_performance_tracker() -> PerformanceTracker:
    """Get the global performance tracker instance."""
    return _global_tracker
