"""
Empty Possessions Calculator Module

Analyzes possession efficiency to protect against "fake pace" overs by calculating:
- TO% (Turnover Rate): TOV / Possessions - lower is better
- OREB% (Offensive Rebound Rate): OREB / (OREB + OppDREB) - higher is better
- FTr (Free Throw Rate): FTA / FGA - higher is better

Provides both Season and Last 5 game windows with opponent context blending.
"""

import sqlite3
import os
from typing import Dict, Optional, Tuple
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


def safe_divide(numerator, denominator, decimals=3):
    """
    Safely divide two numbers, handling None and zero division.

    Args:
        numerator: Number to divide
        denominator: Number to divide by
        decimals: Number of decimal places to round to

    Returns:
        Rounded result or None if division is invalid
    """
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    try:
        result = numerator / denominator
        return round(result, decimals)
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def calculate_possessions(fga: float, fta: float, oreb: float, tov: float) -> Optional[float]:
    """
    Calculate possessions using standard formula.

    Formula: FGA + (0.44 * FTA) - OREB + TOV

    Args:
        fga: Field goal attempts
        fta: Free throw attempts
        oreb: Offensive rebounds
        tov: Turnovers

    Returns:
        Possessions count or None if data is invalid
    """
    if any(x is None for x in [fga, fta, oreb, tov]):
        return None

    try:
        possessions = fga + (0.44 * fta) - oreb + tov
        return round(possessions, 2)
    except (ValueError, TypeError):
        return None


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max"""
    return max(min_val, min(value, max_val))


def normalize_to_pct(to_pct: float) -> Optional[float]:
    """
    Normalize TO% to 0-100 scale (inverted - lower is better).

    Typical range: 10-18%
    - 10% = 100 (excellent)
    - 18% = 0 (poor)

    Args:
        to_pct: Turnover percentage

    Returns:
        Normalized score 0-100 or None if invalid
    """
    if to_pct is None:
        return None

    # Invert: lower TO% is better
    normalized = 100 - ((to_pct - 10) / (18 - 10)) * 100
    return round(clamp(normalized, 0, 100), 1)


def normalize_oreb_pct(oreb_pct: float) -> Optional[float]:
    """
    Normalize OREB% to 0-100 scale (higher is better).

    Typical range: 20-35%
    - 20% = 0 (poor)
    - 35% = 100 (excellent)

    Args:
        oreb_pct: Offensive rebound percentage

    Returns:
        Normalized score 0-100 or None if invalid
    """
    if oreb_pct is None:
        return None

    normalized = ((oreb_pct - 20) / (35 - 20)) * 100
    return round(clamp(normalized, 0, 100), 1)


def normalize_ftr(ftr: float) -> Optional[float]:
    """
    Normalize FTr to 0-100 scale (higher is better).

    Typical range: 15-35%
    - 15% = 0 (poor)
    - 35% = 100 (excellent)

    Args:
        ftr: Free throw rate (FTA / FGA * 100)

    Returns:
        Normalized score 0-100 or None if invalid
    """
    if ftr is None:
        return None

    normalized = ((ftr - 15) / (35 - 15)) * 100
    return round(clamp(normalized, 0, 100), 1)


def calculate_team_conversion_score(normalized_to: float, normalized_oreb: float, normalized_ftr: float) -> Optional[float]:
    """
    Calculate weighted conversion score from normalized metrics.

    Weighting:
    - TO%: 40%
    - OREB%: 30%
    - FTr: 30%

    Args:
        normalized_to: Normalized turnover percentage (0-100)
        normalized_oreb: Normalized offensive rebound percentage (0-100)
        normalized_ftr: Normalized free throw rate (0-100)

    Returns:
        Weighted score 0-100 or None if any metric is None
    """
    if any(x is None for x in [normalized_to, normalized_oreb, normalized_ftr]):
        return None

    score = (normalized_to * 0.40) + (normalized_oreb * 0.30) + (normalized_ftr * 0.30)
    return round(score, 1)


def _get_game_type_filter() -> str:
    """
    Get SQL WHERE clause for game_type filtering.

    Always filters to Regular Season + NBA Cup (excludes Summer League, Preseason, etc.)

    Returns:
        SQL WHERE clause string
    """
    return "AND game_type IN ('Regular Season', 'NBA Cup')"


def calculate_team_rates(team_id: int, season: str = '2025-26', limit: Optional[int] = None) -> Optional[Dict]:
    """
    Calculate team's offensive rates (how they score).

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')
        limit: Number of games to include (None = all season)

    Returns:
        Dict with to_pct, oreb_pct, ftr, games or None if insufficient data
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    try:
        game_type_filter = _get_game_type_filter()

        # Build query
        query = f'''
            SELECT
                fga, fta, offensive_rebounds as oreb, turnovers as tov, opp_defensive_rebounds as opp_dreb
            FROM team_game_logs
            WHERE team_id = ?
                AND season = ?
                {game_type_filter}
            ORDER BY game_date DESC
        '''

        if limit:
            query += f' LIMIT {limit}'

        cursor.execute(query, (team_id, season))
        games = cursor.fetchall()

        if not games or len(games) < 3:
            logger.warning(f"Insufficient data for team {team_id}: {len(games) if games else 0} games")
            conn.close()
            return None

        # Aggregate totals
        total_fga = sum(game['fga'] or 0 for game in games)
        total_fta = sum(game['fta'] or 0 for game in games)
        total_oreb = sum(game['oreb'] or 0 for game in games)
        total_tov = sum(game['tov'] or 0 for game in games)
        total_opp_dreb = sum(game['opp_dreb'] or 0 for game in games)

        # Calculate possessions
        possessions = calculate_possessions(total_fga, total_fta, total_oreb, total_tov)
        if possessions is None or possessions == 0:
            conn.close()
            return None

        # Calculate rates - multiply by 100 FIRST, then round
        to_pct = (safe_divide(total_tov, possessions, decimals=6) * 100) if possessions else None
        oreb_pct = (safe_divide(total_oreb, total_oreb + total_opp_dreb, decimals=6) * 100) if (total_oreb + total_opp_dreb) > 0 else None
        ftr = (safe_divide(total_fta, total_fga, decimals=6) * 100) if total_fga > 0 else None

        conn.close()

        return {
            'to_pct': round(to_pct, 1) if to_pct is not None else None,
            'oreb_pct': round(oreb_pct, 1) if oreb_pct is not None else None,
            'ftr': round(ftr, 1) if ftr is not None else None,
            'games': len(games)
        }

    except Exception as e:
        logger.error(f"Error calculating team rates for team {team_id}: {e}")
        conn.close()
        return None


def calculate_opponent_rates_allowed(team_id: int, season: str = '2025-26', limit: Optional[int] = None) -> Optional[Dict]:
    """
    Calculate what rates the team allows opponents (defensive perspective).

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')
        limit: Number of games to include (None = all season)

    Returns:
        Dict with to_pct, oreb_pct, ftr, games or None if insufficient data
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    try:
        game_type_filter = _get_game_type_filter()

        # Build query - use opponent stats
        query = f'''
            SELECT
                opp_fga, opp_fta, opp_offensive_rebounds as opp_oreb, opp_turnovers as opp_tov, defensive_rebounds as dreb
            FROM team_game_logs
            WHERE team_id = ?
                AND season = ?
                {game_type_filter}
            ORDER BY game_date DESC
        '''

        if limit:
            query += f' LIMIT {limit}'

        cursor.execute(query, (team_id, season))
        games = cursor.fetchall()

        if not games or len(games) < 3:
            logger.warning(f"Insufficient data for team {team_id} opponent rates: {len(games) if games else 0} games")
            conn.close()
            return None

        # Aggregate totals (opponent stats)
        total_opp_fga = sum(game['opp_fga'] or 0 for game in games)
        total_opp_fta = sum(game['opp_fta'] or 0 for game in games)
        total_opp_oreb = sum(game['opp_oreb'] or 0 for game in games)
        total_opp_tov = sum(game['opp_tov'] or 0 for game in games)
        total_dreb = sum(game['dreb'] or 0 for game in games)

        # Calculate opponent possessions
        opp_possessions = calculate_possessions(total_opp_fga, total_opp_fta, total_opp_oreb, total_opp_tov)
        if opp_possessions is None or opp_possessions == 0:
            conn.close()
            return None

        # Calculate what team allowed - multiply by 100 FIRST, then round
        to_pct = (safe_divide(total_opp_tov, opp_possessions, decimals=6) * 100) if opp_possessions else None
        oreb_pct = (safe_divide(total_opp_oreb, total_opp_oreb + total_dreb, decimals=6) * 100) if (total_opp_oreb + total_dreb) > 0 else None
        ftr = (safe_divide(total_opp_fta, total_opp_fga, decimals=6) * 100) if total_opp_fga > 0 else None

        conn.close()

        return {
            'to_pct': round(to_pct, 1) if to_pct is not None else None,
            'oreb_pct': round(oreb_pct, 1) if oreb_pct is not None else None,
            'ftr': round(ftr, 1) if ftr is not None else None,
            'games': len(games)
        }

    except Exception as e:
        logger.error(f"Error calculating opponent rates allowed for team {team_id}: {e}")
        conn.close()
        return None


def blend_offense_vs_defense(team_rates: Dict, opp_rates: Dict) -> Optional[Dict]:
    """
    Blend team offense rates with opponent defense allowed rates.

    Blending: 60% team offense + 40% opponent defense allowed

    Args:
        team_rates: Dict with to_pct, oreb_pct, ftr
        opp_rates: Dict with to_pct, oreb_pct, ftr (what team allows)

    Returns:
        Dict with blended to_pct, oreb_pct, ftr or None if data missing
    """
    if not team_rates or not opp_rates:
        return None

    # Check all required metrics exist
    if any(team_rates.get(k) is None for k in ['to_pct', 'oreb_pct', 'ftr']):
        return None
    if any(opp_rates.get(k) is None for k in ['to_pct', 'oreb_pct', 'ftr']):
        return None

    blended_to = (team_rates['to_pct'] * 0.60) + (opp_rates['to_pct'] * 0.40)
    blended_oreb = (team_rates['oreb_pct'] * 0.60) + (opp_rates['oreb_pct'] * 0.40)
    blended_ftr = (team_rates['ftr'] * 0.60) + (opp_rates['ftr'] * 0.40)

    return {
        'to_pct': round(blended_to, 1),
        'oreb_pct': round(blended_oreb, 1),
        'ftr': round(blended_ftr, 1)
    }


def calculate_trend(season_val: float, last5_val: float, inverted: bool = False) -> str:
    """
    Calculate trend arrow based on season vs last 5 comparison.

    Args:
        season_val: Season average value
        last5_val: Last 5 games average value
        inverted: If True, lower is better (for TO%)

    Returns:
        'up', 'down', or 'neutral'
    """
    if season_val is None or last5_val is None:
        return 'neutral'

    diff = last5_val - season_val
    threshold = 1.0  # 1 percentage point threshold

    if abs(diff) < threshold:
        return 'neutral'

    if inverted:
        # For TO%, lower is better, so negative diff is good
        return 'up' if diff < 0 else 'down'
    else:
        # For OREB% and FTr, higher is better, so positive diff is good
        return 'up' if diff > 0 else 'down'


def generate_matchup_summary(home_score: float, away_score: float, matchup_score: float) -> str:
    """
    Generate one-sentence matchup summary.

    Args:
        home_score: Home team blended conversion score
        away_score: Away team blended conversion score
        matchup_score: Combined matchup score

    Returns:
        One-sentence summary string
    """
    if matchup_score >= 67:
        quality = "excellent"
    elif matchup_score >= 50:
        quality = "good"
    elif matchup_score >= 33:
        quality = "moderate"
    else:
        quality = "poor"

    score_diff = abs(home_score - away_score)
    if score_diff < 5:
        balance = "balanced offense expected from both teams"
    elif home_score > away_score:
        balance = "home team showing stronger efficiency"
    else:
        balance = "away team showing stronger efficiency"

    return f"{quality.capitalize()} possession conversion expected with {balance}."


def calculate_matchup_empty_possessions(game_id: str, season: str = '2025-26') -> Optional[Dict]:
    """
    Calculate empty possessions analysis for a game matchup.

    Main orchestration function that:
    1. Gets both teams from game
    2. Calculates season and last 5 rates for each team
    3. Calculates opponent rates allowed for each team's opponent
    4. Blends offense vs defense
    5. Normalizes and scores
    6. Generates summary

    Args:
        game_id: NBA game ID
        season: Season string (e.g., '2025-26')

    Returns:
        Complete empty possessions analysis or None if data unavailable
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    try:
        # Find game to get team IDs
        cursor.execute('''
            SELECT home_team_id, away_team_id
            FROM todays_games
            WHERE game_id = ?
            LIMIT 1
        ''', (game_id,))

        game_row = cursor.fetchone()

        if not game_row:
            # Try historical games table
            cursor.execute('''
                SELECT home_team_id, visitor_team_id as away_team_id
                FROM historical_games
                WHERE game_id = ?
                LIMIT 1
            ''', (game_id,))
            game_row = cursor.fetchone()

        if not game_row:
            logger.warning(f"Game {game_id} not found")
            conn.close()
            return None

        home_team_id = game_row['home_team_id']
        away_team_id = game_row['away_team_id']

        conn.close()

        # Calculate rates for both teams
        home_season = calculate_team_rates(home_team_id, season, limit=None)
        home_last5 = calculate_team_rates(home_team_id, season, limit=5)
        away_season = calculate_team_rates(away_team_id, season, limit=None)
        away_last5 = calculate_team_rates(away_team_id, season, limit=5)

        # Calculate opponent rates allowed (what each team's opponent typically allows)
        away_def_season = calculate_opponent_rates_allowed(away_team_id, season, limit=None)
        away_def_last5 = calculate_opponent_rates_allowed(away_team_id, season, limit=5)
        home_def_season = calculate_opponent_rates_allowed(home_team_id, season, limit=None)
        home_def_last5 = calculate_opponent_rates_allowed(home_team_id, season, limit=5)

        # Check for minimum data
        if not all([home_season, home_last5, away_season, away_last5,
                   away_def_season, away_def_last5, home_def_season, home_def_last5]):
            logger.warning(f"Insufficient data for game {game_id}")
            return None

        # Blend team offense with opponent defense
        home_blended_season = blend_offense_vs_defense(home_season, away_def_season)
        home_blended_last5 = blend_offense_vs_defense(home_last5, away_def_last5)
        away_blended_season = blend_offense_vs_defense(away_season, home_def_season)
        away_blended_last5 = blend_offense_vs_defense(away_last5, home_def_last5)

        if not all([home_blended_season, home_blended_last5, away_blended_season, away_blended_last5]):
            logger.warning(f"Failed to blend rates for game {game_id}")
            return None

        # Normalize and calculate scores
        # Home team season
        home_season_norm_to = normalize_to_pct(home_blended_season['to_pct'])
        home_season_norm_oreb = normalize_oreb_pct(home_blended_season['oreb_pct'])
        home_season_norm_ftr = normalize_ftr(home_blended_season['ftr'])
        home_season_score = calculate_team_conversion_score(home_season_norm_to, home_season_norm_oreb, home_season_norm_ftr)

        # Home team last 5
        home_last5_norm_to = normalize_to_pct(home_blended_last5['to_pct'])
        home_last5_norm_oreb = normalize_oreb_pct(home_blended_last5['oreb_pct'])
        home_last5_norm_ftr = normalize_ftr(home_blended_last5['ftr'])
        home_last5_score = calculate_team_conversion_score(home_last5_norm_to, home_last5_norm_oreb, home_last5_norm_ftr)

        # Away team season
        away_season_norm_to = normalize_to_pct(away_blended_season['to_pct'])
        away_season_norm_oreb = normalize_oreb_pct(away_blended_season['oreb_pct'])
        away_season_norm_ftr = normalize_ftr(away_blended_season['ftr'])
        away_season_score = calculate_team_conversion_score(away_season_norm_to, away_season_norm_oreb, away_season_norm_ftr)

        # Away team last 5
        away_last5_norm_to = normalize_to_pct(away_blended_last5['to_pct'])
        away_last5_norm_oreb = normalize_oreb_pct(away_blended_last5['oreb_pct'])
        away_last5_norm_ftr = normalize_ftr(away_blended_last5['ftr'])
        away_last5_score = calculate_team_conversion_score(away_last5_norm_to, away_last5_norm_oreb, away_last5_norm_ftr)

        # Calculate blended scores (average of season and last 5)
        home_blended_score = round((home_season_score + home_last5_score) / 2, 1) if all([home_season_score, home_last5_score]) else None
        away_blended_score = round((away_season_score + away_last5_score) / 2, 1) if all([away_season_score, away_last5_score]) else None

        # Calculate combined matchup score
        if home_blended_score is not None and away_blended_score is not None:
            matchup_score = round((home_blended_score + away_blended_score) / 2, 1)
        else:
            matchup_score = None

        # Calculate trends
        home_to_trend = calculate_trend(home_blended_season['to_pct'], home_blended_last5['to_pct'], inverted=True)
        home_oreb_trend = calculate_trend(home_blended_season['oreb_pct'], home_blended_last5['oreb_pct'])
        home_ftr_trend = calculate_trend(home_blended_season['ftr'], home_blended_last5['ftr'])

        away_to_trend = calculate_trend(away_blended_season['to_pct'], away_blended_last5['to_pct'], inverted=True)
        away_oreb_trend = calculate_trend(away_blended_season['oreb_pct'], away_blended_last5['oreb_pct'])
        away_ftr_trend = calculate_trend(away_blended_season['ftr'], away_blended_last5['ftr'])

        # Generate summary
        summary = generate_matchup_summary(home_blended_score, away_blended_score, matchup_score)

        # Debug logging to verify TO% values
        logger.info(f"[EmptyPossessions] Home TO%: Season={home_blended_season['to_pct']}, Last5={home_blended_last5['to_pct']}")
        logger.info(f"[EmptyPossessions] Away TO%: Season={away_blended_season['to_pct']}, Last5={away_blended_last5['to_pct']}")

        return {
            'home_team': {
                'team_id': home_team_id,
                'season': {
                    'to_pct': home_blended_season['to_pct'],
                    'oreb_pct': home_blended_season['oreb_pct'],
                    'ftr': home_blended_season['ftr'],
                    'score': home_season_score
                },
                'last5': {
                    'to_pct': home_blended_last5['to_pct'],
                    'oreb_pct': home_blended_last5['oreb_pct'],
                    'ftr': home_blended_last5['ftr'],
                    'score': home_last5_score
                },
                'blended_score': home_blended_score,
                'opp_context': {
                    'to_trend': home_to_trend,
                    'oreb_trend': home_oreb_trend,
                    'ftr_trend': home_ftr_trend
                }
            },
            'away_team': {
                'team_id': away_team_id,
                'season': {
                    'to_pct': away_blended_season['to_pct'],
                    'oreb_pct': away_blended_season['oreb_pct'],
                    'ftr': away_blended_season['ftr'],
                    'score': away_season_score
                },
                'last5': {
                    'to_pct': away_blended_last5['to_pct'],
                    'oreb_pct': away_blended_last5['oreb_pct'],
                    'ftr': away_blended_last5['ftr'],
                    'score': away_last5_score
                },
                'blended_score': away_blended_score,
                'opp_context': {
                    'to_trend': away_to_trend,
                    'oreb_trend': away_oreb_trend,
                    'ftr_trend': away_ftr_trend
                }
            },
            'matchup_score': matchup_score,
            'matchup_summary': summary
        }

    except Exception as e:
        logger.error(f"Error calculating empty possessions for game {game_id}: {e}")
        if 'conn' in locals():
            conn.close()
        return None
