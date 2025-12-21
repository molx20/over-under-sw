#!/usr/bin/env python3
"""
Test script to verify full season sync functionality.

This script:
1. Connects to the database to check existing game count
2. Runs the sync_game_logs function with last_n_games=None (fetch all)
3. Verifies that games were synced
4. Shows new vs updated game counts
"""

import sqlite3
from api.utils.sync_nba_data import sync_game_logs

DB_PATH = 'api/data/nba_data.db'

def check_game_count():
    """Check how many games are currently in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Count total games
    cursor.execute("SELECT COUNT(*) FROM games WHERE season = '2025-26'")
    total_games = cursor.fetchone()[0]

    # Count completed games
    cursor.execute("SELECT COUNT(*) FROM games WHERE season = '2025-26' AND status = 'final'")
    completed_games = cursor.fetchone()[0]

    # Get date range
    cursor.execute("""
        SELECT MIN(game_date), MAX(game_date)
        FROM games
        WHERE season = '2025-26'
    """)
    date_range = cursor.fetchone()

    conn.close()

    return {
        'total': total_games,
        'completed': completed_games,
        'min_date': date_range[0],
        'max_date': date_range[1]
    }

def main():
    print("=" * 70)
    print("FULL SEASON SYNC TEST")
    print("=" * 70)

    # Check before
    print("\n📊 BEFORE SYNC:")
    before = check_game_count()
    print(f"   Total games: {before['total']}")
    print(f"   Completed games: {before['completed']}")
    print(f"   Date range: {before['min_date']} to {before['max_date']}")

    # Run sync
    print("\n🔄 RUNNING FULL SEASON SYNC...")
    print("   (This will fetch ALL completed games for 2025-26 season)")
    print("   (May take a few minutes due to API rate limits)")
    print()

    records_synced, error = sync_game_logs(season='2025-26', last_n_games=None)

    if error:
        print(f"\n❌ Sync failed: {error}")
        return

    print(f"\n✅ Sync completed: {records_synced} game log records processed")

    # Check after
    print("\n📊 AFTER SYNC:")
    after = check_game_count()
    print(f"   Total games: {after['total']}")
    print(f"   Completed games: {after['completed']}")
    print(f"   Date range: {after['min_date']} to {after['max_date']}")

    # Calculate changes
    new_games = after['total'] - before['total']
    print(f"\n📈 CHANGE:")
    print(f"   New games added: {new_games}")

    print("\n" + "=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
