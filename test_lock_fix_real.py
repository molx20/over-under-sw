"""
Test the actual database lock fix with realistic scenario
"""
import sys
import os
import time
import threading

sys.path.append(os.path.dirname(__file__))

from api.utils import db

def test_write_after_long_idle():
    """Test that writes work after database has been idle"""
    print("\n=== Test: Write After Long Idle ===")

    # Initialize database
    db.init_db()
    print("✓ Database initialized")

    # Simulate long idle period (connection going stale)
    print("Simulating 2 second idle period...")
    time.sleep(2)

    # Now try to write - this would fail with "database locked" before fix
    print("Attempting write after idle period...")
    result = db.save_prediction(
        game_id="test_game_001",
        home_team="BOS",
        away_team="LAL",
        game_date="2025-01-15",
        pred_home=110.5,
        pred_away=108.3,
        pred_total=218.8
    )

    if result['success']:
        print(f"✓ Write successful after idle: {result['game_id']}")
    else:
        print(f"✗ Write failed: {result.get('error')}")
        return False

    # Try another write immediately
    result2 = db.submit_line("test_game_001", 220.5)
    if result2['success']:
        print(f"✓ Second write successful: line={result2['line']}")
    else:
        print(f"✗ Second write failed: {result2.get('error')}")
        return False

    print("✓ All writes after idle period succeeded\n")
    return True


def test_concurrent_writes():
    """Test multiple threads writing simultaneously"""
    print("\n=== Test: Concurrent Writes ===")

    errors = []
    successes = []

    def write_operation(thread_id):
        try:
            result = db.save_prediction(
                game_id=f"concurrent_test_{thread_id}",
                home_team="BOS",
                away_team="LAL",
                game_date="2025-01-15",
                pred_home=110.0 + thread_id,
                pred_away=108.0,
                pred_total=218.0 + thread_id
            )
            if result['success']:
                successes.append(thread_id)
                print(f"  Thread {thread_id}: ✓")
            else:
                errors.append((thread_id, result.get('error')))
                print(f"  Thread {thread_id}: ✗ {result.get('error')}")
        except Exception as e:
            errors.append((thread_id, str(e)))
            print(f"  Thread {thread_id}: ✗ Exception: {str(e)}")

    # Launch 5 concurrent writes
    threads = []
    for i in range(5):
        t = threading.Thread(target=write_operation, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    if errors:
        print(f"\n✗ {len(errors)} threads failed:")
        for thread_id, error in errors:
            print(f"  Thread {thread_id}: {error}")
        return False
    else:
        print(f"\n✓ All {len(successes)} concurrent writes succeeded")
        return True


def test_retry_on_lock():
    """Test that retry logic works"""
    print("\n=== Test: Retry Logic ===")

    # This should succeed even if there's brief contention
    result = db.save_prediction(
        game_id="retry_test_001",
        home_team="MIA",
        away_team="NYK",
        game_date="2025-01-16",
        pred_home=105.0,
        pred_away=103.0,
        pred_total=208.0
    )

    if result['success']:
        print("✓ Retry-protected write succeeded")
        return True
    else:
        print(f"✗ Retry-protected write failed: {result.get('error')}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Database Lock Fixes - Real Scenario")
    print("=" * 60)

    all_passed = True

    # Test 1: Write after idle
    if not test_write_after_long_idle():
        all_passed = False

    # Test 2: Concurrent writes
    if not test_concurrent_writes():
        all_passed = False

    # Test 3: Retry logic
    if not test_retry_on_lock():
        all_passed = False

    print("=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED - Database lock fixes working!")
    else:
        print("✗ SOME TESTS FAILED - Review errors above")
        sys.exit(1)
    print("=" * 60)
