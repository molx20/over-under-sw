"""
Team Profile Classifier Module

Classifies teams into behavioral tiers using deterministic rules and maps
those tiers to numerical prediction weights.

All logic is rule-based with fixed constants - no machine learning.
"""

import sqlite3
import statistics
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ============================================================================
# TUNABLE CONSTANTS - All classification thresholds in one place
# ============================================================================

# Pace Classification (std deviations from mean)
PACE_SLOW_THRESHOLD = 0.75   # Below this = slow
PACE_FAST_THRESHOLD = 0.75   # Above this = fast

# Variance Classification (std deviations from mean)
VARIANCE_LOW_THRESHOLD = 0.5    # Below this = low (steady)
VARIANCE_HIGH_THRESHOLD = 0.5   # Above this = high (swingy)

# Home/Away Classification (absolute PPG difference)
HOME_AWAY_POINT_THRESHOLD = 4.0  # Difference to be considered home/road strong

# Matchup Sensitivity Classification (PPG delta vs elite/bad defenses)
MATCHUP_LOW_THRESHOLD = 3.0    # Below this = low sensitivity
MATCHUP_HIGH_THRESHOLD = 6.0   # Above this = high sensitivity

# Minimum games required for classification
MIN_GAMES_FOR_PROFILE = 5
MIN_GAMES_FOR_MATCHUP = 3  # Per bucket (elite/bad defenses)

# Defense tier boundaries (by rank)
ELITE_DEFENSE_RANK_MAX = 10
BAD_DEFENSE_RANK_MIN = 21

# ============================================================================
# WEIGHT PRESETS - Tier labels → numerical weights
# ============================================================================

VARIANCE_WEIGHTS = {
    'low':    {'season': 0.70, 'recent': 0.30},  # Steady teams trust season
    'medium': {'season': 0.55, 'recent': 0.45},
    'high':   {'season': 0.40, 'recent': 0.60},  # Swingy teams trust recent
}

PACE_WEIGHTS = {
    'slow':   0.8,   # Reduce pace impact for slow teams
    'medium': 1.0,   # Neutral
    'fast':   1.2,   # Amplify pace impact for fast teams
}

MATCHUP_WEIGHTS = {
    'low':    0.8,   # Less responsive to opponent defense
    'medium': 1.0,   # Neutral
    'high':   1.2,   # More responsive to opponent defense
}

HOME_AWAY_WEIGHTS = {
    'neutral':      0.5,  # Neutral home/away impact
    'home_strong':  1.0,  # Full home court advantage
    'road_strong':  1.0,  # Full road advantage (inverted)
}


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def compute_league_references(cursor: sqlite3.Cursor, season: str) -> Optional[Dict]:
    """
    Compute league-wide reference statistics (means and standard deviations)

    Args:
        cursor: SQLite cursor
        season: Season string

    Returns:
        Dict with pace_mean, pace_std, points_cv_mean, points_cv_std
        or None if insufficient data
    """
    # Get pace stats from all teams
    cursor.execute('''
        SELECT pace
        FROM team_season_stats
        WHERE season = ? AND split_type = 'overall' AND pace IS NOT NULL
    ''', (season,))

    pace_values = [row[0] for row in cursor.fetchall()]

    if len(pace_values) < 10:  # Need at least 10 teams
        logger.warning(f"Insufficient pace data for league references ({len(pace_values)} teams)")
        return None

    pace_mean = statistics.mean(pace_values)
    pace_std = statistics.stdev(pace_values) if len(pace_values) > 1 else 1.0

    # Get points coefficient of variation for all teams
    # We need to calculate this from game logs
    cursor.execute('''
        SELECT team_id
        FROM team_season_stats
        WHERE season = ? AND split_type = 'overall'
    ''', (season,))

    team_ids = [row[0] for row in cursor.fetchall()]
    cv_values = []

    for team_id in team_ids:
        cursor.execute('''
            SELECT team_pts
            FROM team_game_logs
            WHERE team_id = ? AND season = ? AND team_pts IS NOT NULL
        ''', (team_id, season))

        points = [row[0] for row in cursor.fetchall()]

        if len(points) >= MIN_GAMES_FOR_PROFILE:
            points_mean = statistics.mean(points)
            points_std = statistics.stdev(points) if len(points) > 1 else 0
            if points_mean > 0:
                cv = points_std / points_mean
                cv_values.append(cv)

    if len(cv_values) < 10:
        logger.warning(f"Insufficient variance data for league references ({len(cv_values)} teams)")
        return None

    cv_mean = statistics.mean(cv_values)
    cv_std = statistics.stdev(cv_values) if len(cv_values) > 1 else 0.01

    logger.info(f"League references: pace={pace_mean:.1f}±{pace_std:.1f}, CV={cv_mean:.3f}±{cv_std:.3f}")

    return {
        'pace_mean': pace_mean,
        'pace_std': pace_std,
        'points_cv_mean': cv_mean,
        'points_cv_std': cv_std,
    }


def compute_team_metrics(cursor: sqlite3.Cursor, team_id: int, season: str) -> Optional[Dict]:
    """
    Compute per-team metrics for classification

    Args:
        cursor: SQLite cursor
        team_id: Team ID
        season: Season string

    Returns:
        Dict with pace, points_cv, home_away_diff, matchup_delta
        or None if insufficient data
    """
    # Check if team has enough games
    cursor.execute('''
        SELECT COUNT(*)
        FROM team_game_logs
        WHERE team_id = ? AND season = ?
    ''', (team_id, season))

    game_count = cursor.fetchone()[0]

    if game_count < MIN_GAMES_FOR_PROFILE:
        logger.info(f"Team {team_id} has only {game_count} games, skipping profile")
        return None

    # Get pace from season stats
    cursor.execute('''
        SELECT pace
        FROM team_season_stats
        WHERE team_id = ? AND season = ? AND split_type = 'overall'
    ''', (team_id, season))

    pace_row = cursor.fetchone()
    pace = pace_row[0] if pace_row and pace_row[0] else 100.0

    # Calculate points variance (coefficient of variation)
    cursor.execute('''
        SELECT team_pts
        FROM team_game_logs
        WHERE team_id = ? AND season = ? AND team_pts IS NOT NULL
    ''', (team_id, season))

    points = [row[0] for row in cursor.fetchall()]

    if len(points) < MIN_GAMES_FOR_PROFILE:
        logger.warning(f"Team {team_id} insufficient game points data")
        return None

    points_mean = statistics.mean(points)
    points_std = statistics.stdev(points) if len(points) > 1 else 0
    points_cv = points_std / points_mean if points_mean > 0 else 0

    # Get home/away split
    cursor.execute('''
        SELECT ppg
        FROM team_season_stats
        WHERE team_id = ? AND season = ? AND split_type = 'home'
    ''', (team_id, season))

    home_row = cursor.fetchone()
    home_ppg = home_row[0] if home_row and home_row[0] else None

    cursor.execute('''
        SELECT ppg
        FROM team_season_stats
        WHERE team_id = ? AND season = ? AND split_type = 'away'
    ''', (team_id, season))

    away_row = cursor.fetchone()
    away_ppg = away_row[0] if away_row and away_row[0] else None

    # Calculate home/away difference (use overall PPG if splits missing)
    if home_ppg is not None and away_ppg is not None:
        home_away_diff = home_ppg - away_ppg
    else:
        # Fallback: use overall PPG for both (neutral)
        home_away_diff = 0.0
        logger.info(f"Team {team_id} missing home/away splits, using neutral")

    # Calculate matchup sensitivity (avg vs bad defenses - avg vs elite defenses)
    matchup_delta = _calculate_matchup_delta(cursor, team_id, season)

    matchup_str = f"{matchup_delta:+.1f}" if matchup_delta is not None else "N/A"
    logger.info(
        f"Team {team_id} metrics: pace={pace:.1f}, cv={points_cv:.3f}, "
        f"home_away_diff={home_away_diff:+.1f}, matchup_delta={matchup_str}"
    )

    return {
        'pace': pace,
        'points_cv': points_cv,
        'home_away_diff': home_away_diff,
        'matchup_delta': matchup_delta,
    }


def _calculate_matchup_delta(cursor: sqlite3.Cursor, team_id: int, season: str) -> Optional[float]:
    """
    Calculate matchup sensitivity: PPG vs bad defenses - PPG vs elite defenses

    Returns None if insufficient data (defaults to medium sensitivity)
    """
    # Get points vs elite defenses (ranks 1-10)
    cursor.execute('''
        SELECT tgl.team_pts
        FROM team_game_logs tgl
        LEFT JOIN team_season_stats tss_opp
            ON tgl.opponent_team_id = tss_opp.team_id
            AND tgl.season = tss_opp.season
            AND tss_opp.split_type = 'overall'
        WHERE tgl.team_id = ?
            AND tgl.season = ?
            AND tss_opp.def_rtg_rank IS NOT NULL
            AND tss_opp.def_rtg_rank <= ?
            AND tgl.team_pts IS NOT NULL
    ''', (team_id, season, ELITE_DEFENSE_RANK_MAX))

    elite_games = [row[0] for row in cursor.fetchall()]

    # Get points vs bad defenses (ranks 21-30)
    cursor.execute('''
        SELECT tgl.team_pts
        FROM team_game_logs tgl
        LEFT JOIN team_season_stats tss_opp
            ON tgl.opponent_team_id = tss_opp.team_id
            AND tgl.season = tss_opp.season
            AND tss_opp.split_type = 'overall'
        WHERE tgl.team_id = ?
            AND tgl.season = ?
            AND tss_opp.def_rtg_rank IS NOT NULL
            AND tss_opp.def_rtg_rank >= ?
            AND tgl.team_pts IS NOT NULL
    ''', (team_id, season, BAD_DEFENSE_RANK_MIN))

    bad_games = [row[0] for row in cursor.fetchall()]

    # Check if we have enough games in each bucket
    if len(elite_games) < MIN_GAMES_FOR_MATCHUP or len(bad_games) < MIN_GAMES_FOR_MATCHUP:
        logger.info(
            f"Team {team_id} insufficient matchup data (elite: {len(elite_games)}, bad: {len(bad_games)}), "
            f"defaulting to medium sensitivity"
        )
        return None

    avg_vs_elite = statistics.mean(elite_games)
    avg_vs_bad = statistics.mean(bad_games)
    matchup_delta = avg_vs_bad - avg_vs_elite

    logger.info(
        f"Team {team_id} matchup: vs elite={avg_vs_elite:.1f} ({len(elite_games)} games), "
        f"vs bad={avg_vs_bad:.1f} ({len(bad_games)} games), delta={matchup_delta:+.1f}"
    )

    return matchup_delta


def classify_team(team_metrics: Dict, league_refs: Dict) -> Dict:
    """
    Classify team into tiers based on metrics and league references

    Args:
        team_metrics: Dict with pace, points_cv, home_away_diff, matchup_delta
        league_refs: Dict with pace_mean, pace_std, points_cv_mean, points_cv_std

    Returns:
        Dict with pace_label, variance_label, home_away_label, matchup_label
    """
    # Pace classification
    pace = team_metrics['pace']
    pace_mean = league_refs['pace_mean']
    pace_std = league_refs['pace_std']

    if pace <= pace_mean - (PACE_SLOW_THRESHOLD * pace_std):
        pace_label = 'slow'
    elif pace >= pace_mean + (PACE_FAST_THRESHOLD * pace_std):
        pace_label = 'fast'
    else:
        pace_label = 'medium'

    # Variance classification
    points_cv = team_metrics['points_cv']
    cv_mean = league_refs['points_cv_mean']
    cv_std = league_refs['points_cv_std']

    if points_cv <= cv_mean - (VARIANCE_LOW_THRESHOLD * cv_std):
        variance_label = 'low'
    elif points_cv >= cv_mean + (VARIANCE_HIGH_THRESHOLD * cv_std):
        variance_label = 'high'
    else:
        variance_label = 'medium'

    # Home/Away classification
    home_away_diff = team_metrics['home_away_diff']
    home_away_abs = abs(home_away_diff)

    if home_away_abs < HOME_AWAY_POINT_THRESHOLD:
        home_away_label = 'neutral'
    elif home_away_diff > 0:
        home_away_label = 'home_strong'
    else:
        home_away_label = 'road_strong'

    # Matchup classification
    matchup_delta = team_metrics.get('matchup_delta')

    if matchup_delta is None:
        # Insufficient data - default to medium
        matchup_label = 'medium'
    elif matchup_delta <= MATCHUP_LOW_THRESHOLD:
        matchup_label = 'low'
    elif matchup_delta >= MATCHUP_HIGH_THRESHOLD:
        matchup_label = 'high'
    else:
        matchup_label = 'medium'

    return {
        'pace_label': pace_label,
        'variance_label': variance_label,
        'home_away_label': home_away_label,
        'matchup_label': matchup_label,
    }


def map_tiers_to_weights(tier_labels: Dict) -> Dict:
    """
    Map tier labels to numerical prediction weights

    Args:
        tier_labels: Dict with pace_label, variance_label, home_away_label, matchup_label

    Returns:
        Dict with season_weight, recent_weight, pace_weight, def_weight, home_away_weight
    """
    variance_label = tier_labels['variance_label']
    pace_label = tier_labels['pace_label']
    matchup_label = tier_labels['matchup_label']
    home_away_label = tier_labels['home_away_label']

    # Map variance to season/recent weights
    variance_weights = VARIANCE_WEIGHTS.get(variance_label, VARIANCE_WEIGHTS['medium'])
    season_weight = variance_weights['season']
    recent_weight = variance_weights['recent']

    # Map pace to pace weight
    pace_weight = PACE_WEIGHTS.get(pace_label, 1.0)

    # Map matchup to defense weight
    def_weight = MATCHUP_WEIGHTS.get(matchup_label, 1.0)

    # Map home/away to home court weight
    home_away_weight = HOME_AWAY_WEIGHTS.get(home_away_label, 0.5)

    return {
        'season_weight': season_weight,
        'recent_weight': recent_weight,
        'pace_weight': pace_weight,
        'def_weight': def_weight,
        'home_away_weight': home_away_weight,
    }


def create_team_profile(cursor: sqlite3.Cursor, team_id: int, season: str, league_refs: Dict) -> Optional[Dict]:
    """
    Create complete team profile (metrics → tiers → weights)

    Args:
        cursor: SQLite cursor
        team_id: Team ID
        season: Season string
        league_refs: League reference stats

    Returns:
        Complete profile dict ready for upsert, or None if insufficient data
    """
    # Compute team metrics
    team_metrics = compute_team_metrics(cursor, team_id, season)
    if not team_metrics:
        return None

    # Classify into tiers
    tier_labels = classify_team(team_metrics, league_refs)

    # Map tiers to weights
    weights = map_tiers_to_weights(tier_labels)

    # Combine into complete profile
    profile = {
        'team_id': team_id,
        'season': season,
        'pace_label': tier_labels['pace_label'],
        'variance_label': tier_labels['variance_label'],
        'home_away_label': tier_labels['home_away_label'],
        'matchup_label': tier_labels['matchup_label'],
        'season_weight': weights['season_weight'],
        'recent_weight': weights['recent_weight'],
        'pace_weight': weights['pace_weight'],
        'def_weight': weights['def_weight'],
        'home_away_weight': weights['home_away_weight'],
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        f"Team {team_id} profile: {tier_labels['pace_label']}/{tier_labels['variance_label']}/"
        f"{tier_labels['home_away_label']}/{tier_labels['matchup_label']} → "
        f"pace_w={weights['pace_weight']}, def_w={weights['def_weight']}, "
        f"home_w={weights['home_away_weight']}"
    )

    return profile
