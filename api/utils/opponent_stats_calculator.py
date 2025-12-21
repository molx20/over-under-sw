"""
Opponent Statistics Calculator Module

This module computes opponent statistics and possessions for NBA games.

KEY CONCEPTS:
1. Opponent stats = the other team's stats in the same game
2. Possessions formula: FGA + 0.44*FTA - OREB + TOV
3. Each team's opponent stats show what they ALLOWED their opponent to do

Usage:
    from api.utils.opponent_stats_calculator import (
        compute_possessions,
        compute_opponent_stats_for_game,
        backfill_all_opponent_stats
    )

    # Compute possessions
    poss = compute_possessions(fga=85, fta=24, oreb=10, tov=14)

    # Compute opponent stats for a specific game
    compute_opponent_stats_for_game(game_id, conn)

    # Backfill all games
    backfill_all_opponent_stats(season='2025-26')
"""

import sqlite3
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def compute_possessions(
    fga: Optional[int],
    fta: Optional[int],
    oreb: Optional[int],
    tov: Optional[int]
) -> Optional[float]:
    """
    Compute possessions using the standard formula:
        Possessions = FGA + 0.44 * FTA - OREB + TOV

    Args:
        fga: Field goal attempts
        fta: Free throw attempts
        oreb: Offensive rebounds
        tov: Turnovers

    Returns:
        Possessions (float), or None if any required stat is missing
    """
    if any(x is None for x in [fga, fta, oreb, tov]):
        return None

    try:
        possessions = fga + (0.44 * fta) - oreb + tov
        return round(possessions, 1)
    except (ValueError, TypeError):
        return None


def safe_divide(numerator, denominator, decimals=3):
    """Safely divide two numbers, returning None if division fails or denominator is 0"""
    if numerator is None or denominator is None:
        return None
    try:
        if denominator == 0:
            return None
        result = numerator / denominator
        return round(result, decimals)
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def compute_opponent_stats_for_game(game_id: str, conn: sqlite3.Connection) -> Dict[str, int]:
    """
    Compute opponent statistics for both teams in a game.

    For each team, opponent stats = the other team's stats in the same game.

    Args:
        game_id: NBA game ID (e.g., "0022500123")
        conn: SQLite connection

    Returns:
        Dictionary with update counts: {'updated': 2, 'errors': 0}
    """
    cursor = conn.cursor()
    result = {'updated': 0, 'errors': 0}

    try:
        # Get both teams' stats for this game
        cursor.execute('''
            SELECT
                team_id,
                fgm, fga, fg_pct,
                fg2m, fg2a,
                fg3m, fg3a, fg3_pct,
                ftm, fta, ft_pct,
                offensive_rebounds,
                defensive_rebounds,
                rebounds,
                assists,
                turnovers,
                steals,
                blocks,
                team_pts,
                pace,
                off_rating,
                def_rating,
                points_off_turnovers,
                fast_break_points,
                points_in_paint,
                second_chance_points
            FROM team_game_logs
            WHERE game_id = ?
            ORDER BY team_id
        ''', (game_id,))

        teams = cursor.fetchall()

        if len(teams) != 2:
            logger.warning(f"Game {game_id} does not have exactly 2 teams (found {len(teams)})")
            result['errors'] += 1
            return result

        # Extract stats for both teams
        team_a = teams[0]
        team_b = teams[1]

        # For each team, the opponent's stats = the other team's stats
        for team_row, opp_row in [(team_a, team_b), (team_b, team_a)]:
            team_id = team_row[0]

            # Unpack team's own stats for possession calculation
            team_fga = team_row[2]  # fga
            team_fta = team_row[9]  # fta
            team_oreb = team_row[11]  # offensive_rebounds
            team_tov = team_row[15]  # turnovers

            # Unpack opponent's stats
            opp_fgm = opp_row[1]
            opp_fga = opp_row[2]
            opp_fg_pct = opp_row[3]
            opp_fg2m = opp_row[4]
            opp_fg2a = opp_row[5]
            opp_fg3m = opp_row[6]
            opp_fg3a = opp_row[7]
            opp_fg3_pct = opp_row[8]
            opp_ftm = opp_row[9]
            opp_fta = opp_row[10]
            opp_ft_pct = opp_row[11]
            opp_offensive_rebounds = opp_row[12]
            opp_defensive_rebounds = opp_row[13]
            opp_rebounds = opp_row[14]
            opp_assists = opp_row[15]
            opp_turnovers = opp_row[16]
            opp_steals = opp_row[17]
            opp_blocks = opp_row[18]
            opp_pts = opp_row[19]
            opp_pace = opp_row[20]
            opp_off_rating = opp_row[21]
            opp_def_rating = opp_row[22]
            opp_points_off_turnovers = opp_row[23]
            opp_fast_break_points = opp_row[24]
            opp_points_in_paint = opp_row[25]
            opp_second_chance_points = opp_row[26]

            # Compute FG2 percentage for opponent
            opp_fg2_pct = safe_divide(opp_fg2m, opp_fg2a)

            # Compute possessions for both team and opponent
            team_possessions = compute_possessions(team_fga, team_fta, team_oreb, team_tov)
            opp_possessions = compute_possessions(opp_fga, opp_fta, opp_offensive_rebounds, opp_turnovers)

            # Update the team's row with opponent stats
            cursor.execute('''
                UPDATE team_game_logs
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
                    opp_turnovers = ?,
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
                WHERE game_id = ? AND team_id = ?
            ''', (
                opp_fgm, opp_fga, opp_fg_pct,
                opp_fg2m, opp_fg2a, opp_fg2_pct,
                opp_fg3m, opp_fg3a, opp_fg3_pct,
                opp_ftm, opp_fta, opp_ft_pct,
                opp_offensive_rebounds, opp_defensive_rebounds, opp_rebounds,
                opp_assists, opp_turnovers, opp_steals, opp_blocks,
                opp_pace, opp_off_rating, opp_def_rating,
                opp_points_off_turnovers, opp_fast_break_points,
                opp_points_in_paint, opp_second_chance_points,
                team_possessions, opp_possessions,
                game_id, team_id
            ))

            result['updated'] += 1

    except Exception as e:
        logger.error(f"Error computing opponent stats for game {game_id}: {e}")
        import traceback
        traceback.print_exc()
        result['errors'] += 1

    return result


def backfill_all_opponent_stats(season: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, int]:
    """
    Backfill opponent statistics for all games in the database.

    Args:
        season: Optional season filter (e.g., '2025-26'). If None, processes all seasons.
        limit: Optional limit on number of games to process (for testing)

    Returns:
        Dictionary with counts: {'total_games': X, 'updated': Y, 'errors': Z}
    """
    conn = sqlite3.connect(NBA_DATA_DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("BACKFILLING OPPONENT STATISTICS")
    print("=" * 80)

    # Get unique game_ids to process
    if season:
        cursor.execute('''
            SELECT DISTINCT game_id
            FROM team_game_logs
            WHERE season = ?
            ORDER BY game_date DESC
        ''', (season,))
        print(f"\nFiltering by season: {season}")
    else:
        cursor.execute('''
            SELECT DISTINCT game_id
            FROM team_game_logs
            ORDER BY game_date DESC
        ''')
        print("\nProcessing ALL seasons")

    game_ids = [row[0] for row in cursor.fetchall()]

    if limit:
        game_ids = game_ids[:limit]
        print(f"Limiting to first {limit} games")

    total_games = len(game_ids)
    print(f"Found {total_games} games to process\n")

    results = {'total_games': total_games, 'updated': 0, 'errors': 0}

    # Process each game
    for idx, game_id in enumerate(game_ids, 1):
        if idx % 50 == 0:
            print(f"  Progress: {idx}/{total_games} games processed...")

        game_result = compute_opponent_stats_for_game(game_id, conn)
        results['updated'] += game_result['updated']
        results['errors'] += game_result['errors']

    # Commit all changes
    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print("✅ BACKFILL COMPLETE!")
    print(f"   Total games: {results['total_games']}")
    print(f"   Teams updated: {results['updated']}")
    print(f"   Errors: {results['errors']}")
    print("=" * 80)

    return results


if __name__ == '__main__':
    # Test the module
    print("Testing Opponent Stats Calculator\n")

    # Test possession calculation
    print("1. Testing possession formula:")
    poss = compute_possessions(fga=85, fta=24, oreb=10, tov=14)
    print(f"   FGA=85, FTA=24, OREB=10, TOV=14 → Possessions: {poss}")

    # Backfill all games
    print("\n2. Backfilling opponent stats for 2025-26 season:")
    results = backfill_all_opponent_stats(season='2025-26')

    print("\n3. Sample query to verify:")
    conn = sqlite3.connect(NBA_DATA_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            game_id,
            team_pts as team_score,
            opp_pts as opp_score,
            fg3a as team_3pa,
            opp_fg3a as opp_3pa,
            possessions,
            opp_possessions
        FROM team_game_logs
        WHERE opp_fg3a IS NOT NULL
        LIMIT 3
    ''')

    print("\n   Sample results:")
    for row in cursor.fetchall():
        print(f"     Game {row[0]}: Team={row[1]}, Opp={row[2]}, Team3PA={row[3]}, Opp3PA={row[4]}, Poss={row[5]}, OppPoss={row[6]}")

    conn.close()
