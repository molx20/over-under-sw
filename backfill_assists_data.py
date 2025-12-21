#!/usr/bin/env python3
"""
Backfill Assists Data - Populates opp_assists and opp_assists_rank

Run this on Railway after deployment to populate assists data:
  python backfill_assists_data.py
"""
import sqlite3
from api.utils.db_config import get_db_path
from api.utils.season_opponent_stats_aggregator import update_team_season_opponent_stats

def backfill_assists():
    """Backfill opp_assists and opp_assists_rank for all teams"""
    db_path = get_db_path('nba_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    season = '2025-26'

    print("=" * 80)
    print("BACKFILLING ASSISTS DATA")
    print("=" * 80)

    # Step 1: Update opponent stats (populates opp_assists from game logs)
    print("\n[1/2] Aggregating opponent assists from game logs...")
    cursor.execute('''
        SELECT DISTINCT team_id
        FROM team_season_stats
        WHERE season = ?
        ORDER BY team_id
    ''', (season,))

    teams = [row['team_id'] for row in cursor.fetchall()]
    print(f"Found {len(teams)} teams to update")

    for idx, team_id in enumerate(teams, 1):
        try:
            # Update all three split types
            update_team_season_opponent_stats(team_id, season, 'overall')
            update_team_season_opponent_stats(team_id, season, 'home')
            update_team_season_opponent_stats(team_id, season, 'away')
            if idx % 10 == 0:
                print(f"  Progress: {idx}/{len(teams)} teams updated...")
        except Exception as e:
            print(f"  ERROR updating team {team_id}: {e}")

    conn.close()
    print(f"✓ Aggregated opponent stats for {len(teams)} teams")

    # Step 2: Rank teams by opp_assists
    print("\n[2/2] Computing opp_assists rankings...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT team_id, opp_assists
        FROM team_season_stats
        WHERE season = ? AND split_type = 'overall' AND opp_assists IS NOT NULL
        ORDER BY opp_assists ASC
    ''', (season,))

    ranked_teams = cursor.fetchall()
    print(f"Ranking {len(ranked_teams)} teams by opponent assists allowed...")

    for rank, team in enumerate(ranked_teams, start=1):
        cursor.execute('''
            UPDATE team_season_stats
            SET opp_assists_rank = ?
            WHERE team_id = ? AND season = ? AND split_type = 'overall'
        ''', (rank, team['team_id'], season))

    conn.commit()
    print(f"✓ Ranked {len(ranked_teams)} teams")

    # Step 3: Verify
    print("\n[VERIFICATION] Top 5 ball-movement defenses:")
    cursor.execute('''
        SELECT team_id, opp_assists, opp_assists_rank
        FROM team_season_stats
        WHERE season = ? AND split_type = 'overall' AND opp_assists_rank IS NOT NULL
        ORDER BY opp_assists_rank ASC
        LIMIT 5
    ''', (season,))

    for row in cursor.fetchall():
        print(f"  Rank #{row['opp_assists_rank']}: Team {row['team_id']} - {row['opp_assists']:.1f} AST allowed/game")

    conn.close()

    print("\n" + "=" * 80)
    print("✅ ASSISTS DATA BACKFILL COMPLETE!")
    print("=" * 80)

if __name__ == '__main__':
    backfill_assists()
