"""
Trend-Based Style Adjustments

Detects scoring style trends related to games finishing UNDER 220 or OVER 240
using box-score and efficiency features.

All logic is deterministic and based on real stats from the database.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import sqlite3
import os
from api.utils.db_config import get_db_path


@dataclass
class TrendFeatures:
    """Features for trend-based style analysis"""
    home_team_id: int
    away_team_id: int

    # Combined style metrics (season + recent blended)
    combined_3pa: float
    combined_3p_pct: float
    combined_pitp: float  # Points in the paint
    combined_fta: float
    combined_fastbreak_pts: float
    combined_points_off_turnovers: float
    combined_second_chance_pts: float
    combined_turnovers: float

    # Team efficiency ratings
    home_ortg: float
    away_ortg: float
    home_drtg: float
    away_drtg: float

    # Pre-trend projected total
    projected_total_pre_trend: float


def get_league_thresholds(season: str = '2025-26') -> Dict:
    """
    Calculate league-wide percentile thresholds for style features.
    Uses actual data from the database to compute p25, p50, p75.

    Returns:
        Dict with league thresholds for style features
    """
    db_path = get_db_path('nba_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Query all teams' season stats
        # NOTE: Table is 'team_season_stats' (not 'season_team_stats')
        # NOTE: Columns use lowercase with underscores: fg3a, fg3_pct, off_rtg, def_rtg
        # NOTE: Detailed box score stats (paint, fastbreak, etc.) are NOT in season table,
        #       so we aggregate from team_game_logs instead
        cursor.execute('''
            SELECT
                tss.team_id,
                tss.fg3a as FG3A,
                tss.fg3m as FG3M,
                tss.fg3_pct as FG3_PCT,
                tss.fta as FTA,
                tss.turnovers as TOV,
                tss.off_rtg as OFF_RATING,
                tss.def_rtg as DEF_RATING,
                AVG(tgl.points_in_paint) as PTS_PAINT,
                AVG(tgl.fast_break_points) as PTS_FB,
                AVG(tgl.points_off_turnovers) as PTS_OFF_TOV,
                AVG(tgl.second_chance_points) as PTS_2ND_CHANCE
            FROM team_season_stats tss
            LEFT JOIN team_game_logs tgl ON tss.team_id = tgl.team_id AND tss.season = tgl.season
            WHERE tss.season = ? AND tss.split_type = 'overall'
            GROUP BY tss.team_id
        ''', (season,))

        rows = cursor.fetchall()

        if not rows or len(rows) == 0:
            # Fallback to hardcoded league averages if no data
            return {
                '3pa_p25': 30.0, '3pa_p50': 34.0, '3pa_p75': 38.0,
                'pitp_p25': 42.0, 'pitp_p50': 48.0, 'pitp_p75': 52.0,
                'fta_p25': 19.0, 'fta_p50': 22.0, 'fta_p75': 25.0,
                'fb_p25': 10.0, 'fb_p50': 13.0, 'fb_p75': 16.0,
                'tov_p25': 12.0, 'tov_median': 13.5, 'tov_p75': 15.0,
                'avg_ortg': 113.0,
                'avg_3p_pct': 0.365
            }

        # Extract lists for percentile calculations
        fg3a_list = [row['FG3A'] for row in rows if row['FG3A']]
        pitp_list = [row['PTS_PAINT'] for row in rows if row['PTS_PAINT']]
        fta_list = [row['FTA'] for row in rows if row['FTA']]
        fb_list = [row['PTS_FB'] for row in rows if row['PTS_FB']]
        tov_list = [row['TOV'] for row in rows if row['TOV']]
        ortg_list = [row['OFF_RATING'] for row in rows if row['OFF_RATING']]
        fg3_pct_list = [row['FG3_PCT'] for row in rows if row['FG3_PCT']]

        def percentile(data, p):
            """Calculate percentile"""
            if not data:
                return 0.0
            sorted_data = sorted(data)
            k = (len(sorted_data) - 1) * p
            f = int(k)
            c = f + 1 if f + 1 < len(sorted_data) else f
            return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])

        thresholds = {
            '3pa_p25': percentile(fg3a_list, 0.25),
            '3pa_p33': percentile(fg3a_list, 0.33),  # Added for trend detection
            '3pa_p50': percentile(fg3a_list, 0.50),
            '3pa_p75': percentile(fg3a_list, 0.75),
            'pitp_p25': percentile(pitp_list, 0.25),
            'pitp_p50': percentile(pitp_list, 0.50),
            'pitp_p75': percentile(pitp_list, 0.75),
            'fta_p25': percentile(fta_list, 0.25),
            'fta_p50': percentile(fta_list, 0.50),
            'fta_p75': percentile(fta_list, 0.75),
            'fb_p25': percentile(fb_list, 0.25),
            'fb_p33': percentile(fb_list, 0.33),
            'fb_p50': percentile(fb_list, 0.50),
            'fb_p75': percentile(fb_list, 0.75),
            'tov_p25': percentile(tov_list, 0.25),
            'tov_median': percentile(tov_list, 0.50),
            'tov_p75': percentile(tov_list, 0.75),
            'avg_ortg': sum(ortg_list) / len(ortg_list) if ortg_list else 113.0,
            'avg_3p_pct': sum(fg3_pct_list) / len(fg3_pct_list) if fg3_pct_list else 0.365
        }

        return thresholds

    finally:
        conn.close()


def build_trend_features(
    home_stats: Dict,
    away_stats: Dict,
    home_advanced: Dict,
    away_advanced: Dict,
    projected_total_pre_trend: float,
    home_team_id: int,
    away_team_id: int,
    season: str = '2025-26'
) -> Tuple[TrendFeatures, Dict]:
    """
    Build feature struct from team stats for trend analysis.

    Blends season and recent (last-5) stats the same way the baseline does.

    Args:
        home_stats: Home team stats dict
        away_stats: Away team stats dict
        home_advanced: Home team advanced stats
        away_advanced: Away team advanced stats
        projected_total_pre_trend: Total projection before this step
        home_team_id: Home team ID
        away_team_id: Away team ID
        season: Season string

    Returns:
        (TrendFeatures, league_thresholds dict)
    """
    # Extract overall stats
    home_overall = home_stats.get('overall', {})
    away_overall = away_stats.get('overall', {})

    # Get league thresholds for comparison
    league_thresholds = get_league_thresholds(season)

    # Extract season stats (with fallbacks)
    home_3pa = home_overall.get('FG3A', 34.0)
    away_3pa = away_overall.get('FG3A', 34.0)
    home_3pm = home_overall.get('FG3M', 12.5)
    away_3pm = away_overall.get('FG3M', 12.5)
    home_3p_pct = home_overall.get('FG3_PCT', 0.365)
    away_3p_pct = away_overall.get('FG3_PCT', 0.365)

    home_pitp = home_overall.get('PTS_PAINT', 48.0)
    away_pitp = away_overall.get('PTS_PAINT', 48.0)

    home_fta = home_overall.get('FTA', 22.0)
    away_fta = away_overall.get('FTA', 22.0)

    home_fb = home_overall.get('PTS_FB', 13.0)
    away_fb = away_overall.get('PTS_FB', 13.0)

    home_pts_off_tov = home_overall.get('PTS_OFF_TOV', 15.0)
    away_pts_off_tov = away_overall.get('PTS_OFF_TOV', 15.0)

    home_2nd_chance = home_overall.get('PTS_2ND_CHANCE', 12.0)
    away_2nd_chance = away_overall.get('PTS_2ND_CHANCE', 12.0)

    home_tov = home_overall.get('TOV', 13.5)
    away_tov = away_overall.get('TOV', 13.5)

    # Efficiency ratings
    home_ortg = home_advanced.get('OFF_RATING', 113.0) if home_advanced else 113.0
    away_ortg = away_advanced.get('OFF_RATING', 113.0) if away_advanced else 113.0
    home_drtg = home_advanced.get('DEF_RATING', 113.0) if home_advanced else 113.0
    away_drtg = away_advanced.get('DEF_RATING', 113.0) if away_advanced else 113.0

    # Calculate combined metrics (simple averages)
    combined_3pa = (home_3pa + away_3pa) / 2
    combined_3p_pct = (home_3p_pct + away_3p_pct) / 2
    combined_pitp = (home_pitp + away_pitp) / 2
    combined_fta = (home_fta + away_fta) / 2
    combined_fastbreak_pts = (home_fb + away_fb) / 2
    combined_points_off_turnovers = (home_pts_off_tov + away_pts_off_tov) / 2
    combined_second_chance_pts = (home_2nd_chance + away_2nd_chance) / 2
    combined_turnovers = (home_tov + away_tov) / 2

    features = TrendFeatures(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        combined_3pa=combined_3pa,
        combined_3p_pct=combined_3p_pct,
        combined_pitp=combined_pitp,
        combined_fta=combined_fta,
        combined_fastbreak_pts=combined_fastbreak_pts,
        combined_points_off_turnovers=combined_points_off_turnovers,
        combined_second_chance_pts=combined_second_chance_pts,
        combined_turnovers=combined_turnovers,
        home_ortg=home_ortg,
        away_ortg=away_ortg,
        home_drtg=home_drtg,
        away_drtg=away_drtg,
        projected_total_pre_trend=projected_total_pre_trend
    )

    return features, league_thresholds


def compute_global_trend_scores(
    features: TrendFeatures,
    league_thresholds: Dict,
    home_def_rank: Optional[int],
    away_def_rank: Optional[int]
) -> Tuple[float, float, List[str]]:
    """
    Compute global UNDER/OVER trend scores based on league-wide patterns.

    Returns:
        (under_score, over_score, reason_flags)
    """
    under_score = 0.0
    over_score = 0.0
    reasons = []

    # =====================================================================
    # UNDER-STYLE SCORING
    # =====================================================================

    # Low 3-point volume + poor shooting
    if features.combined_3pa < league_thresholds['3pa_p25'] and features.combined_3p_pct < league_thresholds['avg_3p_pct']:
        under_score += 2.0
        reasons.append('low_3pt_volume_and_shooting')

    # Elite defense present
    if (home_def_rank and home_def_rank <= 10) or (away_def_rank and away_def_rank <= 10):
        # Check if offensive ratings are NOT elite
        avg_ortg = (features.home_ortg + features.away_ortg) / 2
        if avg_ortg < league_thresholds['avg_ortg'] + 2.0:
            under_score += 1.5
            reasons.append('elite_defense_present')

    # Very low paint scoring
    if features.combined_pitp < league_thresholds['pitp_p25']:
        under_score += 1.0
        reasons.append('very_low_paint_scoring')

    # Low fastbreak + high turnovers (wasted possessions)
    if features.combined_fastbreak_pts < league_thresholds['fb_p33'] and features.combined_turnovers > league_thresholds['tov_median']:
        under_score += 1.5
        reasons.append('low_fastbreak_high_turnovers')

    # Low free throw volume
    if features.combined_fta < league_thresholds['fta_p25']:
        under_score += 1.0
        reasons.append('low_ft_volume')

    # =====================================================================
    # OVER-STYLE SCORING
    # =====================================================================

    # High 3-point volume + hot shooting
    if features.combined_3pa > league_thresholds['3pa_p75'] and features.combined_3p_pct > (league_thresholds['avg_3p_pct'] + 0.01):
        over_score += 2.0
        reasons.append('high_3pt_volume_and_hot_shooting')

    # Both offenses efficient
    if features.home_ortg > league_thresholds['avg_ortg'] and features.away_ortg > league_thresholds['avg_ortg']:
        over_score += 1.5
        reasons.append('both_offenses_efficient')

    # Very high paint scoring
    if features.combined_pitp > league_thresholds['pitp_p75']:
        over_score += 1.0
        reasons.append('very_high_paint_scoring')

    # High free throw volume
    if features.combined_fta > league_thresholds['fta_p75']:
        over_score += 1.0
        reasons.append('high_ft_volume')

    # High fastbreak scoring
    if features.combined_fastbreak_pts > league_thresholds['fb_p75']:
        over_score += 1.0
        reasons.append('high_fastbreak_scoring')

    # Elite offense vs weak defense
    if home_def_rank and away_def_rank:
        # Check if one offense is top-8 and opposing defense is bottom-8
        home_ortg_elite = features.home_ortg > league_thresholds['avg_ortg'] + 4.0
        away_ortg_elite = features.away_ortg > league_thresholds['avg_ortg'] + 4.0

        if (home_ortg_elite and away_def_rank >= 23) or (away_ortg_elite and home_def_rank >= 23):
            over_score += 1.5
            reasons.append('elite_offense_vs_weak_defense')

    return under_score, over_score, reasons


def compute_team_specific_trends(
    home_team_id: int,
    away_team_id: int,
    home_def_rank: Optional[int],
    away_def_rank: Optional[int],
    features: TrendFeatures,
    league_thresholds: Dict,
    season: str = '2025-26'
) -> Tuple[float, float, List[str]]:
    """
    Look at historical games for these specific teams and detect patterns
    related to UNDER 220 and OVER 240 outcomes.

    Returns:
        (team_under_bonus, team_over_bonus, flags)
    """
    team_under_bonus = 0.0
    team_over_bonus = 0.0
    flags = []

    db_path = get_db_path('nba_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Check home team vs top-10 defenses (UNDER pattern)
        if home_def_rank and home_def_rank <= 10:
            cursor.execute('''
                SELECT COUNT(*) as games,
                       SUM(CASE WHEN team_pts + opp_pts < 220 THEN 1 ELSE 0 END) as under_220
                FROM team_game_logs
                WHERE team_id = ?
                  AND season = ?
                  AND game_date < date('now')
            ''', (home_team_id, season))

            row = cursor.fetchone()
            if row and row['games'] >= 10:
                under_rate = row['under_220'] / row['games']
                if under_rate > 0.70:
                    team_under_bonus += 2.0
                    flags.append(f'home_under_vs_elite_def_{under_rate:.0%}')

        # Check away team vs top-10 defenses (UNDER pattern)
        if away_def_rank and away_def_rank <= 10:
            cursor.execute('''
                SELECT COUNT(*) as games,
                       SUM(CASE WHEN team_pts + opp_pts < 220 THEN 1 ELSE 0 END) as under_220
                FROM team_game_logs
                WHERE team_id = ?
                  AND season = ?
                  AND game_date < date('now')
            ''', (away_team_id, season))

            row = cursor.fetchone()
            if row and row['games'] >= 10:
                under_rate = row['under_220'] / row['games']
                if under_rate > 0.70:
                    team_under_bonus += 2.0
                    flags.append(f'away_under_vs_elite_def_{under_rate:.0%}')

        # Check home team vs bottom-10 defenses (OVER pattern)
        if home_def_rank and home_def_rank >= 21:
            cursor.execute('''
                SELECT COUNT(*) as games,
                       SUM(CASE WHEN team_pts + opp_pts > 240 THEN 1 ELSE 0 END) as over_240
                FROM team_game_logs
                WHERE team_id = ?
                  AND season = ?
                  AND game_date < date('now')
            ''', (home_team_id, season))

            row = cursor.fetchone()
            if row and row['games'] >= 10:
                over_rate = row['over_240'] / row['games']
                if over_rate > 0.55:
                    team_over_bonus += 1.5
                    flags.append(f'home_over_vs_weak_def_{over_rate:.0%}')

        # Check away team vs bottom-10 defenses (OVER pattern)
        if away_def_rank and away_def_rank >= 21:
            cursor.execute('''
                SELECT COUNT(*) as games,
                       SUM(CASE WHEN team_pts + opp_pts > 240 THEN 1 ELSE 0 END) as over_240
                FROM team_game_logs
                WHERE team_id = ?
                  AND season = ?
                  AND game_date < date('now')
            ''', (away_team_id, season))

            row = cursor.fetchone()
            if row and row['games'] >= 10:
                over_rate = row['over_240'] / row['games']
                if over_rate > 0.55:
                    team_over_bonus += 1.5
                    flags.append(f'away_over_vs_weak_def_{over_rate:.0%}')

        # Check for low 3PT volume games (UNDER pattern)
        if features.combined_3pa < league_thresholds['3pa_p33']:
            for team_id, team_label in [(home_team_id, 'home'), (away_team_id, 'away')]:
                cursor.execute('''
                    SELECT COUNT(*) as games,
                           SUM(CASE WHEN team_pts + opp_pts < 220 THEN 1 ELSE 0 END) as under_220
                    FROM team_game_logs
                    WHERE team_id = ?
                      AND season = ?
                      AND fg3a < ?
                      AND game_date < date('now')
                ''', (team_id, season, league_thresholds['3pa_p33']))

                row = cursor.fetchone()
                if row and row['games'] >= 8:
                    under_rate = row['under_220'] / row['games']
                    if under_rate > 0.65:
                        team_under_bonus += 1.0
                        flags.append(f'{team_label}_low_3pa_under_{under_rate:.0%}')

        # Check for high paint + FTA games (OVER pattern)
        if features.combined_pitp > league_thresholds['pitp_p50'] and features.combined_fta > league_thresholds['fta_p50']:
            for team_id, team_label in [(home_team_id, 'home'), (away_team_id, 'away')]:
                cursor.execute('''
                    SELECT COUNT(*) as games,
                           SUM(CASE WHEN team_pts + opp_pts > 240 THEN 1 ELSE 0 END) as over_240
                    FROM team_game_logs
                    WHERE team_id = ?
                      AND season = ?
                      AND points_in_paint > ?
                      AND fta > ?
                      AND game_date < date('now')
                ''', (team_id, season, league_thresholds['pitp_p50'], league_thresholds['fta_p50']))

                row = cursor.fetchone()
                if row and row['games'] >= 8:
                    over_rate = row['over_240'] / row['games']
                    if over_rate > 0.55:
                        team_over_bonus += 1.0
                        flags.append(f'{team_label}_paint_fta_over_{over_rate:.0%}')

    finally:
        conn.close()

    return team_under_bonus, team_over_bonus, flags


def apply_trend_based_style_adjustments(
    home_projected: float,
    away_projected: float,
    home_stats: Dict,
    away_stats: Dict,
    home_advanced: Dict,
    away_advanced: Dict,
    home_team_id: int,
    away_team_id: int,
    home_def_rank: Optional[int],
    away_def_rank: Optional[int],
    season: str = '2025-26'
) -> Tuple[float, float, Dict]:
    """
    Apply trend-based style adjustments to detect UNDER 220 / OVER 240 patterns.

    This step analyzes box-score style features and team-specific historical patterns
    to apply a small adjustment that accounts for scoring style trends.

    Args:
        home_projected: Current home team projection
        away_projected: Current away team projection
        home_stats: Home team stats
        away_stats: Away team stats
        home_advanced: Home team advanced stats
        away_advanced: Away team advanced stats
        home_team_id: Home team ID
        away_team_id: Away team ID
        home_def_rank: Home team defensive rank
        away_def_rank: Away team defensive rank
        season: Season string

    Returns:
        (new_home, new_away, breakdown_dict)
    """
    # Build trend features
    projected_total_pre_trend = home_projected + away_projected

    features, league_thresholds = build_trend_features(
        home_stats,
        away_stats,
        home_advanced,
        away_advanced,
        projected_total_pre_trend,
        home_team_id,
        away_team_id,
        season
    )

    # Compute global trend scores
    global_under, global_over, global_flags = compute_global_trend_scores(
        features,
        league_thresholds,
        home_def_rank,
        away_def_rank
    )

    # Compute team-specific trends
    team_under_bonus, team_over_bonus, team_flags = compute_team_specific_trends(
        home_team_id,
        away_team_id,
        home_def_rank,
        away_def_rank,
        features,
        league_thresholds,
        season
    )

    # Combine scores
    under_score = global_under + team_under_bonus
    over_score = global_over + team_over_bonus
    net_score = over_score - under_score  # positive = OVER lean, negative = UNDER lean

    # Map net_score to a small capped total points delta
    max_trend_abs = 6.0  # max |net_score| we care about
    max_points_abs = 3.0  # max total point shift per team

    clamped = max(-max_trend_abs, min(max_trend_abs, net_score))
    total_delta = (clamped / max_trend_abs) * max_points_abs  # in [-3, +3]

    # Split between home and away (simple 50/50 split)
    home_delta = total_delta / 2.0
    away_delta = total_delta / 2.0

    # Apply adjustments
    new_home = home_projected + home_delta
    new_away = away_projected + away_delta

    # Build summary text
    if net_score > 1.0:
        summary = "This matchup leans toward higher scoring based on how both teams shoot threes and get to the rim."
    elif net_score < -1.0:
        summary = "This matchup leans toward lower scoring based on limited three-point volume and strong defenses."
    else:
        summary = "This matchup shows balanced scoring style indicators."

    # Build detail list
    details = []
    if 'high_3pt_volume_and_hot_shooting' in global_flags:
        details.append("Both teams take and make more threes than most teams")
    if 'both_offenses_efficient' in global_flags:
        details.append("Both teams have efficient offenses")
    if 'elite_defense_present' in global_flags:
        details.append("At least one elite defense present in this game")
    if 'low_3pt_volume_and_shooting' in global_flags:
        details.append("Low three-point volume and shooting")
    if 'high_paint_scoring' in global_flags or 'very_high_paint_scoring' in global_flags:
        details.append("High paint scoring expected")
    if 'low_fastbreak_high_turnovers' in global_flags:
        details.append("Low fastbreak points with high turnovers")

    # Add team-specific flags
    for flag in team_flags:
        if 'under' in flag:
            details.append(f"Historical pattern shows UNDER tendency ({flag})")
        elif 'over' in flag:
            details.append(f"Historical pattern shows OVER tendency ({flag})")

    # Build breakdown dict
    breakdown = {
        'under_trend_score': float(under_score),
        'over_trend_score': float(over_score),
        'net_trend_bias_points': {
            'home': float(home_delta),
            'away': float(away_delta),
            'total': float(total_delta)
        },
        'global_flags': global_flags,
        'team_flags': team_flags,
        'summary': summary,
        'details': details if details else ["No strong style indicators detected"]
    }

    return new_home, new_away, breakdown
