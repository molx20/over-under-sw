"""
Bar Drilldown Utilities

Provides drilldown functionality for chart bars across all metrics:
- Scoring vs Defense Tiers / Pace Buckets
- 3PT Scoring vs 3PT Defense Tiers / Pace Buckets
- Turnovers vs Defense Pressure Tiers / Pace Buckets

This module returns the exact games that make up each bar,
ensuring count and averages match what's shown in the chart.
"""

import sqlite3
from typing import Dict, List, Optional
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


# ============================================================================
# PACE TIER CLASSIFICATION
# ============================================================================

def get_pace_tier(pace: float, pace_type: str = 'actual') -> Optional[str]:
    """
    Classify pace into tier bucket.

    Args:
        pace: Pace value (possessions per 48 minutes)
        pace_type: 'actual' or 'projected' (determines thresholds)

    Returns:
        'slow', 'normal', or 'fast'
    """
    if pace is None or pace <= 0:
        return None

    # Different thresholds based on whether it's projected or actual pace
    if pace_type == 'projected':
        # Projected pace uses slightly different thresholds
        if pace < 96:
            return 'slow'
        elif pace <= 101:
            return 'normal'
        else:
            return 'fast'
    else:
        # Actual pace thresholds
        if pace < 98:
            return 'slow'
        elif pace < 102:
            return 'normal'
        else:
            return 'fast'


# ============================================================================
# DEFENSE TIER CLASSIFICATION
# ============================================================================

def get_defense_tier_from_rank(rank: int) -> Optional[str]:
    """
    Map defensive rating rank (1-30) to tier.

    Args:
        rank: Defensive rating rank (1 = best defense, 30 = worst)

    Returns:
        'elite' (ranks 1-10), 'avg' (11-20), or 'bad' (21-30)
    """
    if rank is None or rank < 1 or rank > 30:
        return None

    if rank <= 10:
        return 'elite'
    elif rank <= 20:
        return 'avg'
    else:  # rank <= 30
        return 'bad'


def get_threept_def_tier_from_rank(rank: int) -> Optional[str]:
    """
    Map 3PT defense rank (1-30) to tier.

    Args:
        rank: 3PT% allowed rank (1 = best 3PT defense, 30 = worst)

    Returns:
        'elite' (ranks 1-10), 'avg' (11-20), or 'bad' (21-30)
    """
    if rank is None or rank < 1 or rank > 30:
        return None

    if rank <= 10:
        return 'elite'
    elif rank <= 20:
        return 'avg'
    else:
        return 'bad'


def get_pressure_tier_from_rank(rank: int) -> Optional[str]:
    """
    Map defensive pressure rank (1-30) to tier.

    Args:
        rank: Defensive pressure/turnover forcing rank

    Returns:
        'elite' (ranks 1-10), 'avg' (11-20), or 'low' (21-30)
    """
    if rank is None or rank < 1 or rank > 30:
        return None

    if rank <= 10:
        return 'elite'
    elif rank <= 20:
        return 'avg'
    else:
        return 'low'


def get_ball_movement_tier_from_rank(rank: int) -> Optional[str]:
    """
    Map ball-movement defense rank (1-30) to tier.

    Args:
        rank: Ball-movement defense rank (1 = allows fewest assists, 30 = most)

    Returns:
        'elite' (ranks 1-10), 'avg' (11-20), or 'bad' (21-30)
    """
    if rank is None or rank < 1 or rank > 30:
        return None

    if rank <= 10:
        return 'elite'
    elif rank <= 20:
        return 'avg'
    else:
        return 'bad'


# ============================================================================
# OPPONENT RANK LOOKUP
# ============================================================================

def get_opponent_def_rank(opponent_team_id: int, game_date: str, season: str) -> Optional[int]:
    """
    Get opponent's defensive rating rank at time of game.

    For now, uses season-to-date rank. In future, could use snapshot ranks.

    Args:
        opponent_team_id: Opponent team ID
        game_date: Game date (ISO format)
        season: Season string

    Returns:
        Defensive rating rank (1-30) or None
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    try:
        # Get opponent's defensive rating rank (already computed in team_season_stats)
        cursor.execute('''
            SELECT def_rtg_rank
            FROM team_season_stats
            WHERE team_id = ?
                AND season = ?
                AND split_type = 'overall'
        ''', (opponent_team_id, season))

        row = cursor.fetchone()
        return row['def_rtg_rank'] if row and row['def_rtg_rank'] else None

    finally:
        conn.close()


def get_opponent_threept_def_rank(opponent_team_id: int, game_date: str, season: str) -> Optional[int]:
    """
    Get opponent's 3PT% allowed rank at time of game.

    Args:
        opponent_team_id: Opponent team ID
        game_date: Game date (ISO format)
        season: Season string

    Returns:
        3PT% allowed rank (1-30) or None
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    try:
        # Get opponent's 3PT defense rank (already computed in team_season_stats)
        cursor.execute('''
            SELECT opp_fg3_pct_rank
            FROM team_season_stats
            WHERE team_id = ?
                AND season = ?
                AND split_type = 'overall'
        ''', (opponent_team_id, season))

        row = cursor.fetchone()
        return row['opp_fg3_pct_rank'] if row and row['opp_fg3_pct_rank'] else None

    finally:
        conn.close()


def get_opponent_pressure_rank(opponent_team_id: int, game_date: str, season: str) -> Optional[int]:
    """
    Get opponent's defensive pressure rank (based on opponent turnovers forced).

    Args:
        opponent_team_id: Opponent team ID
        game_date: Game date
        season: Season string

    Returns:
        Pressure rank (1-30) or None
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    try:
        # Get opponent's turnover pressure rank (already computed in team_season_stats)
        cursor.execute('''
            SELECT opp_tov_rank
            FROM team_season_stats
            WHERE team_id = ?
                AND season = ?
                AND split_type = 'overall'
        ''', (opponent_team_id, season))

        row = cursor.fetchone()
        return row['opp_tov_rank'] if row and row['opp_tov_rank'] else None

    finally:
        conn.close()


def get_opponent_assists_rank(opponent_team_id: int, game_date: str, season: str) -> Optional[int]:
    """
    Get opponent's ball-movement defense rank (based on opponent assists allowed).

    Args:
        opponent_team_id: Opponent team ID
        game_date: Game date
        season: Season string

    Returns:
        Assists allowed rank (1-30) or None
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    try:
        # Get opponent's assists allowed rank (already computed in team_season_stats)
        cursor.execute('''
            SELECT opp_assists_rank
            FROM team_season_stats
            WHERE team_id = ?
                AND season = ?
                AND split_type = 'overall'
        ''', (opponent_team_id, season))

        row = cursor.fetchone()
        return row['opp_assists_rank'] if row and row['opp_assists_rank'] else None

    finally:
        conn.close()


# ============================================================================
# DRILLDOWN QUERY FUNCTIONS
# ============================================================================

def get_drilldown_games(
    team_id: int,
    metric: str,
    dimension: str,
    context: str,
    bucket: Optional[str] = None,
    tier: Optional[str] = None,
    pace_type: str = 'actual',
    season: str = '2025-26'
) -> Dict:
    """
    Get the exact games that make up a bar in any chart.

    Args:
        team_id: Team ID
        metric: 'scoring', 'threept', or 'turnovers'
        dimension: 'pace_bucket', 'defense_tier', 'threept_def_tier', or 'pressure_tier'
        context: 'home' or 'away'
        bucket: Pace bucket ('slow', 'normal', 'fast') if dimension is pace_bucket
        tier: Tier ('elite', 'avg', 'bad' or 'low') if dimension is a tier
        pace_type: 'actual' or 'projected' (for pace_bucket dimension)
        season: Season string

    Returns:
        {
            'count': int,
            'bar_value': float,  # Average value shown in bar
            'games': [...]  # List of game objects
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    try:
        # Build query based on metric and dimension
        is_home = 1 if context == 'home' else 0

        # Base query gets all games for this team in this context
        # FILTER: Only Regular Season + NBA Cup (exclude Summer League, preseason, etc.)
        query = '''
            SELECT
                tgl.game_id,
                tgl.game_date,
                tgl.is_home,
                tgl.opponent_team_id,
                tgl.opponent_abbr,
                tgl.team_pts,
                tgl.opp_pts,
                tgl.fg3m,
                tgl.fg3a,
                tgl.fg3_pct,
                tgl.turnovers as team_tov,
                tgl.assists as team_ast,
                tgl.pace as pace_actual,
                g.actual_total_points as total_points
            FROM team_game_logs tgl
            LEFT JOIN games g ON tgl.game_id = g.id
            WHERE tgl.team_id = ?
                AND tgl.season = ?
                AND tgl.is_home = ?
                AND tgl.team_pts IS NOT NULL
                AND tgl.game_type IN ('Regular Season', 'NBA Cup')
        '''

        params = [team_id, season, is_home]

        cursor.execute(query, params)
        all_games = cursor.fetchall()

        # Filter games based on dimension
        filtered_games = []

        for game in all_games:
            include_game = False
            game_dict = dict(game)

            # Add computed fields
            game_dict['three_pt_points'] = (game['fg3m'] or 0) * 3

            if dimension == 'pace_bucket':
                # Use actual pace for filtering
                pace_val = game['pace_actual']
                if pace_val:
                    game_pace_tier = get_pace_tier(pace_val, pace_type)
                    game_dict['pace_value'] = pace_val
                    game_dict['tier_label'] = game_pace_tier.capitalize() if game_pace_tier else None
                    include_game = (game_pace_tier == bucket)

            elif dimension == 'defense_tier':
                # Get opponent's defensive rank
                opp_rank = get_opponent_def_rank(
                    game['opponent_team_id'],
                    game['game_date'],
                    season
                )
                if opp_rank:
                    opp_tier = get_defense_tier_from_rank(opp_rank)
                    game_dict['opponent_rank'] = opp_rank
                    game_dict['tier_label'] = opp_tier.capitalize() if opp_tier else None
                    include_game = (opp_tier == tier)

            elif dimension == 'threept_def_tier':
                # Get opponent's 3PT defensive rank
                opp_rank = get_opponent_threept_def_rank(
                    game['opponent_team_id'],
                    game['game_date'],
                    season
                )
                if opp_rank:
                    opp_tier = get_threept_def_tier_from_rank(opp_rank)
                    game_dict['opponent_rank'] = opp_rank
                    game_dict['tier_label'] = opp_tier.capitalize() if opp_tier else None
                    include_game = (opp_tier == tier)

            elif dimension == 'pressure_tier':
                # Get opponent's pressure rank
                opp_rank = get_opponent_pressure_rank(
                    game['opponent_team_id'],
                    game['game_date'],
                    season
                )
                if opp_rank:
                    opp_tier = get_pressure_tier_from_rank(opp_rank)
                    game_dict['opponent_rank'] = opp_rank
                    game_dict['tier_label'] = opp_tier.capitalize() if opp_tier else None
                    include_game = (opp_tier == tier)

            elif dimension == 'ball_movement_tier':
                # Get opponent's ball-movement defense rank
                opp_rank = get_opponent_assists_rank(
                    game['opponent_team_id'],
                    game['game_date'],
                    season
                )
                if opp_rank:
                    opp_tier = get_ball_movement_tier_from_rank(opp_rank)
                    game_dict['opponent_rank'] = opp_rank
                    game_dict['tier_label'] = opp_tier.capitalize() if opp_tier else None
                    include_game = (opp_tier == tier)

            if include_game:
                filtered_games.append(game_dict)

        # Calculate bar value based on metric
        if not filtered_games:
            return {
                'count': 0,
                'bar_value': 0,
                'games': []
            }

        bar_value = 0

        if metric == 'scoring':
            # Average points per game
            bar_value = sum(g['team_pts'] or 0 for g in filtered_games) / len(filtered_games)

        elif metric == 'threept':
            # Average 3PT points per game
            bar_value = sum(g['three_pt_points'] for g in filtered_games) / len(filtered_games)

        elif metric == 'turnovers':
            # Average turnovers per game
            bar_value = sum(g['team_tov'] or 0 for g in filtered_games) / len(filtered_games)

        elif metric == 'assists':
            # Average assists per game
            bar_value = sum(g['team_ast'] or 0 for g in filtered_games) / len(filtered_games)

        return {
            'count': len(filtered_games),
            'bar_value': round(bar_value, 1),
            'games': filtered_games
        }

    finally:
        conn.close()
