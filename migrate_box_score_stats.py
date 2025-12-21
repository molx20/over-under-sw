"""
Database migration to add box score statistics to team_game_logs table.

This adds columns for advanced box score stats that weren't in the original schema:
- fgm, fga (total field goals made/attempted)
- offensive_rebounds, defensive_rebounds (rebound breakdown)
- steals, blocks (defensive stats)
- points_off_turnovers, fast_break_points, points_in_paint, second_chance_points (scoring breakdown)

Data sources:
- fgm, fga, offensive_rebounds, defensive_rebounds, steals, blocks: BoxScoreTraditionalV3
- points_off_turnovers, fast_break_points, points_in_paint: Calculated from BoxScoreScoringV3 percentages
- second_chance_points: Estimated from offensive rebounds and team efficiency
"""

import sqlite3
import os

DB_PATH = 'api/data/nba_data.db'

def migrate():
    """Add box score columns to team_game_logs table."""

    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("=" * 70)
        print("TEAM_GAME_LOGS BOX SCORE MIGRATION")
        print("=" * 70)

        # Check current schema
        cursor.execute("PRAGMA table_info(team_game_logs)")
        existing_columns = {col[1] for col in cursor.fetchall()}

        columns_to_add = [
            ("fgm", "INTEGER", "Total field goals made"),
            ("fga", "INTEGER", "Total field goals attempted"),
            ("offensive_rebounds", "INTEGER", "Offensive rebounds"),
            ("defensive_rebounds", "INTEGER", "Defensive rebounds"),
            ("steals", "INTEGER", "Steals"),
            ("blocks", "INTEGER", "Blocks"),
            ("points_off_turnovers", "INTEGER", "Points off turnovers"),
            ("fast_break_points", "INTEGER", "Fast break points"),
            ("points_in_paint", "INTEGER", "Points in the paint"),
            ("second_chance_points", "INTEGER", "Second chance points"),
        ]

        added_count = 0
        skipped_count = 0

        for col_name, col_type, description in columns_to_add:
            if col_name in existing_columns:
                print(f"⏭️  Column '{col_name}' already exists, skipping")
                skipped_count += 1
            else:
                print(f"➕ Adding column '{col_name}' ({col_type}) - {description}")
                cursor.execute(f"ALTER TABLE team_game_logs ADD COLUMN {col_name} {col_type}")
                added_count += 1

        conn.commit()

        print("\n" + "=" * 70)
        print(f"✅ Migration complete!")
        print(f"   Columns added: {added_count}")
        print(f"   Columns skipped: {skipped_count}")
        print("=" * 70)

        # Show updated schema
        cursor.execute("PRAGMA table_info(team_game_logs)")
        all_columns = cursor.fetchall()

        print("\n📋 Updated schema:")
        print(f"   Total columns: {len(all_columns)}")
        new_columns = [col[1] for col in all_columns if col[1] in {c[0] for c in columns_to_add}]
        if new_columns:
            print(f"   New box score columns: {', '.join(new_columns)}")

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
