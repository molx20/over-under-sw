"""
Migration script to populate rest_days and is_back_to_back columns
in team_game_logs table for existing data.

Run this once after adding the new columns to the schema.
"""
import sqlite3
from datetime import datetime

DB_PATH = 'api/data/nba_data.db'

def calculate_rest_days(current_date, previous_date):
    """Calculate days between two dates."""
    if not previous_date:
        return None

    curr = datetime.fromisoformat(current_date.replace('Z', '+00:00'))
    prev = datetime.fromisoformat(previous_date.replace('Z', '+00:00'))
    delta = (curr.date() - prev.date()).days
    return delta

def migrate_rest_days():
    """Populate rest_days and is_back_to_back for all existing game logs."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Starting migration: Adding rest_days and is_back_to_back to team_game_logs")

    # Get all teams
    cursor.execute("SELECT DISTINCT team_id FROM team_game_logs ORDER BY team_id")
    teams = [row[0] for row in cursor.fetchall()]

    total_updates = 0

    for team_id in teams:
        # Get all games for this team, sorted by date
        cursor.execute("""
            SELECT game_id, game_date
            FROM team_game_logs
            WHERE team_id = ?
            ORDER BY game_date ASC
        """, (team_id,))

        games = cursor.fetchall()

        if not games:
            continue

        # First game of season - no previous game
        game_id, game_date = games[0]
        cursor.execute("""
            UPDATE team_game_logs
            SET rest_days = NULL, is_back_to_back = 0
            WHERE game_id = ? AND team_id = ?
        """, (game_id, team_id))
        total_updates += 1

        # Process remaining games
        for i in range(1, len(games)):
            current_game_id, current_date = games[i]
            previous_date = games[i-1][1]

            rest_days = calculate_rest_days(current_date, previous_date)
            is_b2b = 1 if rest_days == 1 else 0

            cursor.execute("""
                UPDATE team_game_logs
                SET rest_days = ?, is_back_to_back = ?
                WHERE game_id = ? AND team_id = ?
            """, (rest_days, is_b2b, current_game_id, team_id))
            total_updates += 1

    conn.commit()

    # Verify results
    cursor.execute("SELECT COUNT(*) FROM team_game_logs WHERE is_back_to_back = 1")
    b2b_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM team_game_logs")
    total_games = cursor.fetchone()[0]

    print(f"✓ Migration complete!")
    print(f"  Total game logs updated: {total_updates}")
    print(f"  Back-to-back games found: {b2b_count}")
    print(f"  Total games in database: {total_games}")
    print(f"  B2B percentage: {(b2b_count / total_games * 100):.1f}%")

    conn.close()

if __name__ == '__main__':
    migrate_rest_days()
