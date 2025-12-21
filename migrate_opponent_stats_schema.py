"""
Opponent Statistics Schema Migration

This script adds comprehensive opponent statistics columns to:
1. team_game_logs (per-game opponent stats)
2. team_season_stats (season-average opponent stats allowed)

Run this BEFORE backfilling data.

Usage:
    python3 migrate_opponent_stats_schema.py
"""

import sqlite3
from api.utils.db_config import get_db_path

NBA_DATA_DB_PATH = get_db_path('nba_data.db')

def migrate_opponent_stats():
    """Add opponent statistics columns to database tables"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("OPPONENT STATISTICS SCHEMA MIGRATION")
    print("=" * 80)

    # ========================================================================
    # PART 1: team_game_logs - Add per-game opponent stats
    # ========================================================================
    print("\n[1/2] Adding opponent stats columns to team_game_logs...")

    # Check existing columns
    cursor.execute("PRAGMA table_info(team_game_logs)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    game_log_columns = {
        # Shooting stats
        'opp_fgm': 'INTEGER',
        'opp_fga': 'INTEGER',
        'opp_fg_pct': 'REAL',
        'opp_fg2m': 'INTEGER',
        'opp_fg2a': 'INTEGER',
        'opp_fg2_pct': 'REAL',
        'opp_fg3m': 'INTEGER',
        'opp_fg3a': 'INTEGER',
        'opp_fg3_pct': 'REAL',
        'opp_ftm': 'INTEGER',
        'opp_fta': 'INTEGER',
        'opp_ft_pct': 'REAL',

        # Rebounds
        'opp_offensive_rebounds': 'INTEGER',
        'opp_defensive_rebounds': 'INTEGER',
        'opp_rebounds': 'INTEGER',

        # Playmaking and defense
        'opp_assists': 'INTEGER',
        'opp_turnovers': 'INTEGER',
        'opp_steals': 'INTEGER',
        'opp_blocks': 'INTEGER',

        # Advanced stats
        'opp_pace': 'REAL',
        'opp_off_rating': 'REAL',
        'opp_def_rating': 'REAL',

        # Scoring breakdown
        'opp_points_off_turnovers': 'INTEGER',
        'opp_fast_break_points': 'INTEGER',
        'opp_points_in_paint': 'INTEGER',
        'opp_second_chance_points': 'INTEGER',

        # Possession stats
        'possessions': 'REAL',
        'opp_possessions': 'REAL',
    }

    added_count = 0
    for col_name, col_type in game_log_columns.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE team_game_logs ADD COLUMN {col_name} {col_type}")
                print(f"  ✓ Added: {col_name} ({col_type})")
                added_count += 1
            except Exception as e:
                print(f"  ✗ Error adding {col_name}: {e}")
        else:
            print(f"  ⊘ Already exists: {col_name}")

    print(f"\n  Added {added_count} new columns to team_game_logs")

    # ========================================================================
    # PART 2: team_season_stats - Add season-average opponent stats
    # ========================================================================
    print("\n[2/2] Adding opponent stats columns to team_season_stats...")

    cursor.execute("PRAGMA table_info(team_season_stats)")
    existing_season_columns = {row[1] for row in cursor.fetchall()}

    season_stat_columns = {
        # Shooting stats allowed
        'opp_fgm': 'REAL',
        'opp_fga': 'REAL',
        'opp_fg_pct': 'REAL',
        'opp_fg2m': 'REAL',
        'opp_fg2a': 'REAL',
        'opp_fg2_pct': 'REAL',
        # opp_fg3m, opp_fg3a, opp_fg3_pct already exist
        'opp_ftm': 'REAL',
        'opp_fta': 'REAL',
        'opp_ft_pct': 'REAL',

        # Rebounds allowed
        'opp_offensive_rebounds': 'REAL',
        'opp_defensive_rebounds': 'REAL',
        'opp_rebounds': 'REAL',

        # Playmaking allowed
        'opp_assists': 'REAL',
        # opp_tov already exists
        'opp_steals': 'REAL',
        'opp_blocks': 'REAL',

        # Advanced stats allowed
        'opp_pace': 'REAL',
        'opp_off_rating': 'REAL',
        'opp_def_rating': 'REAL',

        # Scoring breakdown allowed
        'opp_points_off_turnovers': 'REAL',
        'opp_fast_break_points': 'REAL',
        'opp_points_in_paint': 'REAL',
        'opp_second_chance_points': 'REAL',

        # Possessions
        'possessions': 'REAL',
        'opp_possessions': 'REAL',

        # Rankings for key opponent stats
        'opp_fg_pct_rank': 'INTEGER',
        'opp_ft_pct_rank': 'INTEGER',
        'opp_rebounds_rank': 'INTEGER',
        'opp_assists_rank': 'INTEGER',
        'opp_pace_rank': 'INTEGER',
        'opp_off_rating_rank': 'INTEGER',
        'opp_def_rating_rank': 'INTEGER',
    }

    added_season_count = 0
    for col_name, col_type in season_stat_columns.items():
        if col_name not in existing_season_columns:
            try:
                cursor.execute(f"ALTER TABLE team_season_stats ADD COLUMN {col_name} {col_type}")
                print(f"  ✓ Added: {col_name} ({col_type})")
                added_season_count += 1
            except Exception as e:
                print(f"  ✗ Error adding {col_name}: {e}")
        else:
            print(f"  ⊘ Already exists: {col_name}")

    print(f"\n  Added {added_season_count} new columns to team_season_stats")

    # ========================================================================
    # Commit changes
    # ========================================================================
    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print(f"✅ MIGRATION COMPLETE!")
    print(f"   team_game_logs: {added_count} columns added")
    print(f"   team_season_stats: {added_season_count} columns added")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Run: python3 compute_opponent_stats.py (to backfill all games)")
    print("  2. Run: python3 compute_season_opponent_stats.py (to aggregate season averages)")
    print("  3. Update: sync_nba_data.py (to compute opponent stats on future syncs)")
    print("=" * 80)


if __name__ == '__main__':
    migrate_opponent_stats()
