"""
Scoring Breakdown Module

This module provides functions to calculate team scoring projections broken down by type:
- 2-point field goals (FG2)
- 3-point field goals (FG3)
- Free throws (FT)

This replaces the single-metric approach (total PPG) with a more granular model that can
detect matchup-specific advantages (e.g., 3PT-heavy offense vs bad perimeter defense).

Key Functions:
- get_defense_adjusted_scoring_breakdown(): Main query function for scoring by type
- apply_differentiated_pace_adjustment(): Pace affects FG more than FT
- blend_recent_form_by_scoring_type(): 3PT uses lower recency weight (30% vs 50%)
- detect_shootout_and_allocate_bonus(): Shootout bonuses allocated by scoring type
"""

import sqlite3
from typing import Dict, List, Optional, Tuple
import logging

from api.utils.defense_tiers import get_defense_tier
from api.utils.three_pt_defense_tiers import get_3pt_defense_tier, get_3pt_defense_tier_range
from api.utils.db_config import get_db_path

logger = logging.getLogger(__name__)

# Database path
NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def get_defense_adjusted_scoring_breakdown(
    team_id: int,
    opponent_def_rank: Optional[int],
    opponent_3pt_def_rank: Optional[int],
    is_home: bool,
    season: str = '2025-26',
    fallback_ppg: float = 115.0
) -> Dict:
    """
    Get defense-adjusted scoring breakdown (2PT, 3PT, FT) for a team.

    This function queries historical games where the team faced similar defenses
    (both overall and 3PT-specific) to project scoring by type.

    Args:
        team_id: Team ID
        opponent_def_rank: Opponent's overall defensive rank (1-30)
        opponent_3pt_def_rank: Opponent's 3PT defensive rank (1-30)
        is_home: True if home game
        season: Season (e.g., '2025-26')
        fallback_ppg: Fallback total PPG if no data

    Returns:
        {
            'two_pt': {'ppg': float, 'fgm': float, 'fga': float, 'pct': float, 'games': int},
            'three_pt': {'ppg': float, 'fgm': float, 'fga': float, 'pct': float, 'games': int},
            'ft': {'ppg': float, 'ftm': float, 'fta': float, 'pct': float, 'games': int},
            'total_ppg': float,
            'data_quality': str  # 'excellent' (3+ games), 'limited' (1-2 games), 'fallback' (0 games)
        }
    """
    location = 'home' if is_home else 'away'

    # Get defense tiers
    overall_def_tier = get_defense_tier(opponent_def_rank)
    threept_def_tier = get_3pt_defense_tier(opponent_3pt_def_rank)

    if not overall_def_tier:
        logger.warning(f"Invalid opponent_def_rank: {opponent_def_rank}, using fallback")
        return _get_fallback_breakdown(fallback_ppg)

    # If no 3PT defense rank, use overall defense tier as proxy
    if not threept_def_tier:
        logger.info(f"No 3PT defense rank for opponent, using overall tier as proxy")
        threept_def_tier = overall_def_tier

    # Try to get data with both overall and 3PT defense filters
    breakdown = _query_scoring_breakdown_vs_defense_tiers(
        team_id, overall_def_tier, threept_def_tier, is_home, season
    )

    if breakdown and breakdown['two_pt']['games'] >= 3:
        breakdown['data_quality'] = 'excellent'
        logger.info(
            f"Team {team_id} {location} vs {overall_def_tier} def / {threept_def_tier} 3PT def: "
            f"2PT={breakdown['two_pt']['ppg']:.1f}, 3PT={breakdown['three_pt']['ppg']:.1f}, "
            f"FT={breakdown['ft']['ppg']:.1f} ({breakdown['two_pt']['games']} games)"
        )
        return breakdown
    elif breakdown and breakdown['two_pt']['games'] > 0:
        breakdown['data_quality'] = 'limited'
        logger.info(
            f"Team {team_id} {location} vs {overall_def_tier}/{threept_def_tier}: Limited data "
            f"({breakdown['two_pt']['games']} games), will blend with season average"
        )
        return breakdown
    else:
        # No games found - try overall defense tier only
        logger.info(f"No games vs {overall_def_tier}/{threept_def_tier}, trying overall tier only")
        breakdown = _query_scoring_breakdown_vs_defense_tier_only(
            team_id, overall_def_tier, is_home, season
        )

        if breakdown and breakdown['two_pt']['games'] >= 1:
            breakdown['data_quality'] = 'limited'
            return breakdown
        else:
            # Fall back to season average
            logger.info(f"No historical data, using season average breakdown")
            breakdown = _get_season_average_breakdown(team_id, is_home, season)
            if breakdown:
                breakdown['data_quality'] = 'fallback'
                return breakdown
            else:
                # Ultimate fallback: use provided PPG split evenly
                return _get_fallback_breakdown(fallback_ppg)


def _query_scoring_breakdown_vs_defense_tiers(
    team_id: int,
    overall_def_tier: str,
    threept_def_tier: str,
    is_home: bool,
    season: str
) -> Optional[Dict]:
    """Query games vs BOTH overall defense tier AND 3PT defense tier"""
    from api.utils.defense_tiers import get_defense_tier_range

    overall_min, overall_max = get_defense_tier_range(overall_def_tier)
    threept_min, threept_max = get_3pt_defense_tier_range(threept_def_tier)

    conn = sqlite3.connect(NBA_DATA_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            tgl.fg2m, tgl.fg2a, tgl.fg3m, tgl.fg3a, tgl.ftm, tgl.fta
        FROM team_game_logs tgl
        JOIN team_season_stats tss_opp
            ON tgl.opponent_team_id = tss_opp.team_id
            AND tgl.season = tss_opp.season
            AND tss_opp.split_type = 'overall'
        WHERE tgl.team_id = ?
            AND tgl.season = ?
            AND tgl.is_home = ?
            AND tss_opp.def_rtg_rank BETWEEN ? AND ?
            AND tss_opp.opp_fg3_pct_rank BETWEEN ? AND ?
            AND tgl.fg2m IS NOT NULL
            AND tgl.fg3m IS NOT NULL
            AND tgl.ftm IS NOT NULL
    ''', (team_id, season, 1 if is_home else 0, overall_min, overall_max, threept_min, threept_max))

    games = cursor.fetchall()
    conn.close()

    if not games:
        return None

    return _calculate_breakdown_from_games(games)


def _query_scoring_breakdown_vs_defense_tier_only(
    team_id: int,
    overall_def_tier: str,
    is_home: bool,
    season: str
) -> Optional[Dict]:
    """Query games vs overall defense tier only (no 3PT filter)"""
    from api.utils.defense_tiers import get_defense_tier_range

    overall_min, overall_max = get_defense_tier_range(overall_def_tier)

    conn = sqlite3.connect(NBA_DATA_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            tgl.fg2m, tgl.fg2a, tgl.fg3m, tgl.fg3a, tgl.ftm, tgl.fta
        FROM team_game_logs tgl
        JOIN team_season_stats tss_opp
            ON tgl.opponent_team_id = tss_opp.team_id
            AND tgl.season = tss_opp.season
            AND tss_opp.split_type = 'overall'
        WHERE tgl.team_id = ?
            AND tgl.season = ?
            AND tgl.is_home = ?
            AND tss_opp.def_rtg_rank BETWEEN ? AND ?
            AND tgl.fg2m IS NOT NULL
            AND tgl.fg3m IS NOT NULL
            AND tgl.ftm IS NOT NULL
    ''', (team_id, season, 1 if is_home else 0, overall_min, overall_max))

    games = cursor.fetchall()
    conn.close()

    if not games:
        return None

    return _calculate_breakdown_from_games(games)


def _get_season_average_breakdown(
    team_id: int,
    is_home: bool,
    season: str
) -> Optional[Dict]:
    """Get season average scoring breakdown from team_season_stats"""
    split_type = 'home' if is_home else 'away'

    conn = sqlite3.connect(NBA_DATA_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT fg2m, fg2a, fg3m, fg3a, ftm, fta, games_played
        FROM team_season_stats
        WHERE team_id = ? AND season = ? AND split_type = ?
    ''', (team_id, season, split_type))

    row = cursor.fetchone()
    conn.close()

    if not row or not row['fg2m']:
        return None

    return {
        'two_pt': {
            'ppg': float(row['fg2m']) * 2,
            'fgm': float(row['fg2m']),
            'fga': float(row['fg2a']) if row['fg2a'] else 0,
            'pct': (float(row['fg2m']) / float(row['fg2a']) * 100) if row['fg2a'] else 0,
            'games': int(row['games_played'])
        },
        'three_pt': {
            'ppg': float(row['fg3m']) * 3,
            'fgm': float(row['fg3m']),
            'fga': float(row['fg3a']) if row['fg3a'] else 0,
            'pct': (float(row['fg3m']) / float(row['fg3a']) * 100) if row['fg3a'] else 0,
            'games': int(row['games_played'])
        },
        'ft': {
            'ppg': float(row['ftm']),
            'ftm': float(row['ftm']),
            'fta': float(row['fta']) if row['fta'] else 0,
            'pct': (float(row['ftm']) / float(row['fta']) * 100) if row['fta'] else 0,
            'games': int(row['games_played'])
        },
        'total_ppg': float(row['fg2m']) * 2 + float(row['fg3m']) * 3 + float(row['ftm']),
        'data_quality': 'fallback'
    }


def _calculate_breakdown_from_games(games: List[sqlite3.Row]) -> Dict:
    """Calculate average scoring breakdown from list of games"""
    n = len(games)

    avg_fg2m = sum(float(g['fg2m']) if g['fg2m'] is not None else 0 for g in games) / n
    avg_fg2a = sum(float(g['fg2a']) if g['fg2a'] is not None else 0 for g in games) / n
    avg_fg3m = sum(float(g['fg3m']) if g['fg3m'] is not None else 0 for g in games) / n
    avg_fg3a = sum(float(g['fg3a']) if g['fg3a'] is not None else 0 for g in games) / n
    avg_ftm = sum(float(g['ftm']) if g['ftm'] is not None else 0 for g in games) / n
    avg_fta = sum(float(g['fta']) if g['fta'] is not None else 0 for g in games) / n

    return {
        'two_pt': {
            'ppg': avg_fg2m * 2,
            'fgm': avg_fg2m,
            'fga': avg_fg2a,
            'pct': (avg_fg2m / avg_fg2a * 100) if avg_fg2a > 0 else 0,
            'games': n
        },
        'three_pt': {
            'ppg': avg_fg3m * 3,
            'fgm': avg_fg3m,
            'fga': avg_fg3a,
            'pct': (avg_fg3m / avg_fg3a * 100) if avg_fg3a > 0 else 0,
            'games': n
        },
        'ft': {
            'ppg': avg_ftm,
            'ftm': avg_ftm,
            'fta': avg_fta,
            'pct': (avg_ftm / avg_fta * 100) if avg_fta > 0 else 0,
            'games': n
        },
        'total_ppg': (avg_fg2m * 2) + (avg_fg3m * 3) + avg_ftm,
        'data_quality': 'excellent' if n >= 3 else 'limited'
    }


def _get_fallback_breakdown(fallback_ppg: float) -> Dict:
    """
    Create a generic breakdown based on league-average distributions.
    Typical NBA scoring: ~50% from 2PT, ~35% from 3PT, ~15% from FT
    """
    two_pt_ppg = fallback_ppg * 0.50
    three_pt_ppg = fallback_ppg * 0.35
    ft_ppg = fallback_ppg * 0.15

    return {
        'two_pt': {
            'ppg': two_pt_ppg,
            'fgm': two_pt_ppg / 2,
            'fga': (two_pt_ppg / 2) / 0.50,  # Assume 50% FG2
            'pct': 50.0,
            'games': 0
        },
        'three_pt': {
            'ppg': three_pt_ppg,
            'fgm': three_pt_ppg / 3,
            'fga': (three_pt_ppg / 3) / 0.36,  # Assume 36% FG3
            'pct': 36.0,
            'games': 0
        },
        'ft': {
            'ppg': ft_ppg,
            'ftm': ft_ppg,
            'fta': ft_ppg / 0.80,  # Assume 80% FT
            'pct': 80.0,
            'games': 0
        },
        'total_ppg': fallback_ppg,
        'data_quality': 'fallback'
    }


def apply_differentiated_pace_adjustment(
    breakdown: Dict,
    game_pace: float,
    league_avg_pace: float = 100.0
) -> Dict:
    """
    Apply pace adjustments differentiated by scoring type.

    Fast pace = more possessions = more shots (FG2, FG3) but NOT proportionally more fouls.

    Args:
        breakdown: Scoring breakdown dict
        game_pace: Projected game pace (possessions per 48 min)
        league_avg_pace: League average pace (default 100)

    Returns:
        Updated breakdown with pace adjustments applied
    """
    pace_diff = game_pace - league_avg_pace

    # Full pace adjustment for field goals (more possessions = more shots)
    fg_multiplier = 1.0 + (pace_diff / 100.0) * 0.3

    # Reduced pace adjustment for free throws (50% of FG adjustment)
    # Faster pace doesn't necessarily mean more fouls
    ft_multiplier = 1.0 + (pace_diff / 100.0) * 0.15

    # Apply multipliers
    breakdown['two_pt']['ppg'] *= fg_multiplier
    breakdown['two_pt']['fgm'] *= fg_multiplier
    breakdown['two_pt']['fga'] *= fg_multiplier

    breakdown['three_pt']['ppg'] *= fg_multiplier
    breakdown['three_pt']['fgm'] *= fg_multiplier
    breakdown['three_pt']['fga'] *= fg_multiplier

    breakdown['ft']['ppg'] *= ft_multiplier
    breakdown['ft']['ftm'] *= ft_multiplier
    breakdown['ft']['fta'] *= ft_multiplier

    # Update total
    breakdown['total_ppg'] = (
        breakdown['two_pt']['ppg'] +
        breakdown['three_pt']['ppg'] +
        breakdown['ft']['ppg']
    )

    logger.debug(
        f"Pace adjustment (pace={game_pace:.1f}): FG multiplier={fg_multiplier:.3f}, "
        f"FT multiplier={ft_multiplier:.3f}"
    )

    return breakdown


def blend_recent_form_by_scoring_type(
    base_breakdown: Dict,
    recent_games: List[Dict],
    season: str
) -> Dict:
    """
    Blend recent form with base projection, using different weights for each scoring type.

    Weights:
    - 3PT: 30% recent, 70% base (most volatile, don't chase noise)
    - 2PT: 40% recent, 60% base
    - FT: 50% recent, 50% base (most stable)

    Args:
        base_breakdown: Defense-adjusted breakdown
        recent_games: List of recent game dicts (must have fg2m, fg3m, ftm keys)
        season: Season

    Returns:
        Blended breakdown
    """
    if not recent_games:
        return base_breakdown

    # Calculate recent averages
    n = len(recent_games)

    # Check if recent games have breakdown data
    has_breakdown = recent_games[0].get('fg2m') is not None

    if not has_breakdown:
        # Games don't have breakdown yet (forward-only data)
        logger.debug("Recent games missing breakdown data, skipping form blend")
        return base_breakdown

    recent_fg2m = sum(float(g.get('fg2m', 0)) for g in recent_games) / n
    recent_fg3m = sum(float(g.get('fg3m', 0)) for g in recent_games) / n
    recent_ftm = sum(float(g.get('ftm', 0)) for g in recent_games) / n

    recent_2pt_ppg = recent_fg2m * 2
    recent_3pt_ppg = recent_fg3m * 3
    recent_ft_ppg = recent_ftm

    # Blend with different weights
    base_breakdown['two_pt']['ppg'] = (
        base_breakdown['two_pt']['ppg'] * 0.6 + recent_2pt_ppg * 0.4
    )
    base_breakdown['three_pt']['ppg'] = (
        base_breakdown['three_pt']['ppg'] * 0.7 + recent_3pt_ppg * 0.3  # Less weight!
    )
    base_breakdown['ft']['ppg'] = (
        base_breakdown['ft']['ppg'] * 0.5 + recent_ft_ppg * 0.5
    )

    # Update total
    base_breakdown['total_ppg'] = (
        base_breakdown['two_pt']['ppg'] +
        base_breakdown['three_pt']['ppg'] +
        base_breakdown['ft']['ppg']
    )

    logger.debug(
        f"Recent form blend: 2PT={base_breakdown['two_pt']['ppg']:.1f}, "
        f"3PT={base_breakdown['three_pt']['ppg']:.1f}, FT={base_breakdown['ft']['ppg']:.1f}"
    )

    return base_breakdown


def detect_shootout_and_allocate_bonus(
    home_def_tier: Optional[str],
    away_def_tier: Optional[str],
    home_3pt_def_tier: Optional[str],
    away_3pt_def_tier: Optional[str],
    home_breakdown: Dict,
    away_breakdown: Dict
) -> Tuple[Dict, Dict]:
    """
    Detect shootout potential and allocate bonuses by scoring type.

    Bonuses:
    - Both overall defenses bad: +12 pts each, split as (5 to 2PT, 5 to 3PT, 2 to FT)
    - One overall defense bad: +6 pts to team facing bad defense
    - Both 3PT defenses bad: Additional +3 pts to 3PT each

    Args:
        home_def_tier: Home team's defensive tier
        away_def_tier: Away team's defensive tier
        home_3pt_def_tier: Home team's 3PT defensive tier
        away_3pt_def_tier: Away team's 3PT defensive tier
        home_breakdown: Home team scoring breakdown
        away_breakdown: Away team scoring breakdown

    Returns:
        Tuple of (updated_home_breakdown, updated_away_breakdown)
    """
    home_bonus_2pt = 0.0
    home_bonus_3pt = 0.0
    home_bonus_ft = 0.0
    away_bonus_2pt = 0.0
    away_bonus_3pt = 0.0
    away_bonus_ft = 0.0

    # Overall shootout detection
    if home_def_tier == 'bad' and away_def_tier == 'bad':
        # Both defenses bad: major shootout (+12 each)
        home_bonus_2pt += 5.0
        home_bonus_3pt += 5.0
        home_bonus_ft += 2.0
        away_bonus_2pt += 5.0
        away_bonus_3pt += 5.0
        away_bonus_ft += 2.0
        logger.info("Both defenses bad: Major shootout detected (+12 pts each, split by type)")
    elif home_def_tier == 'bad':
        # Away team facing bad defense (+6)
        away_bonus_2pt += 3.0
        away_bonus_3pt += 2.0
        away_bonus_ft += 1.0
        logger.info("Home defense bad: Away team gets +6 pts shootout bonus")
    elif away_def_tier == 'bad':
        # Home team facing bad defense (+6)
        home_bonus_2pt += 3.0
        home_bonus_3pt += 2.0
        home_bonus_ft += 1.0
        logger.info("Away defense bad: Home team gets +6 pts shootout bonus")

    # 3PT shootout detection
    if home_3pt_def_tier == 'bad' and away_3pt_def_tier == 'bad':
        # Both 3PT defenses bad: additional 3PT bonus
        home_bonus_3pt += 3.0
        away_bonus_3pt += 3.0
        logger.info("Both 3PT defenses bad: Additional +3 pts to 3PT each")
    elif home_3pt_def_tier == 'bad':
        away_bonus_3pt += 2.0
        logger.info("Home 3PT defense bad: Away team gets +2 pts 3PT bonus")
    elif away_3pt_def_tier == 'bad':
        home_bonus_3pt += 2.0
        logger.info("Away 3PT defense bad: Home team gets +2 pts 3PT bonus")

    # Apply bonuses
    home_breakdown['two_pt']['ppg'] += home_bonus_2pt
    home_breakdown['three_pt']['ppg'] += home_bonus_3pt
    home_breakdown['ft']['ppg'] += home_bonus_ft

    away_breakdown['two_pt']['ppg'] += away_bonus_2pt
    away_breakdown['three_pt']['ppg'] += away_bonus_3pt
    away_breakdown['ft']['ppg'] += away_bonus_ft

    # Update totals
    home_breakdown['total_ppg'] = (
        home_breakdown['two_pt']['ppg'] +
        home_breakdown['three_pt']['ppg'] +
        home_breakdown['ft']['ppg']
    )
    away_breakdown['total_ppg'] = (
        away_breakdown['two_pt']['ppg'] +
        away_breakdown['three_pt']['ppg'] +
        away_breakdown['ft']['ppg']
    )

    return home_breakdown, away_breakdown
