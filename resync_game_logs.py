#!/usr/bin/env python3
"""
Re-sync game logs with corrected pace calculation.
This script re-syncs the last 10 games for all teams to populate game pace values.
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(__file__))

from api.utils.sync_nba_data import sync_game_logs

if __name__ == '__main__':
    print("=" * 60)
    print("Re-syncing Game Logs with Corrected Pace Calculation")
    print("=" * 60)
    print()
    print("This will:")
    print("  1. Fetch last 10 games for all NBA teams")
    print("  2. Calculate game pace using both teams' possessions")
    print("  3. Update database with correct pace values")
    print()

    season = '2025-26'

    print(f"Starting sync for season {season}...")
    print()

    count, error = sync_game_logs(season=season, team_ids=None, last_n_games=10)

    print()
    print("=" * 60)
    if error:
        print(f"ERROR: {error}")
        sys.exit(1)
    else:
        print(f"SUCCESS: {count} game logs synced with corrected pace values")
        print()
        print("Next steps:")
        print("  - Run validation query to check pace values")
        print("  - Compare Utah Jazz pace with NBA.com")
    print("=" * 60)
