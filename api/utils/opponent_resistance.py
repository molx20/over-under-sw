"""
Opponent Resistance Module (Possession-Only)

Calculates team identity metrics and opponent resistance to generate
expected matchup metrics for pregame analysis.

Key Metrics:
- Team Identity: TO%, OREB%, Empty Possessions (season + last5)
- Opponent Resistance: Forces TO%, Limits OREB%, FTr allowed (season + last5)
- Expected Matchup: Blended predictions based on team identity + opponent resistance

Date Range: Oct 21, 2025 - Jan 2, 2026
Database: api/data/nba_data.db (team_game_logs)
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Import DB helper
try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

NBA_DATA_DB_PATH = get_db_path('nba_data.db')

# In-memory cache for season aggregates (keyed by season+as_of_date)
_SEASON_CACHE = {}


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def _calculate_possessions(row: Dict, fta_coefficient: float = 0.44) -> float:
    """
    Calculate possessions estimate from box score
    possessions_est = FGA + fta_coefficient*FTA - OREB + TO

    Args:
        row: Game data dictionary
        fta_coefficient: Learned FTA weight (default 0.44 for backwards compatibility)
    """
    try:
        return row['fga'] + fta_coefficient * row['fta'] - row['offensive_rebounds'] + row['turnovers']
    except (KeyError, TypeError):
        # Fallback to database possessions if available
        return row.get('possessions', 0)


def _calculate_empty_possessions(row: Dict) -> float:
    """
    Calculate empty possessions estimate
    empty_possessions = (FGA - FGM) + (FTA - FTM) + TO - OREB
    """
    try:
        missed_fga = row['fga'] - row['fgm']
        missed_fta = row['fta'] - row['ftm']
        return missed_fga + missed_fta + row['turnovers'] - row['offensive_rebounds']
    except (KeyError, TypeError):
        return 0


def get_team_identity(
    team_id: int,
    season: str = '2025-26',
    as_of_date: str = '2026-01-02',
    window: str = 'season',
    fta_coefficient: Optional[float] = None
) -> Dict:
    """
    Get team's possession identity metrics

    Args:
        team_id: NBA team ID
        season: Season string
        as_of_date: Calculate metrics up to this date
        window: 'season' or 'last5'
        fta_coefficient: Optional learned FTA coefficient (loaded if None)

    Returns:
        {
            'team_id': int,
            'games_count': int,
            'avg_possessions': float,
            'to_pct': float,  # TO / possessions
            'oreb_pct': float,  # OREB / (OREB + opp_DREB)
            'ftr': float,  # FTA / FGA
            'avg_empty_possessions': float,
            'empty_rate': float,  # empty / possessions
        }
    """
    # Load learned coefficients if not provided
    if fta_coefficient is None:
        try:
            from api.utils.coefficient_learner import get_active_coefficients
            coeffs = get_active_coefficients(season)
            fta_coefficient = coeffs['fta_coefficient']
        except (ImportError, ValueError, KeyError):
            logger.warning("[opponent_resistance] Could not load learned coefficients, using default 0.44")
            fta_coefficient = 0.44

    conn = _get_db_connection()
    cursor = conn.cursor()

    # Build query based on window
    if window == 'last5':
        query = '''
            SELECT *
            FROM team_game_logs
            WHERE team_id = ?
              AND season = ?
              AND date(game_date) <= date(?)
            ORDER BY game_date DESC
            LIMIT 5
        '''
    else:  # season
        query = '''
            SELECT *
            FROM team_game_logs
            WHERE team_id = ?
              AND season = ?
              AND date(game_date) >= '2025-10-21'
              AND date(game_date) <= date(?)
            ORDER BY game_date DESC
        '''

    cursor.execute(query, (team_id, season, as_of_date))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        logger.warning(f"[opponent_resistance] No games found for team {team_id} in {window}")
        return None

    # Convert to list of dicts
    games = [dict(row) for row in rows]

    # Calculate aggregates
    total_possessions = 0
    total_to = 0
    total_oreb = 0
    total_opp_dreb = 0
    total_fta = 0
    total_fga = 0
    total_empty = 0

    for game in games:
        poss = game.get('possessions', _calculate_possessions(game, fta_coefficient))
        total_possessions += poss
        total_to += game['turnovers']
        total_oreb += game['offensive_rebounds']
        total_opp_dreb += game['opp_defensive_rebounds']
        total_fta += game['fta']
        total_fga += game['fga']
        total_empty += _calculate_empty_possessions(game)

    # Calculate rates
    avg_possessions = total_possessions / len(games)
    to_pct = (total_to / total_possessions * 100) if total_possessions > 0 else 0
    oreb_pct = (total_oreb / (total_oreb + total_opp_dreb) * 100) if (total_oreb + total_opp_dreb) > 0 else 0
    ftr = (total_fta / total_fga * 100) if total_fga > 0 else 0
    avg_empty = total_empty / len(games)
    empty_rate = (total_empty / total_possessions * 100) if total_possessions > 0 else 0

    return {
        'team_id': team_id,
        'games_count': len(games),
        'avg_possessions': round(avg_possessions, 2),
        'to_pct': round(to_pct, 2),
        'oreb_pct': round(oreb_pct, 2),
        'ftr': round(ftr, 2),
        'avg_empty_possessions': round(avg_empty, 2),
        'empty_rate': round(empty_rate, 2),
    }


def get_opponent_resistance(
    team_id: int,
    season: str = '2025-26',
    as_of_date: str = '2026-01-02',
    window: str = 'season'
) -> Dict:
    """
    Get opponent resistance metrics (how opponents perform AGAINST this team)

    This measures defensive pressure from the team's perspective:
    - How often do opponents turn it over when playing this team?
    - How often do opponents get offensive rebounds against this team?
    - How often do opponents get to the FT line against this team?

    Args:
        team_id: NBA team ID (the defense)
        season: Season string
        as_of_date: Calculate metrics up to this date
        window: 'season' or 'last5'

    Returns:
        {
            'team_id': int,
            'games_count': int,
            'opp_forces_to_pct': float,  # Opponent TO% when playing this team
            'opp_oreb_allowed_pct': float,  # Opponent OREB% when playing this team
            'opp_ftr_allowed': float,  # Opponent FTr when playing this team
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Same query as team identity but we'll use opponent stats
    if window == 'last5':
        query = '''
            SELECT *
            FROM team_game_logs
            WHERE team_id = ?
              AND season = ?
              AND date(game_date) <= date(?)
            ORDER BY game_date DESC
            LIMIT 5
        '''
    else:  # season
        query = '''
            SELECT *
            FROM team_game_logs
            WHERE team_id = ?
              AND season = ?
              AND date(game_date) >= '2025-10-21'
              AND date(game_date) <= date(?)
            ORDER BY game_date DESC
        '''

    cursor.execute(query, (team_id, season, as_of_date))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        logger.warning(f"[opponent_resistance] No games found for team {team_id} in {window}")
        return None

    games = [dict(row) for row in rows]

    # Calculate opponent performance against this team
    total_opp_possessions = 0
    total_opp_to = 0
    total_opp_oreb = 0
    total_team_dreb = 0  # This team's DREB (for opponent OREB% calc)
    total_opp_fta = 0
    total_opp_fga = 0

    for game in games:
        opp_poss = game.get('opp_possessions', 0)
        total_opp_possessions += opp_poss
        total_opp_to += game['opp_turnovers']
        total_opp_oreb += game['opp_offensive_rebounds']
        total_team_dreb += game['defensive_rebounds']
        total_opp_fta += game['opp_fta']
        total_opp_fga += game['opp_fga']

    # Calculate resistance rates (from opponent perspective)
    opp_forces_to_pct = (total_opp_to / total_opp_possessions * 100) if total_opp_possessions > 0 else 0
    opp_oreb_allowed_pct = (total_opp_oreb / (total_opp_oreb + total_team_dreb) * 100) if (total_opp_oreb + total_team_dreb) > 0 else 0
    opp_ftr_allowed = (total_opp_fta / total_opp_fga * 100) if total_opp_fga > 0 else 0

    return {
        'team_id': team_id,
        'games_count': len(games),
        'opp_forces_to_pct': round(opp_forces_to_pct, 2),
        'opp_oreb_allowed_pct': round(opp_oreb_allowed_pct, 2),
        'opp_ftr_allowed': round(opp_ftr_allowed, 2),
    }


def compute_expected_empty(
    team_identity: Dict,
    opp_resistance: Dict,
    expected_to_pct: float,
    expected_oreb_pct: float,
    mode: str = 'index'
) -> Dict:
    """
    Compute expected empty possessions metric

    Mode 'index': Returns z-scored index (0-100 scaled)
    Mode 'estimate': Returns estimated empty possessions count

    Args:
        team_identity: Team identity metrics dict
        opp_resistance: Opponent resistance metrics dict
        expected_to_pct: Blended TO%
        expected_oreb_pct: Blended OREB%
        mode: 'index' or 'estimate'

    Returns:
        {
            'expected_empty_index': float (0-100),
            'expected_to_delta': float,  # How much TO% changes from identity
            'expected_oreb_delta': float,  # How much OREB% changes from identity
        }
    """
    # Calculate deltas from team identity
    to_delta = expected_to_pct - team_identity['to_pct']
    oreb_delta = expected_oreb_pct - team_identity['oreb_pct']

    if mode == 'index':
        # Simple index: Higher TO% = more empty, Lower OREB% = more empty
        # Normalize to 0-100 scale
        empty_pressure = 50 + (to_delta * 2) - (oreb_delta * 2)
        empty_pressure = max(0, min(100, empty_pressure))  # Clamp to 0-100

        return {
            'expected_empty_index': round(empty_pressure, 1),
            'expected_to_delta': round(to_delta, 2),
            'expected_oreb_delta': round(oreb_delta, 2),
        }
    else:  # 'estimate' mode
        # Estimate change in empty possessions
        avg_possessions = team_identity['avg_possessions']
        avg_empty = team_identity['avg_empty_possessions']

        # Adjust empty possessions based on deltas
        to_impact = (to_delta / 100) * avg_possessions  # Additional TOs
        oreb_impact = (oreb_delta / 100) * team_identity['oreb_pct'] / 100 * avg_possessions  # Lost OREBs

        expected_empty = avg_empty + to_impact - oreb_impact

        return {
            'expected_empty_possessions': round(expected_empty, 1),
            'expected_to_delta': round(to_delta, 2),
            'expected_oreb_delta': round(oreb_delta, 2),
        }


def get_expected_matchup_metrics(
    team_id: int,
    opp_id: int,
    season: str = '2025-26',
    as_of_date: str = '2026-01-02'
) -> Dict:
    """
    Calculate expected matchup metrics by blending team identity with opponent resistance

    Returns metrics for both season and last5 windows

    Args:
        team_id: Team A's ID
        opp_id: Team B's ID (opponent)
        season: Season string
        as_of_date: Calculate metrics up to this date

    Returns:
        {
            'team': {
                'season': { identity + expected metrics },
                'last5': { identity + expected metrics }
            },
            'opp': {
                'season': { identity + expected metrics },
                'last5': { identity + expected metrics }
            },
            'expected': {
                'team_expected_to_pct_season': float,
                'team_expected_oreb_pct_season': float,
                'team_expected_empty_index_season': float,
                'opp_expected_to_pct_season': float,
                'opp_expected_oreb_pct_season': float,
                'opp_expected_empty_index_season': float,
                'empty_edge_index_season': float,  # team - opp
                'team_expected_to_pct_last5': float,
                'team_expected_oreb_pct_last5': float,
                'team_expected_empty_index_last5': float,
                'opp_expected_to_pct_last5': float,
                'opp_expected_oreb_pct_last5': float,
                'opp_expected_empty_index_last5': float,
                'empty_edge_index_last5': float,  # team - opp
            }
        }
    """
    # Load learned coefficients
    try:
        from api.utils.coefficient_learner import get_active_coefficients
        coeffs = get_active_coefficients(season)
        fta_coefficient = coeffs['fta_coefficient']
        blend_weight_team = coeffs['blend_weight_team']
        blend_weight_opp = coeffs['blend_weight_opp']
        logger.info(f"[opponent_resistance] Using learned coefficients: FTA={fta_coefficient:.4f}, Blend={blend_weight_team:.2f}/{blend_weight_opp:.2f}")
    except (ImportError, ValueError, KeyError) as e:
        logger.warning(f"[opponent_resistance] Could not load learned coefficients: {e}. Using defaults.")
        fta_coefficient = 0.44
        blend_weight_team = 0.5
        blend_weight_opp = 0.5

    # Get all metrics for both windows (pass fta_coefficient)
    team_identity_season = get_team_identity(team_id, season, as_of_date, 'season', fta_coefficient)
    team_identity_last5 = get_team_identity(team_id, season, as_of_date, 'last5', fta_coefficient)
    opp_identity_season = get_team_identity(opp_id, season, as_of_date, 'season', fta_coefficient)
    opp_identity_last5 = get_team_identity(opp_id, season, as_of_date, 'last5', fta_coefficient)

    # Get opponent resistance (from defensive perspective)
    team_resistance_season = get_opponent_resistance(team_id, season, as_of_date, 'season')
    team_resistance_last5 = get_opponent_resistance(team_id, season, as_of_date, 'last5')
    opp_resistance_season = get_opponent_resistance(opp_id, season, as_of_date, 'season')
    opp_resistance_last5 = get_opponent_resistance(opp_id, season, as_of_date, 'last5')

    if not all([team_identity_season, team_identity_last5, opp_identity_season, opp_identity_last5,
                team_resistance_season, team_resistance_last5, opp_resistance_season, opp_resistance_last5]):
        logger.error(f"[opponent_resistance] Missing data for matchup {team_id} vs {opp_id}")
        return None

    # === SEASON WINDOW ===
    # Team A expected metrics (blend team A identity with team B resistance using learned weights)
    team_expected_to_season = (blend_weight_team * team_identity_season['to_pct'] +
                                blend_weight_opp * opp_resistance_season['opp_forces_to_pct'])
    team_expected_oreb_season = (blend_weight_team * team_identity_season['oreb_pct'] +
                                  blend_weight_opp * opp_resistance_season['opp_oreb_allowed_pct'])
    team_expected_ftr_season = (blend_weight_team * team_identity_season['ftr'] +
                                 blend_weight_opp * opp_resistance_season['opp_ftr_allowed'])
    team_expected_ftr_delta_season = team_expected_ftr_season - team_identity_season['ftr']

    team_empty_season = compute_expected_empty(
        team_identity_season,
        opp_resistance_season,
        team_expected_to_season,
        team_expected_oreb_season,
        mode='index'
    )

    # Team B expected metrics (blend team B identity with team A resistance using learned weights)
    opp_expected_to_season = (blend_weight_team * opp_identity_season['to_pct'] +
                               blend_weight_opp * team_resistance_season['opp_forces_to_pct'])
    opp_expected_oreb_season = (blend_weight_team * opp_identity_season['oreb_pct'] +
                                 blend_weight_opp * team_resistance_season['opp_oreb_allowed_pct'])
    opp_expected_ftr_season = (blend_weight_team * opp_identity_season['ftr'] +
                                blend_weight_opp * team_resistance_season['opp_ftr_allowed'])
    opp_expected_ftr_delta_season = opp_expected_ftr_season - opp_identity_season['ftr']

    opp_empty_season = compute_expected_empty(
        opp_identity_season,
        team_resistance_season,
        opp_expected_to_season,
        opp_expected_oreb_season,
        mode='index'
    )

    # === LAST5 WINDOW ===
    team_expected_to_last5 = (blend_weight_team * team_identity_last5['to_pct'] +
                               blend_weight_opp * opp_resistance_last5['opp_forces_to_pct'])
    team_expected_oreb_last5 = (blend_weight_team * team_identity_last5['oreb_pct'] +
                                 blend_weight_opp * opp_resistance_last5['opp_oreb_allowed_pct'])
    team_expected_ftr_last5 = (blend_weight_team * team_identity_last5['ftr'] +
                                blend_weight_opp * opp_resistance_last5['opp_ftr_allowed'])
    team_expected_ftr_delta_last5 = team_expected_ftr_last5 - team_identity_last5['ftr']

    team_empty_last5 = compute_expected_empty(
        team_identity_last5,
        opp_resistance_last5,
        team_expected_to_last5,
        team_expected_oreb_last5,
        mode='index'
    )

    opp_expected_to_last5 = (blend_weight_team * opp_identity_last5['to_pct'] +
                              blend_weight_opp * team_resistance_last5['opp_forces_to_pct'])
    opp_expected_oreb_last5 = (blend_weight_team * opp_identity_last5['oreb_pct'] +
                                blend_weight_opp * team_resistance_last5['opp_oreb_allowed_pct'])
    opp_expected_ftr_last5 = (blend_weight_team * opp_identity_last5['ftr'] +
                               blend_weight_opp * team_resistance_last5['opp_ftr_allowed'])
    opp_expected_ftr_delta_last5 = opp_expected_ftr_last5 - opp_identity_last5['ftr']

    opp_empty_last5 = compute_expected_empty(
        opp_identity_last5,
        team_resistance_last5,
        opp_expected_to_last5,
        opp_expected_oreb_last5,
        mode='index'
    )

    # Calculate empty edge (positive = team has advantage)
    empty_edge_season = team_empty_season['expected_empty_index'] - opp_empty_season['expected_empty_index']
    empty_edge_last5 = team_empty_last5['expected_empty_index'] - opp_empty_last5['expected_empty_index']

    return {
        'team': {
            'season': {
                **team_identity_season,
                'expected_to_pct': round(team_expected_to_season, 2),
                'expected_oreb_pct': round(team_expected_oreb_season, 2),
                'expected_ftr': round(team_expected_ftr_season, 2),
                'expected_ftr_delta': round(team_expected_ftr_delta_season, 2),
                **team_empty_season,
            },
            'last5': {
                **team_identity_last5,
                'expected_to_pct': round(team_expected_to_last5, 2),
                'expected_oreb_pct': round(team_expected_oreb_last5, 2),
                'expected_ftr': round(team_expected_ftr_last5, 2),
                'expected_ftr_delta': round(team_expected_ftr_delta_last5, 2),
                **team_empty_last5,
            }
        },
        'opp': {
            'season': {
                **opp_identity_season,
                'expected_to_pct': round(opp_expected_to_season, 2),
                'expected_oreb_pct': round(opp_expected_oreb_season, 2),
                'expected_ftr': round(opp_expected_ftr_season, 2),
                'expected_ftr_delta': round(opp_expected_ftr_delta_season, 2),
                **opp_empty_season,
            },
            'last5': {
                **opp_identity_last5,
                'expected_to_pct': round(opp_expected_to_last5, 2),
                'expected_oreb_pct': round(opp_expected_oreb_last5, 2),
                'expected_ftr': round(opp_expected_ftr_last5, 2),
                'expected_ftr_delta': round(opp_expected_ftr_delta_last5, 2),
                **opp_empty_last5,
            }
        },
        'expected': {
            'team_expected_to_pct_season': round(team_expected_to_season, 2),
            'team_expected_oreb_pct_season': round(team_expected_oreb_season, 2),
            'team_expected_empty_index_season': team_empty_season['expected_empty_index'],
            'opp_expected_to_pct_season': round(opp_expected_to_season, 2),
            'opp_expected_oreb_pct_season': round(opp_expected_oreb_season, 2),
            'opp_expected_empty_index_season': opp_empty_season['expected_empty_index'],
            'empty_edge_index_season': round(empty_edge_season, 1),
            'team_expected_to_pct_last5': round(team_expected_to_last5, 2),
            'team_expected_oreb_pct_last5': round(team_expected_oreb_last5, 2),
            'team_expected_empty_index_last5': team_empty_last5['expected_empty_index'],
            'opp_expected_to_pct_last5': round(opp_expected_to_last5, 2),
            'opp_expected_oreb_pct_last5': round(opp_expected_oreb_last5, 2),
            'opp_expected_empty_index_last5': opp_empty_last5['expected_empty_index'],
            'empty_edge_index_last5': round(empty_edge_last5, 1),
        }
    }


def calculate_pregame_projections(
    team_identity: Dict,
    opp_identity: Dict,
    expected_metrics: Dict
) -> Dict:
    """
    Calculate pregame possession count projections

    Translates rates and expected changes into actual possession counts
    for pregame analysis.

    Args:
        team_identity: Home team's season identity metrics
        opp_identity: Away team's season identity metrics
        expected_metrics: Expected matchup metrics from get_expected_matchup_metrics()

    Returns:
        {
            'projected_game_possessions': float,
            'home_projected_team_possessions': float,
            'away_projected_team_possessions': float,
            'home_expected_empty_possessions': float,
            'away_expected_empty_possessions': float,
            'home_expected_scoring_possessions': float,
            'away_expected_scoring_possessions': float,
            'expected_empty_possessions_game': float,
            'expected_empty_rate': float,
            'league_avg_empty_rate': float
        }
    """
    # Get team avg possessions from identity
    home_poss = team_identity['avg_possessions']
    away_poss = opp_identity['avg_possessions']
    game_poss = home_poss + away_poss

    # Calculate expected empty possessions using TO and OREB deltas
    home_to_delta = expected_metrics['team_expected_to_pct_season'] - team_identity['to_pct']
    home_oreb_delta = expected_metrics['team_expected_oreb_pct_season'] - team_identity['oreb_pct']

    # Translate deltas to possession counts
    # TO impact: additional turnovers create more empty possessions
    home_empty_from_to = home_poss * (home_to_delta / 100)

    # OREB impact: fewer OREBs = more empty possessions (negative delta means fewer empties)
    # Using 0.55 misses per possession as temporary placeholder
    MISSES_PER_POSSESSION = 0.55
    home_empty_from_oreb = -(home_poss * MISSES_PER_POSSESSION * (home_oreb_delta / 100))

    # Base empty possessions + adjustments
    home_baseline_empty = (team_identity['empty_rate'] / 100) * home_poss
    home_expected_empty = home_baseline_empty + home_empty_from_to + home_empty_from_oreb

    # Same for away team
    away_to_delta = expected_metrics['opp_expected_to_pct_season'] - opp_identity['to_pct']
    away_oreb_delta = expected_metrics['opp_expected_oreb_pct_season'] - opp_identity['oreb_pct']
    away_empty_from_to = away_poss * (away_to_delta / 100)
    away_empty_from_oreb = -(away_poss * MISSES_PER_POSSESSION * (away_oreb_delta / 100))
    away_baseline_empty = (opp_identity['empty_rate'] / 100) * away_poss
    away_expected_empty = away_baseline_empty + away_empty_from_to + away_empty_from_oreb

    # Game totals
    game_expected_empty = home_expected_empty + away_expected_empty
    game_empty_rate = (game_expected_empty / game_poss) * 100

    # League average (calculate from season data - placeholder for now)
    league_avg_empty_rate = 42.0  # TODO: Calculate from actual season data

    return {
        'projected_game_possessions': round(game_poss, 1),
        'home_projected_team_possessions': round(home_poss, 1),
        'away_projected_team_possessions': round(away_poss, 1),
        'home_expected_empty_possessions': round(home_expected_empty, 1),
        'away_expected_empty_possessions': round(away_expected_empty, 1),
        'home_expected_scoring_possessions': round(home_poss - home_expected_empty, 1),
        'away_expected_scoring_possessions': round(away_poss - away_expected_empty, 1),
        'expected_empty_possessions_game': round(game_expected_empty, 1),
        'expected_empty_rate': round(game_empty_rate, 1),
        'league_avg_empty_rate': league_avg_empty_rate
    }
