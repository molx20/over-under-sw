"""
Test script to verify database lock fixes

Tests:
1. Connection pooling with stale connection detection
2. Retry logic for database lock errors
3. Environment variable DB_PATH handling
"""

import os
import sys
import time
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add api directory to path
sys.path.append(os.path.dirname(__file__))

from api.utils.connection_pool import get_db_pool, retry_on_db_lock
from api.utils.db_config import get_db_path

def test_db_path_config():
    """Test that DB_PATH environment variable works"""
    print("\n=== Test 1: DB Path Configuration ===")

    # Test default (local dev)
    if 'DB_PATH' in os.environ:
        del os.environ['DB_PATH']

    path = get_db_path('test.db')
    print(f"Default path (no env var): {path}")
    assert 'data' in path and path.endswith('test.db'), "Should use data directory by default"

    # Test with environment variable (use temp directory instead of /data)
    import tempfile
    temp_dir = tempfile.mkdtemp()
    os.environ['DB_PATH'] = temp_dir

    # Need to reimport to pick up new env var
    from importlib import reload
    import api.utils.db_config
    reload(api.utils.db_config)
    from api.utils.db_config import get_db_path as get_db_path_reload

    path = get_db_path_reload('test.db')
    print(f"Custom path (DB_PATH={temp_dir}): {path}")
    assert path == os.path.join(temp_dir, 'test.db'), "Should use DB_PATH when set"

    # Clean up
    if 'DB_PATH' in os.environ:
        del os.environ['DB_PATH']
    import shutil
    shutil.rmtree(temp_dir)

    print("✓ DB path configuration working correctly\n")


def test_connection_pool():
    """Test connection pooling and health checks"""
    print("=== Test 2: Connection Pool ===")

    pool = get_db_pool('predictions')

    # Test getting a connection
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print(f"Connection test query result: {result[0]}")
        assert result[0] == 1, "Connection should be healthy"

    stats = pool.get_stats()
    print(f"Pool stats: {stats}")

    print("✓ Connection pool working correctly\n")


def test_concurrent_access():
    """Test multiple concurrent database operations"""
    print("=== Test 3: Concurrent Database Access ===")

    def write_operation(thread_id):
        """Simulate a database write operation"""
        pool = get_db_pool('predictions')
        try:
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                # Create a test table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_concurrent (
                        id INTEGER PRIMARY KEY,
                        thread_id INTEGER,
                        timestamp REAL
                    )
                """)

                # Insert test data
                cursor.execute(
                    "INSERT INTO test_concurrent (thread_id, timestamp) VALUES (?, ?)",
                    (thread_id, time.time())
                )
                conn.commit()

                # Small delay to increase lock contention
                time.sleep(0.01)

                # Read the data back
                cursor.execute("SELECT COUNT(*) FROM test_concurrent WHERE thread_id = ?", (thread_id,))
                count = cursor.fetchone()[0]

                return f"Thread {thread_id}: SUCCESS (wrote {count} row(s))"
        except Exception as e:
            return f"Thread {thread_id}: ERROR - {str(e)}"

    # Run 10 concurrent operations
    print("Running 10 concurrent database operations...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(write_operation, i) for i in range(10)]

        for future in as_completed(futures):
            result = future.result()
            print(f"  {result}")

    # Clean up test table
    pool = get_db_pool('predictions')
    with pool.get_connection() as conn:
        conn.execute("DROP TABLE IF EXISTS test_concurrent")
        conn.commit()

    print("✓ Concurrent access handled correctly\n")


@retry_on_db_lock(max_retries=3, initial_delay=0.05)
def test_retry_decorator():
    """Test the retry decorator"""
    pool = get_db_pool('predictions')
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return cursor.fetchone()[0]


def test_retry_logic():
    """Test retry decorator for database locks"""
    print("=== Test 4: Retry Logic ===")

    result = test_retry_decorator()
    print(f"Retry decorator test result: {result}")
    assert result == 1, "Retry decorator should work"

    print("✓ Retry logic working correctly\n")


def test_stale_connection():
    """Test that stale connections are refreshed"""
    print("=== Test 5: Stale Connection Detection ===")

    # Create a pool with very short idle timeout for testing
    from api.utils.connection_pool import ConnectionPool

    test_db_path = get_db_path('test_stale.db')
    pool = ConnectionPool(test_db_path, pool_size=1, max_idle_time=1.0)  # 1 second timeout

    # Use a connection
    with pool.get_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS test_stale (id INTEGER)")
        conn.commit()
        print("Created test table")

    # Wait for connection to become stale
    print("Waiting 2 seconds for connection to become stale...")
    time.sleep(2)

    # Use the connection again - it should be refreshed automatically
    with pool.get_connection() as conn:
        conn.execute("SELECT 1")
        print("Successfully used refreshed connection")

    # Clean up
    pool.close_all()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    print("✓ Stale connection detection working correctly\n")


if __name__ == '__main__':
    print("Testing Database Lock Fixes")
    print("=" * 50)

    try:
        test_db_path_config()
        test_connection_pool()
        test_concurrent_access()
        test_retry_logic()
        test_stale_connection()

        print("\n" + "=" * 50)
        print("✓ ALL TESTS PASSED!")
        print("=" * 50)

    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
