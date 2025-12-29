"""
Scoring Mix Splits Module

Analyzes how teams generate points across three scoring sources:
- 3-Point Field Goals (FG3M * 3)
- 2-Point Field Goals ((FGM - FG3M) * 2)
- Free Throws (FTM)

Provides three analysis modes:
1. Team: How the team scores their own points
2. Opponent Allowed: What scoring mix the team allows opponents
3. Game Mix: Combined scoring sources from both teams in games

Each mode provides Last 5 vs Season averages for trend analysis.
"""

import sqlite3
import os
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

# Database path
NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _calculate_scoring_mix(three_pt_points: float, two_pt_points: float, ft_points: float, games: int) -> Dict:
    """
    Calculate scoring mix percentages from point totals.

    Args:
        three_pt_points: Total points from 3-pointers
        two_pt_points: Total points from 2-pointers
        ft_points: Total points from free throws
        games: Number of games in sample

    Returns:
        Dict with pct_3pt, pct_2pt, pct_ft, games, avg_pts
    """
    total_points = three_pt_points + two_pt_points + ft_points

    # Handle division by zero
    if total_points == 0:
        return {
            'pct_3pt': 0.0,
            'pct_2pt': 0.0,
            'pct_ft': 0.0,
            'games': games,
            'avg_pts': 0.0
        }

    return {
        'pct_3pt': round((three_pt_points / total_points) * 100, 1),
        'pct_2pt': round((two_pt_points / total_points) * 100, 1),
        'pct_ft': round((ft_points / total_points) * 100, 1),
        'games': games,
        'avg_pts': round(total_points / games, 1) if games > 0 else 0.0
    }


def _get_game_type_filter() -> str:
    """
    Get SQL WHERE clause for game_type filtering.

    Always filters to Regular Season + NBA Cup (excludes Summer League, Preseason, etc.)
    Regular season started Oct 21, 2025.

    Returns:
        SQL WHERE clause string
    """
    # Always exclude Summer League and other non-regular season games
    return "AND tgl.game_type IN ('Regular Season', 'NBA Cup')"


def get_team_scoring_mix(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Calculate scoring mix for a team across 3 modes and 2 time periods.

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')

    Returns:
        Dictionary with team info and scoring mix data for all modes.

    Response Structure:
        {
            'team_id': 1610612738,
            'team_abbreviation': 'BOS',
            'full_name': 'Boston Celtics',
            'season': '2025-26',
            'team': {
                'last5': {'pct_3pt': 42.0, 'pct_2pt': 43.0, 'pct_ft': 15.0, 'games': 5, 'avg_pts': 115.2},
                'season': {'pct_3pt': 40.5, 'pct_2pt': 44.2, 'pct_ft': 15.3, 'games': 30, 'avg_pts': 117.8}
            },
            'opp_allowed': {
                'last5': {...},
                'season': {...}
            },
            'game_mix': {
                'last5': {...},
                'season': {...}
            }
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Get team info
        cursor.execute('''
            SELECT team_id, team_abbreviation, full_name
            FROM nba_teams
            WHERE team_id = ?
            LIMIT 1
        ''', (team_id,))

        team_row = cursor.fetchone()

        if not team_row:
            logger.warning(f"Team {team_id} not found in database")
            conn.close()
            return None

        team_info = {
            'team_id': team_row['team_id'],
            'team_abbreviation': team_row['team_abbreviation'],
            'full_name': team_row['full_name'],
            'season': season
        }

        # Get game type filter
        game_type_filter = _get_game_type_filter()

        # Step 2: Fetch ALL season games
        query = f'''
            SELECT
                tgl.fg3m,
                tgl.fg2m,
                tgl.ftm,
                tgl.opp_fg3m,
                tgl.opp_fg2m,
                tgl.opp_ftm,
                tgl.team_pts
            FROM team_game_logs tgl
            WHERE tgl.team_id = ?
                AND tgl.season = ?
                {game_type_filter}
            ORDER BY tgl.game_date DESC
        '''

        cursor.execute(query, (team_id, season))
        all_games = cursor.fetchall()

        if not all_games:
            logger.warning(f"No game data found for team {team_id} in season {season}")
            conn.close()
            return _empty_scoring_mix(team_info)

        # Step 3: Calculate Team Mode (team's own scoring)
        team_info['team'] = _calculate_team_mode(all_games)

        # Step 4: Calculate Opponent Allowed Mode (what team allows opponents to score)
        team_info['opp_allowed'] = _calculate_opp_allowed_mode(all_games)

        # Step 5: Calculate Game Mix Mode (combined scoring from both teams)
        team_info['game_mix'] = _calculate_game_mix_mode(all_games)

        conn.close()

        logger.info(f"Generated scoring mix splits for team {team_id} ({team_info['team_abbreviation']}) - {season}")
        return team_info

    except Exception as e:
        logger.error(f"Error generating scoring mix splits for team {team_id}: {e}")
        conn.close()
        return None


def _calculate_team_mode(all_games: list) -> Dict:
    """
    Calculate Team Mode: How team scores their own points.

    Uses: fg3m, fg2m, ftm
    """
    # Last 5 games
    last5_games = all_games[:5]
    last5_3pt = sum((game['fg3m'] or 0) * 3 for game in last5_games)
    last5_2pt = sum((game['fg2m'] or 0) * 2 for game in last5_games)
    last5_ft = sum((game['ftm'] or 0) for game in last5_games)

    # All season games
    season_3pt = sum((game['fg3m'] or 0) * 3 for game in all_games)
    season_2pt = sum((game['fg2m'] or 0) * 2 for game in all_games)
    season_ft = sum((game['ftm'] or 0) for game in all_games)

    return {
        'last5': _calculate_scoring_mix(last5_3pt, last5_2pt, last5_ft, len(last5_games)),
        'season': _calculate_scoring_mix(season_3pt, season_2pt, season_ft, len(all_games))
    }


def _calculate_opp_allowed_mode(all_games: list) -> Dict:
    """
    Calculate Opponent Allowed Mode: What team allows opponents to score.

    Uses: opp_fg3m, opp_fg2m, opp_ftm
    """
    # Last 5 games
    last5_games = all_games[:5]
    last5_3pt = sum((game['opp_fg3m'] or 0) * 3 for game in last5_games)
    last5_2pt = sum((game['opp_fg2m'] or 0) * 2 for game in last5_games)
    last5_ft = sum((game['opp_ftm'] or 0) for game in last5_games)

    # All season games
    season_3pt = sum((game['opp_fg3m'] or 0) * 3 for game in all_games)
    season_2pt = sum((game['opp_fg2m'] or 0) * 2 for game in all_games)
    season_ft = sum((game['opp_ftm'] or 0) for game in all_games)

    return {
        'last5': _calculate_scoring_mix(last5_3pt, last5_2pt, last5_ft, len(last5_games)),
        'season': _calculate_scoring_mix(season_3pt, season_2pt, season_ft, len(all_games))
    }


def _calculate_game_mix_mode(all_games: list) -> Dict:
    """
    Calculate Game Mix Mode: Combined scoring from both teams.

    Per user specification: Sum ALL shots across all games, then calculate single mix %.
    For last 5: sum all FG2M/FG3M/FTM from both teams across all 5 games, then calculate.
    """
    # Last 5 games - sum both teams' shots
    last5_games = all_games[:5]
    last5_total_fg3m = sum((game['fg3m'] or 0) + (game['opp_fg3m'] or 0) for game in last5_games)
    last5_total_fg2m = sum((game['fg2m'] or 0) + (game['opp_fg2m'] or 0) for game in last5_games)
    last5_total_ftm = sum((game['ftm'] or 0) + (game['opp_ftm'] or 0) for game in last5_games)

    last5_3pt = last5_total_fg3m * 3
    last5_2pt = last5_total_fg2m * 2
    last5_ft = last5_total_ftm

    # All season games - sum both teams' shots
    season_total_fg3m = sum((game['fg3m'] or 0) + (game['opp_fg3m'] or 0) for game in all_games)
    season_total_fg2m = sum((game['fg2m'] or 0) + (game['opp_fg2m'] or 0) for game in all_games)
    season_total_ftm = sum((game['ftm'] or 0) + (game['opp_ftm'] or 0) for game in all_games)

    season_3pt = season_total_fg3m * 3
    season_2pt = season_total_fg2m * 2
    season_ft = season_total_ftm

    return {
        'last5': _calculate_scoring_mix(last5_3pt, last5_2pt, last5_ft, len(last5_games)),
        'season': _calculate_scoring_mix(season_3pt, season_2pt, season_ft, len(all_games))
    }


def _empty_scoring_mix(team_info: Dict) -> Dict:
    """
    Return empty scoring mix structure when no game data available.

    Args:
        team_info: Dict with team_id, team_abbreviation, full_name, season

    Returns:
        Team info with empty scoring mix data
    """
    empty_mix = {
        'pct_3pt': 0.0,
        'pct_2pt': 0.0,
        'pct_ft': 0.0,
        'games': 0,
        'avg_pts': 0.0
    }

    return {
        **team_info,
        'team': {
            'last5': empty_mix.copy(),
            'season': empty_mix.copy()
        },
        'opp_allowed': {
            'last5': empty_mix.copy(),
            'season': empty_mix.copy()
        },
        'game_mix': {
            'last5': empty_mix.copy(),
            'season': empty_mix.copy()
        }
    }
