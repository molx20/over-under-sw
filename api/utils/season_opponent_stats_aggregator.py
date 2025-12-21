"""
Season Opponent Statistics Aggregator

Aggregates per-game opponent stats into season averages for each team.
This computes what each team ALLOWS their opponents to do on average.

Usage:
    from api.utils.season_opponent_stats_aggregator import (
        aggregate_season_opponent_stats,
        update_team_season_opponent_stats,
        backfill_all_season_opponent_stats
    )

    # Aggregate stats for a specific team
    stats = aggregate_season_opponent_stats(team_id=1, season='2025-26', split_type='overall')

    # Update team_season_stats table for a team
    update_team_season_opponent_stats(team_id=1, season='2025-26', split_type='overall')

    # Backfill all teams for a season
    backfill_all_season_opponent_stats(season='2025-26')
"""

import sqlite3
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def aggregate_season_opponent_stats(
    team_id: int,
    season: str,
    split_type: str = 'overall',
    conn: Optional[sqlite3.Connection] = None
) -> Dict:
    """
    Aggregate opponent stats for a team's season.

    This computes what a team ALLOWS their opponents to do on average.
    For example:
    - opp_fg_pct = What FG% opponents shoot against this team
    - opp_pace = What pace opponents play at against this team
    - opp_turnovers = How many turnovers this team forces

    Args:
        team_id: Team ID
        season: Season (e.g., '2025-26')
        split_type: 'overall', 'home', or 'away'
        conn: Optional database connection

    Returns:
        Dictionary of season-average opponent stats, or None if no data
    """
    should_close = False
    if conn is None:
        conn = sqlite3.connect(NBA_DATA_DB_PATH)
        should_close = True

    cursor = conn.cursor()

    # Build WHERE clause for split type
    where_clause = "team_id = ? AND season = ?"
    params = [team_id, season]

    if split_type == 'home':
        where_clause += " AND is_home = 1"
    elif split_type == 'away':
        where_clause += " AND is_home = 0"

    # Aggregate opponent stats (what this team ALLOWED)
    cursor.execute(f'''
        SELECT
            COUNT(*) as games_played,
            AVG(opp_fgm) as opp_fgm,
            AVG(opp_fga) as opp_fga,
            AVG(opp_fg_pct) as opp_fg_pct,
            AVG(opp_fg2m) as opp_fg2m,
            AVG(opp_fg2a) as opp_fg2a,
            AVG(opp_fg2_pct) as opp_fg2_pct,
            AVG(opp_fg3m) as opp_fg3m,
            AVG(opp_fg3a) as opp_fg3a,
            AVG(opp_fg3_pct) as opp_fg3_pct,
            AVG(opp_ftm) as opp_ftm,
            AVG(opp_fta) as opp_fta,
            AVG(opp_ft_pct) as opp_ft_pct,
            AVG(opp_offensive_rebounds) as opp_offensive_rebounds,
            AVG(opp_defensive_rebounds) as opp_defensive_rebounds,
            AVG(opp_rebounds) as opp_rebounds,
            AVG(opp_assists) as opp_assists,
            AVG(opp_turnovers) as opp_turnovers,
            AVG(opp_steals) as opp_steals,
            AVG(opp_blocks) as opp_blocks,
            AVG(opp_pace) as opp_pace,
            AVG(opp_off_rating) as opp_off_rating,
            AVG(opp_def_rating) as opp_def_rating,
            AVG(opp_points_off_turnovers) as opp_points_off_turnovers,
            AVG(opp_fast_break_points) as opp_fast_break_points,
            AVG(opp_points_in_paint) as opp_points_in_paint,
            AVG(opp_second_chance_points) as opp_second_chance_points,
            AVG(possessions) as possessions,
            AVG(opp_possessions) as opp_possessions
        FROM team_game_logs
        WHERE {where_clause}
    ''', params)

    row = cursor.fetchone()

    if should_close:
        conn.close()

    if not row or row[0] == 0:
        return None

    return {
        'games_played': row[0],
        'opp_fgm': round(row[1], 1) if row[1] else None,
        'opp_fga': round(row[2], 1) if row[2] else None,
        'opp_fg_pct': round(row[3], 3) if row[3] else None,
        'opp_fg2m': round(row[4], 1) if row[4] else None,
        'opp_fg2a': round(row[5], 1) if row[5] else None,
        'opp_fg2_pct': round(row[6], 3) if row[6] else None,
        'opp_fg3m': round(row[7], 1) if row[7] else None,
        'opp_fg3a': round(row[8], 1) if row[8] else None,
        'opp_fg3_pct': round(row[9], 3) if row[9] else None,
        'opp_ftm': round(row[10], 1) if row[10] else None,
        'opp_fta': round(row[11], 1) if row[11] else None,
        'opp_ft_pct': round(row[12], 3) if row[12] else None,
        'opp_offensive_rebounds': round(row[13], 1) if row[13] else None,
        'opp_defensive_rebounds': round(row[14], 1) if row[14] else None,
        'opp_rebounds': round(row[15], 1) if row[15] else None,
        'opp_assists': round(row[16], 1) if row[16] else None,
        'opp_turnovers': round(row[17], 1) if row[17] else None,
        'opp_steals': round(row[18], 1) if row[18] else None,
        'opp_blocks': round(row[19], 1) if row[19] else None,
        'opp_pace': round(row[20], 1) if row[20] else None,
        'opp_off_rating': round(row[21], 1) if row[21] else None,
        'opp_def_rating': round(row[22], 1) if row[22] else None,
        'opp_points_off_turnovers': round(row[23], 1) if row[23] else None,
        'opp_fast_break_points': round(row[24], 1) if row[24] else None,
        'opp_points_in_paint': round(row[25], 1) if row[25] else None,
        'opp_second_chance_points': round(row[26], 1) if row[26] else None,
        'possessions': round(row[27], 1) if row[27] else None,
        'opp_possessions': round(row[28], 1) if row[28] else None,
    }


def update_team_season_opponent_stats(team_id: int, season: str, split_type: str = 'overall'):
    """
    Update team_season_stats with aggregated opponent stats.

    Call this after game logs are populated with opponent stats.
    This will aggregate all per-game opponent stats into season averages
    and store them in the team_season_stats table.

    Args:
        team_id: Team ID
        season: Season (e.g., '2025-26')
        split_type: 'overall', 'home', or 'away'
    """
    conn = sqlite3.connect(NBA_DATA_DB_PATH)
    cursor = conn.cursor()

    # Get aggregated stats
    stats = aggregate_season_opponent_stats(team_id, season, split_type, conn)

    if not stats:
        logger.warning(f"No stats found for team {team_id}, season {season}, split {split_type}")
        conn.close()
        return

    # Update team_season_stats
    cursor.execute('''
        UPDATE team_season_stats
        SET
            opp_fgm = ?,
            opp_fga = ?,
            opp_fg_pct = ?,
            opp_fg2m = ?,
            opp_fg2a = ?,
            opp_fg2_pct = ?,
            opp_fg3m = ?,
            opp_fg3a = ?,
            opp_fg3_pct = ?,
            opp_ftm = ?,
            opp_fta = ?,
            opp_ft_pct = ?,
            opp_offensive_rebounds = ?,
            opp_defensive_rebounds = ?,
            opp_rebounds = ?,
            opp_assists = ?,
            opp_tov = ?,
            opp_steals = ?,
            opp_blocks = ?,
            opp_pace = ?,
            opp_off_rating = ?,
            opp_def_rating = ?,
            opp_points_off_turnovers = ?,
            opp_fast_break_points = ?,
            opp_points_in_paint = ?,
            opp_second_chance_points = ?,
            possessions = ?,
            opp_possessions = ?
        WHERE team_id = ? AND season = ? AND split_type = ?
    ''', (
        stats['opp_fgm'], stats['opp_fga'], stats['opp_fg_pct'],
        stats['opp_fg2m'], stats['opp_fg2a'], stats['opp_fg2_pct'],
        stats['opp_fg3m'], stats['opp_fg3a'], stats['opp_fg3_pct'],
        stats['opp_ftm'], stats['opp_fta'], stats['opp_ft_pct'],
        stats['opp_offensive_rebounds'], stats['opp_defensive_rebounds'], stats['opp_rebounds'],
        stats['opp_assists'], stats['opp_turnovers'], stats['opp_steals'], stats['opp_blocks'],
        stats['opp_pace'], stats['opp_off_rating'], stats['opp_def_rating'],
        stats['opp_points_off_turnovers'], stats['opp_fast_break_points'],
        stats['opp_points_in_paint'], stats['opp_second_chance_points'],
        stats['possessions'], stats['opp_possessions'],
        team_id, season, split_type
    ))

    conn.commit()
    conn.close()

    logger.info(f"✓ Updated opponent stats for team {team_id}, {season}, {split_type}")


def backfill_all_season_opponent_stats(season: str = '2025-26'):
    """
    Backfill season opponent stats for all teams.

    This will aggregate all per-game opponent stats into season averages
    for every team in the team_season_stats table.

    Args:
        season: Season (e.g., '2025-26')
    """
    conn = sqlite3.connect(NBA_DATA_DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("BACKFILLING SEASON OPPONENT STATISTICS")
    print("=" * 80)

    # Get all teams with season stats
    cursor.execute('''
        SELECT DISTINCT team_id, split_type
        FROM team_season_stats
        WHERE season = ?
        ORDER BY team_id, split_type
    ''', (season,))

    teams = cursor.fetchall()
    conn.close()

    total = len(teams)
    print(f"\nFound {total} team/split combinations to update for season {season}\n")

    for idx, (team_id, split_type) in enumerate(teams, 1):
        if idx % 10 == 0:
            print(f"  Progress: {idx}/{total} updated...")

        update_team_season_opponent_stats(team_id, season, split_type)

    print("\n" + "=" * 80)
    print("✅ ALL SEASON OPPONENT STATS UPDATED!")
    print(f"   Updated {total} team/split combinations")
    print("=" * 80)


if __name__ == '__main__':
    # Test the module
    print("Testing Season Opponent Stats Aggregator\n")

    # Backfill all teams for 2025-26 season
    print("Backfilling all season opponent stats for 2025-26...")
    backfill_all_season_opponent_stats('2025-26')

    print("\n2. Sample query to verify:")
    conn = sqlite3.connect(NBA_DATA_DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            team_id,
            split_type,
            opp_fg_pct,
            opp_fg3_pct,
            opp_pace,
            opp_possessions
        FROM team_season_stats
        WHERE season = '2025-26' AND split_type = 'overall'
        LIMIT 5
    ''')

    print("\n   Sample results:")
    for row in cursor.fetchall():
        print(f"     Team {row[0]} ({row[1]}): OppFG%={row[2]}, Opp3P%={row[3]}, OppPace={row[4]}, OppPoss={row[5]}")

    conn.close()
