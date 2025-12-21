#!/usr/bin/env python3
"""
Migration script to rename total_points to actual_total_points and backfill game data.

STRATEGY:
- The 'games' table already has a 'total_points' column (home_score + away_score)
- Rename it to 'actual_total_points' for clarity (actual game result vs predicted total)
- Backfill the 'games' table from 'team_game_logs' (318 unique games)
- This makes actual totals easily accessible for model evaluation

WHY THIS APPROACH:
- Cleaner than creating a separate table (avoids joins)
- The 'games' table is the natural home for game-level results
- Column already exists with correct data type (INTEGER)
- Just needs to be populated and renamed for clarity
"""

import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = 'api/data/nba_data.db'

def migrate():
    """Rename total_points to actual_total_points and backfill game data."""

    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        print("=" * 70)
        print("ACTUAL TOTAL POINTS MIGRATION")
        print("=" * 70)

        # Step 1: Check if column needs to be renamed
        cursor.execute("PRAGMA table_info(games)")
        columns = {col[1]: col for col in cursor.fetchall()}

        has_total_points = 'total_points' in columns
        has_actual_total_points = 'actual_total_points' in columns

        if has_actual_total_points:
            print("\n✓ Column 'actual_total_points' already exists, skipping rename")
        elif has_total_points:
            print("\n➕ Renaming 'total_points' to 'actual_total_points'...")
            cursor.execute("ALTER TABLE games RENAME COLUMN total_points TO actual_total_points")
            conn.commit()
            print("   ✓ Column renamed")
        else:
            print("\n➕ Adding 'actual_total_points' column...")
            cursor.execute("ALTER TABLE games ADD COLUMN actual_total_points INTEGER")
            conn.commit()
            print("   ✓ Column added")

        # Step 2: Count existing games
        cursor.execute("SELECT COUNT(*) FROM games WHERE season = '2025-26'")
        existing_games = cursor.fetchone()[0]
        print(f"\n📊 Current state:")
        print(f"   Games in 'games' table: {existing_games}")

        # Step 3: Count unique games in team_game_logs
        cursor.execute("""
            SELECT COUNT(DISTINCT game_id)
            FROM team_game_logs
            WHERE season = '2025-26'
        """)
        unique_games_in_logs = cursor.fetchone()[0]
        print(f"   Unique games in 'team_game_logs': {unique_games_in_logs}")

        # Step 4: Backfill games table from team_game_logs
        print(f"\n🔄 Backfilling {unique_games_in_logs} games into 'games' table...")

        # Get all unique games with both home and away team data
        cursor.execute("""
            SELECT
                game_id,
                season,
                game_date,
                MAX(CASE WHEN is_home = 1 THEN team_id END) as home_team_id,
                MAX(CASE WHEN is_home = 0 THEN team_id END) as away_team_id,
                MAX(CASE WHEN is_home = 1 THEN team_pts END) as home_score,
                MAX(CASE WHEN is_home = 0 THEN team_pts END) as away_score,
                MAX(pace) as game_pace
            FROM team_game_logs
            WHERE season = '2025-26'
            GROUP BY game_id
            HAVING home_team_id IS NOT NULL AND away_team_id IS NOT NULL
        """)

        games_to_insert = cursor.fetchall()

        synced_at = datetime.now(timezone.utc).isoformat()
        new_games = 0
        updated_games = 0

        for game in games_to_insert:
            game_id = game['game_id']
            actual_total = int(game['home_score'] + game['away_score'])

            # Check if game exists
            cursor.execute("SELECT id FROM games WHERE id = ?", (game_id,))
            exists = cursor.fetchone() is not None

            # Upsert game with actual_total_points
            cursor.execute("""
                INSERT OR REPLACE INTO games (
                    id, season, game_date,
                    home_team_id, away_team_id,
                    home_score, away_score,
                    actual_total_points,
                    game_pace,
                    status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game_id,
                game['season'],
                game['game_date'],
                int(game['home_team_id']),
                int(game['away_team_id']),
                int(game['home_score']),
                int(game['away_score']),
                actual_total,
                float(game['game_pace']) if game['game_pace'] else None,
                'final',
                synced_at,
                synced_at
            ))

            if exists:
                updated_games += 1
            else:
                new_games += 1

        conn.commit()

        print(f"   ✓ Backfill complete:")
        print(f"     - {new_games} new games inserted")
        print(f"     - {updated_games} existing games updated")

        # Step 5: Verify results
        cursor.execute("""
            SELECT COUNT(*)
            FROM games
            WHERE season = '2025-26' AND actual_total_points IS NOT NULL
        """)
        games_with_totals = cursor.fetchone()[0]

        print(f"\n📊 Final state:")
        print(f"   Games with actual_total_points: {games_with_totals}")

        # Show sample data
        cursor.execute("""
            SELECT id, game_date, home_score, away_score, actual_total_points
            FROM games
            WHERE season = '2025-26' AND actual_total_points IS NOT NULL
            ORDER BY game_date DESC
            LIMIT 5
        """)
        samples = cursor.fetchall()

        print(f"\n📋 Sample games:")
        print(f"   {'Game ID':<15} {'Date':<12} {'Score':<10} {'Actual Total'}")
        print(f"   {'-' * 60}")
        for s in samples:
            print(f"   {s['id']:<15} {s['game_date'][:10]:<12} {s['home_score']}-{s['away_score']:<8} {s['actual_total_points']}")

        print("\n" + "=" * 70)
        print("✅ MIGRATION COMPLETE")
        print("=" * 70)
        print("\nNotes:")
        print("  - 'actual_total_points' = home_score + away_score")
        print("  - Used for model evaluation (predicted vs actual)")
        print("  - Safe to re-run (idempotent)")

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
