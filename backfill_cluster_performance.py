"""
Backfill Cluster Performance Data

Processes all completed games in chronological order to build up
team_vs_cluster_performance statistics using running averages.

Usage:
    python3 backfill_cluster_performance.py [--season SEASON]
"""

import argparse
import os
import sqlite3
from datetime import datetime

from api.utils.team_similarity import (
    update_cluster_performance_after_game,
    get_team_cluster_assignment
)


def get_nba_db_connection():
    """Connect to NBA data database"""
    db_path = os.path.join(os.path.dirname(__file__), 'api/data/nba_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def backfill_performance_data(season='2025-26', clear_existing=True):
    """
    Backfill cluster performance data for all completed games in a season.

    Args:
        season: NBA season to process
        clear_existing: If True, clear existing performance data before backfill
    """
    print(f"[Backfill] Starting cluster performance backfill for {season}")

    if clear_existing:
        # Clear existing performance data for this season
        from api.utils.db_schema_similarity import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM team_vs_cluster_performance WHERE season = ?", (season,))
        conn.commit()
        conn.close()
        print(f"[Backfill] Cleared existing performance data")

    # Get all completed games in chronological order
    nba_conn = get_nba_db_connection()
    cursor = nba_conn.cursor()

    # Fetch games with box score data
    cursor.execute("""
        SELECT
            g.game_id,
            g.game_date,
            g.home_team_id,
            g.away_team_id,
            g.home_team_score as home_score,
            g.away_team_score as away_score,
            g.game_status_text,
            tgl_home.pace as home_pace,
            tgl_home.points_in_paint as home_paint_pts,
            tgl_home.fg3m as home_three_pm,
            tgl_home.turnovers as home_turnovers,
            tgl_away.points_in_paint as away_paint_pts,
            tgl_away.fg3m as away_three_pm,
            tgl_away.turnovers as away_turnovers
        FROM todays_games g
        LEFT JOIN team_game_logs tgl_home
            ON g.game_id = tgl_home.game_id AND g.home_team_id = tgl_home.team_id
        LEFT JOIN team_game_logs tgl_away
            ON g.game_id = tgl_away.game_id AND g.away_team_id = tgl_away.team_id
        WHERE g.season = ?
            AND g.game_status_text = 'Final'
            AND g.home_team_score IS NOT NULL
            AND g.away_team_score IS NOT NULL
        ORDER BY g.game_date ASC, g.game_id ASC
    """, (season,))

    games = cursor.fetchall()
    nba_conn.close()

    print(f"[Backfill] Found {len(games)} completed games to process")

    # Check if both teams have cluster assignments
    home_cluster_check = get_team_cluster_assignment(games[0]['home_team_id'], season) if games else None
    away_cluster_check = get_team_cluster_assignment(games[0]['away_team_id'], season) if games else None

    if not home_cluster_check or not away_cluster_check:
        print(f"[Backfill] ERROR: Cluster assignments not found. Run refresh_similarity_engine() first.")
        return {
            'success': False,
            'error': 'Missing cluster assignments',
            'games_processed': 0
        }

    # Process each game
    games_processed = 0
    games_skipped = 0

    for game in games:
        game_id = game['game_id']
        game_date = game['game_date']
        home_team_id = game['home_team_id']
        away_team_id = game['away_team_id']
        home_score = game['home_score']
        away_score = game['away_score']
        total_pts = home_score + away_score

        # Get pace (use home team's pace as game pace)
        pace = game['home_pace'] if game['home_pace'] else 98.0

        # Note: sportsbook lines not available in current schema
        sportsbook_line = None

        # Get box score stats
        home_paint_pts = game['home_paint_pts']
        away_paint_pts = game['away_paint_pts']
        home_three_pm = game['home_three_pm']
        away_three_pm = game['away_three_pm']
        home_turnovers = game['home_turnovers']
        away_turnovers = game['away_turnovers']

        # Update performance for home team
        home_success = update_cluster_performance_after_game(
            team_id=home_team_id,
            opponent_id=away_team_id,
            team_pts=home_score,
            opponent_pts=away_score,
            total_pts=total_pts,
            pace=pace,
            sportsbook_line=sportsbook_line,
            team_paint_pts=home_paint_pts,
            opponent_paint_pts=away_paint_pts,
            team_three_pt_made=home_three_pm,
            opponent_three_pt_made=away_three_pm,
            team_turnovers=home_turnovers,
            opponent_turnovers=away_turnovers,
            season=season
        )

        # Update performance for away team
        away_success = update_cluster_performance_after_game(
            team_id=away_team_id,
            opponent_id=home_team_id,
            team_pts=away_score,
            opponent_pts=home_score,
            total_pts=total_pts,
            pace=pace,
            sportsbook_line=sportsbook_line,
            team_paint_pts=away_paint_pts,
            opponent_paint_pts=home_paint_pts,
            team_three_pt_made=away_three_pm,
            opponent_three_pt_made=home_three_pm,
            team_turnovers=away_turnovers,
            opponent_turnovers=home_turnovers,
            season=season
        )

        if home_success and away_success:
            games_processed += 1
            if games_processed % 50 == 0:
                print(f"[Backfill] Processed {games_processed}/{len(games)} games...")
        else:
            games_skipped += 1

    print(f"[Backfill] Backfill complete!")
    print(f"[Backfill] Games processed: {games_processed}")
    print(f"[Backfill] Games skipped: {games_skipped}")

    return {
        'success': True,
        'games_processed': games_processed,
        'games_skipped': games_skipped
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backfill cluster performance data')
    parser.add_argument('--season', type=str, default='2025-26', help='NBA season (default: 2025-26)')
    parser.add_argument('--no-clear', action='store_true', help='Do not clear existing data before backfill')

    args = parser.parse_args()

    start_time = datetime.now()

    result = backfill_performance_data(
        season=args.season,
        clear_existing=not args.no_clear
    )

    elapsed = (datetime.now() - start_time).total_seconds()

    if result['success']:
        print(f"\n✅ Backfill completed in {elapsed:.2f}s")
        print(f"   - Games processed: {result['games_processed']}")
        print(f"   - Games skipped: {result['games_skipped']}")
    else:
        print(f"\n❌ Backfill failed: {result.get('error', 'Unknown error')}")
