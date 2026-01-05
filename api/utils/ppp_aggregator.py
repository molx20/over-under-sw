"""
PPP (Points Per Possession) Aggregator

Calculates and stores Points Per Possession metrics for teams.
Computes season-long PPP and rolling window PPP (last 10, last 5 games).

Usage:
    from api.utils.ppp_aggregator import (
        calculate_season_ppp,
        calculate_rolling_ppp,
        update_team_season_ppp,
        backfill_all_ppp_metrics
    )

    # Calculate season PPP for a specific team
    ppp = calculate_season_ppp(team_id=1610612738, season='2025-26', split_type='Overall')

    # Calculate rolling 10-game PPP
    ppp, games_used = calculate_rolling_ppp(team_id=1610612738, season='2025-26', n_games=10)

    # Update all PPP metrics for a team
    update_team_season_ppp(team_id=1610612738, season='2025-26', split_type='Overall')

    # Backfill all teams for a season
    backfill_all_ppp_metrics(season='2025-26')
"""

import sqlite3
from typing import Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def safe_divide(numerator: float, denominator: float, decimals: int = 3) -> Optional[float]:
    """
    Safe division with zero-check.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        decimals: Number of decimal places to round to

    Returns:
        Result of division, or None if denominator is zero
    """
    if denominator == 0 or denominator is None:
        return None
    return round(numerator / denominator, decimals)


def calculate_season_ppp(
    team_id: int,
    season: str,
    split_type: str = 'overall',
    conn: Optional[sqlite3.Connection] = None
) -> Optional[float]:
    """
    Calculate full season PPP from team_game_logs.

    Formula: SUM(team_pts) / SUM(possessions)

    Args:
        team_id: Team ID
        season: Season (e.g., '2025-26')
        split_type: 'overall', 'home', or 'away' (lowercase to match database)
        conn: Optional database connection

    Returns:
        PPP (e.g., 1.12) or None if insufficient data

    Edge Cases:
        - Returns None if total_possessions = 0
        - Filters out NULL possessions automatically
    """
    close_conn = False
    if conn is None:
        conn = _get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()

        # Build WHERE clause based on split_type (case-insensitive)
        where_clause = "team_id = ? AND season = ? AND possessions IS NOT NULL"
        params = [team_id, season]

        split_lower = split_type.lower()
        if split_lower == 'home':
            where_clause += " AND is_home = 1"
        elif split_lower == 'away':
            where_clause += " AND is_home = 0"
        # 'overall' doesn't add any extra condition

        cursor.execute(f'''
            SELECT SUM(team_pts) as total_pts, SUM(possessions) as total_poss
            FROM team_game_logs
            WHERE {where_clause}
        ''', params)

        row = cursor.fetchone()

        if not row or not row['total_poss'] or row['total_poss'] == 0:
            return None

        return safe_divide(row['total_pts'], row['total_poss'], decimals=3)

    finally:
        if close_conn:
            conn.close()


def calculate_rolling_ppp(
    team_id: int,
    season: str,
    n_games: int = 10,
    as_of_date: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> Tuple[Optional[float], int]:
    """
    Calculate rolling N-game PPP.

    Args:
        team_id: Team ID
        season: Season (e.g., '2025-26')
        n_games: Window size (10 or 5)
        as_of_date: Optional cutoff for backtesting (ISO format YYYY-MM-DD)
        conn: Optional database connection

    Returns:
        (ppp, actual_games_used)
        - actual_games_used may be < n_games early season

    Example:
        ppp, games = calculate_rolling_ppp(1610612738, '2025-26', n_games=10)
        # ppp = 1.15, games = 10 (full window)
        # OR
        # ppp = 1.08, games = 7 (early season, only 7 games played)
    """
    close_conn = False
    if conn is None:
        conn = _get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()

        # Build WHERE clause
        where_clause = "team_id = ? AND season = ? AND possessions IS NOT NULL"
        params = [team_id, season]

        if as_of_date:
            where_clause += " AND game_date < ?"
            params.append(as_of_date)

        cursor.execute(f'''
            SELECT team_pts, possessions
            FROM team_game_logs
            WHERE {where_clause}
            ORDER BY game_date DESC
            LIMIT ?
        ''', params + [n_games])

        games = cursor.fetchall()

        if not games:
            return None, 0

        total_pts = sum(g['team_pts'] for g in games)
        total_poss = sum(g['possessions'] for g in games)

        if total_poss == 0:
            return None, len(games)

        return safe_divide(total_pts, total_poss, decimals=3), len(games)

    finally:
        if close_conn:
            conn.close()


def update_team_season_ppp(
    team_id: int,
    season: str,
    split_type: str = 'overall'
) -> Dict:
    """
    Update team_season_stats with all PPP metrics.

    Updates:
    - ppp_season (full season)
    - ppp_last10 (last 10 games)
    - ppp_last5 (last 5 games)
    - metadata (games used, timestamp)

    Args:
        team_id: Team ID
        season: Season (e.g., '2025-26')
        split_type: 'overall', 'home', or 'away' (lowercase to match database)

    Returns:
        Dict with calculated PPP values
    """
    conn = _get_db_connection()

    try:
        # Calculate all PPP metrics
        ppp_season = calculate_season_ppp(team_id, season, split_type, conn)
        ppp_last10, last10_games = calculate_rolling_ppp(team_id, season, n_games=10, conn=conn)
        ppp_last5, last5_games = calculate_rolling_ppp(team_id, season, n_games=5, conn=conn)

        cursor = conn.cursor()

        # Update team_season_stats
        cursor.execute('''
            UPDATE team_season_stats
            SET ppp_season = ?,
                ppp_last10 = ?,
                ppp_last5 = ?,
                ppp_last10_games = ?,
                ppp_last5_games = ?,
                ppp_updated_at = ?
            WHERE team_id = ? AND season = ? AND split_type = ?
        ''', (
            ppp_season,
            ppp_last10,
            ppp_last5,
            last10_games,
            last5_games,
            datetime.utcnow().isoformat(),
            team_id,
            season,
            split_type
        ))

        conn.commit()

        logger.info(f'Updated PPP for team {team_id}, {season}, {split_type}')

        return {
            'team_id': team_id,
            'season': season,
            'split_type': split_type,
            'ppp_season': ppp_season,
            'ppp_last10': ppp_last10,
            'ppp_last5': ppp_last5,
            'last10_games': last10_games,
            'last5_games': last5_games
        }

    finally:
        conn.close()


def backfill_all_ppp_metrics(season: str = '2025-26'):
    """
    Backfill PPP for all teams and splits.

    Similar to season_opponent_stats_aggregator.backfill_all_season_opponent_stats()

    Args:
        season: Season to backfill (default: '2025-26')
    """
    conn = _get_db_connection()

    try:
        cursor = conn.cursor()

        print("=" * 80)
        print("BACKFILLING PPP METRICS")
        print("=" * 80)

        cursor.execute('''
            SELECT DISTINCT team_id, split_type
            FROM team_season_stats
            WHERE season = ?
            ORDER BY team_id, split_type
        ''', (season,))

        teams = cursor.fetchall()

        total = len(teams)
        print(f"\nFound {total} team/split combinations for season {season}\n")

        results = []

        for idx, row in enumerate(teams, 1):
            team_id = row['team_id']
            split_type = row['split_type']

            if idx % 10 == 0:
                print(f"  Progress: {idx}/{total}...")

            result = update_team_season_ppp(team_id, season, split_type)
            results.append(result)

        print(f"\n✅ ALL PPP METRICS UPDATED! ({total} combinations)")

        # Print summary statistics
        season_ppps = [r['ppp_season'] for r in results if r['ppp_season'] is not None and r['split_type'] == 'Overall']
        if season_ppps:
            avg_ppp = sum(season_ppps) / len(season_ppps)
            min_ppp = min(season_ppps)
            max_ppp = max(season_ppps)
            print(f"\nSeason PPP Summary (Overall split):")
            print(f"  Average: {avg_ppp:.3f}")
            print(f"  Range: {min_ppp:.3f} - {max_ppp:.3f}")

        return results

    finally:
        conn.close()


def get_team_ppp_metrics(
    team_id: int,
    season: str,
    split_type: str = 'overall'
) -> Optional[Dict]:
    """
    Get all PPP metrics for a team from team_season_stats.

    Args:
        team_id: Team ID
        season: Season (e.g., '2025-26')
        split_type: 'overall', 'home', or 'away' (lowercase to match database)

    Returns:
        Dict with PPP metrics or None if not found
    """
    conn = _get_db_connection()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT ppp_season, ppp_last10, ppp_last5,
                   ppp_last10_games, ppp_last5_games, ppp_updated_at
            FROM team_season_stats
            WHERE team_id = ? AND season = ? AND split_type = ?
        ''', (team_id, season, split_type))

        row = cursor.fetchone()

        if not row:
            return None

        return {
            'ppp_season': row['ppp_season'],
            'ppp_last10': row['ppp_last10'],
            'ppp_last5': row['ppp_last5'],
            'ppp_last10_games': row['ppp_last10_games'],
            'ppp_last5_games': row['ppp_last5_games'],
            'ppp_updated_at': row['ppp_updated_at']
        }

    finally:
        conn.close()


if __name__ == '__main__':
    # Run backfill when executed directly
    import sys

    if len(sys.argv) > 1:
        season = sys.argv[1]
    else:
        season = '2025-26'

    print(f'\n=== PPP Aggregator ===')
    print(f'Season: {season}\n')

    backfill_all_ppp_metrics(season)

    print('\n✅ PPP backfill complete!')
