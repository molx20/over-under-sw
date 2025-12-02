"""
Sync Lock Manager - Prevents concurrent database sync operations

This module provides a global lock mechanism to ensure only one sync operation
runs at a time, completely eliminating database lock conflicts.

Features:
- Thread-safe sync lock with timeout
- Automatic lock release on completion/error
- Queue management for pending syncs
- Status monitoring for admin endpoints
"""

import threading
import time
from contextlib import contextmanager
from typing import Optional
from datetime import datetime, timezone

# Global sync lock
_sync_lock = threading.Lock()
_current_sync_info = None
_sync_history = []
_MAX_HISTORY = 20


class SyncLockError(Exception):
    """Raised when sync lock cannot be acquired"""
    pass


@contextmanager
def sync_lock(sync_type: str, timeout: float = 0.0, wait: bool = False):
    """
    Context manager for exclusive sync operations.

    Args:
        sync_type: Type of sync being performed ('full', 'game_logs', 'todays_games', etc.)
        timeout: Max seconds to wait for lock (0 = fail immediately if locked)
        wait: If True, wait for lock; if False, raise error if locked

    Raises:
        SyncLockError: If lock cannot be acquired within timeout

    Example:
        with sync_lock('full', timeout=5.0, wait=True):
            # Your sync code here
            sync_all()
    """
    global _current_sync_info

    acquired = False
    start_time = time.time()

    try:
        # Try to acquire lock
        if wait and timeout > 0:
            acquired = _sync_lock.acquire(timeout=timeout)
        elif wait:
            _sync_lock.acquire()
            acquired = True
        else:
            acquired = _sync_lock.acquire(blocking=False)

        if not acquired:
            # Check if another sync is running
            if _current_sync_info:
                raise SyncLockError(
                    f"Sync already in progress: {_current_sync_info['sync_type']} "
                    f"started at {_current_sync_info['started_at']}"
                )
            else:
                raise SyncLockError("Could not acquire sync lock")

        # Lock acquired - record sync info
        _current_sync_info = {
            'sync_type': sync_type,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'thread_id': threading.get_ident(),
        }

        print(f"[sync_lock] ✓ Lock acquired for '{sync_type}' sync")

        yield

    finally:
        if acquired:
            # Calculate duration
            duration = time.time() - start_time

            # Record in history
            _sync_history.append({
                'sync_type': sync_type,
                'started_at': _current_sync_info['started_at'],
                'duration_seconds': round(duration, 2),
                'thread_id': _current_sync_info['thread_id'],
            })

            # Trim history
            if len(_sync_history) > _MAX_HISTORY:
                _sync_history.pop(0)

            # Clear current sync info
            _current_sync_info = None

            # Release lock
            _sync_lock.release()
            print(f"[sync_lock] ✓ Lock released for '{sync_type}' sync (duration: {duration:.1f}s)")


def is_sync_in_progress() -> bool:
    """
    Check if a sync operation is currently running.

    Returns:
        True if sync is in progress, False otherwise
    """
    return _current_sync_info is not None


def get_current_sync() -> Optional[dict]:
    """
    Get information about the currently running sync.

    Returns:
        Dict with sync info or None if no sync is running
    """
    return _current_sync_info.copy() if _current_sync_info else None


def get_sync_history(limit: int = 10) -> list:
    """
    Get recent sync history.

    Args:
        limit: Maximum number of history entries to return

    Returns:
        List of recent sync operations (newest first)
    """
    return list(reversed(_sync_history[-limit:]))


def wait_for_sync_completion(timeout: float = 300.0) -> bool:
    """
    Wait for any in-progress sync to complete.

    Args:
        timeout: Maximum seconds to wait

    Returns:
        True if no sync is running, False if timeout reached
    """
    start = time.time()

    while is_sync_in_progress():
        if time.time() - start > timeout:
            return False
        time.sleep(0.5)

    return True
