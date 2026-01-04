"""
Possession Metrics Module

Provides bucketing, classification, and efficiency scoring for possession analysis.

Key Functions:
- classify_scoring_environment: Identify dominant game patterns (FT-driven, rebound-heavy, etc.)
- bucket_by_percentile: Classify values into percentile buckets
- calculate_efficiency_override: Detect when conversion beats possession volume
"""

import pandas as pd
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


def bucket_by_percentile(series: pd.Series, buckets: int = 5) -> pd.Series:
    """
    Bucket continuous values into percentile ranges.

    Args:
        series: Pandas series to bucket
        buckets: Number of buckets (default 5 = quintiles)

    Returns:
        Series with bucket labels ('Q1', 'Q2', etc.)

    Example:
        Q1 = 0-20th percentile (bottom quintile)
        Q5 = 80-100th percentile (top quintile)
    """
    try:
        labels = [f'Q{i}' for i in range(1, buckets + 1)]
        return pd.qcut(series, q=buckets, labels=labels, duplicates='drop')
    except Exception as e:
        logger.warning(f"[possession_metrics] Bucketing failed: {e}")
        return pd.Series(['Unknown'] * len(series), index=series.index)


def classify_scoring_environment(row: pd.Series) -> str:
    """
    Identify dominant scoring pattern for a game.

    Classification hierarchy (first match wins):
    1. FT-driven: FTr > 30
    2. Rebound-heavy: OREB% > 30
    3. Assist-heavy: Assists > 25
    4. Grind: Pace < 96
    5. Shootout: Pace > 103
    6. Balanced: None of above

    Args:
        row: DataFrame row with FTr, OREB_pct, assists, pace

    Returns:
        Environment label string
    """
    try:
        # Extract metrics (handle None values)
        ftr = row.get('FTr', 0) or 0
        oreb_pct = row.get('OREB_pct', 0) or 0
        assists = row.get('assists', 0) or 0
        pace = row.get('pace', 100) or 100

        # Hierarchical classification
        if ftr > 30:
            return 'FT-driven'
        elif oreb_pct > 30:
            return 'Rebound-heavy'
        elif assists > 25:
            return 'Assist-heavy'
        elif pace < 96:
            return 'Grind'
        elif pace > 103:
            return 'Shootout'
        else:
            return 'Balanced'

    except Exception as e:
        logger.warning(f"[possession_metrics] Classification error: {e}")
        return 'Unknown'


def classify_prop_environment(row: pd.Series) -> List[str]:
    """
    Identify favorable prop betting conditions (multi-label).

    Tags games that meet thresholds for player prop categories:
    - High Scoring: Pace > 102 AND (off_rating > 115 OR def_rating > 115)
    - High Assists: Assists > 27
    - High Rebounds: OREB% > 28 OR (pace > 100 AND OREB% > 25)
    - High FT Volume: FTr > 28

    Args:
        row: DataFrame row with pace, off_rating, def_rating, assists, OREB_pct, FTr

    Returns:
        List of environment tags (can be multiple or empty)
    """
    tags = []

    try:
        pace = row.get('pace', 0) or 0
        off_rating = row.get('off_rating', 0) or 0
        def_rating = row.get('def_rating', 0) or 0
        assists = row.get('assists', 0) or 0
        oreb_pct = row.get('OREB_pct', 0) or 0
        ftr = row.get('FTr', 0) or 0

        # High scoring conditions
        if pace > 102 and (off_rating > 115 or def_rating > 115):
            tags.append('High Scoring')

        # High assists
        if assists > 27:
            tags.append('High Assists')

        # High rebounds
        if oreb_pct > 28 or (pace > 100 and oreb_pct > 25):
            tags.append('High Rebounds')

        # High FT volume
        if ftr > 28:
            tags.append('High FT Volume')

    except Exception as e:
        logger.warning(f"[possession_metrics] Prop classification error: {e}")

    return tags


def calculate_efficiency_override_score(row: pd.Series) -> Optional[float]:
    """
    Calculate score representing how much efficiency compensates for opportunity deficit.

    Use case: Team loses opportunity_diff but wins game due to superior conversion.

    Formula:
    - Base score: conversion_score (0-100)
    - Bonus: +20 if ppp > opp_ppp by > 0.10
    - Penalty: -10 if opportunity_diff < -3 (significant deficit)

    Args:
        row: DataFrame row with conversion_score, ppp, opp_ppp, opportunity_diff

    Returns:
        Override score (higher = efficiency matters more than volume)
    """
    try:
        conversion_score = row.get('conversion_score', 50) or 50
        ppp = row.get('ppp', 1.0) or 1.0
        opp_ppp = row.get('opp_ppp', 1.0) or 1.0
        opportunity_diff = row.get('opportunity_diff', 0) or 0

        score = conversion_score

        # Bonus for significant PPP advantage
        if (ppp - opp_ppp) > 0.10:
            score += 20

        # Penalty for large opportunity deficit
        if opportunity_diff < -3:
            score -= 10

        return round(score, 1)

    except Exception as e:
        logger.warning(f"[possession_metrics] Override score error: {e}")
        return None


def identify_failure_games(df: pd.DataFrame, threshold_pct: float = 20) -> pd.DataFrame:
    """
    Identify games where possession patterns "broke down" (unexpected losses).

    Failure criteria (team lost game despite):
    1. Won opportunity_diff by > 2
    2. Had conversion_score > 60 (above average)
    3. Had ppp advantage > 0.05

    Args:
        df: DataFrame with possession metrics
        threshold_pct: Return top N% of failure games by severity

    Returns:
        DataFrame of failure games sorted by severity
    """
    try:
        # Filter to losses only
        losses = df[df['game_win'] == 0].copy()

        # Identify failures
        losses['is_failure'] = (
            (losses['opportunity_diff'] > 2) &
            (losses['conversion_score'] > 60) &
            ((losses['ppp'] - losses['opp_ppp']) > 0.05)
        )

        failures = losses[losses['is_failure']].copy()

        if failures.empty:
            logger.info("[possession_metrics] No failure games found")
            return failures

        # Calculate severity score (higher = more unexpected)
        failures['failure_severity'] = (
            (failures['opportunity_diff'] * 2) +
            (failures['conversion_score'] - 50) +
            ((failures['ppp'] - failures['opp_ppp']) * 50)
        )

        # Return top threshold% by severity
        n_games = max(1, int(len(failures) * (threshold_pct / 100)))
        failures_sorted = failures.sort_values('failure_severity', ascending=False).head(n_games)

        logger.info(f"[possession_metrics] Found {len(failures)} total failures, returning top {n_games}")

        return failures_sorted

    except Exception as e:
        logger.error(f"[possession_metrics] Error identifying failure games: {e}")
        return pd.DataFrame()


def add_percentile_buckets(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """
    Add percentile bucket columns to DataFrame.

    For each column in `columns`, creates a new column `{column}_bucket`
    with quintile labels (Q1-Q5).

    Args:
        df: DataFrame to augment
        columns: List of column names to bucket

    Returns:
        DataFrame with added bucket columns
    """
    df_copy = df.copy()

    for col in columns:
        if col in df_copy.columns:
            bucket_col = f'{col}_bucket'
            df_copy[bucket_col] = bucket_by_percentile(df_copy[col])
            logger.info(f"[possession_metrics] Added {bucket_col}")
        else:
            logger.warning(f"[possession_metrics] Column {col} not found, skipping bucketing")

    return df_copy


def summarize_environment_frequencies(df: pd.DataFrame) -> Dict:
    """
    Calculate frequency distribution of scoring environments.

    Args:
        df: DataFrame with 'scoring_environment' column

    Returns:
        Dict with:
            - frequencies: Count per environment
            - avg_ppp: Average PPP per environment
            - avg_pace: Average pace per environment
    """
    try:
        if 'scoring_environment' not in df.columns:
            # Add environment classification if missing
            df['scoring_environment'] = df.apply(classify_scoring_environment, axis=1)

        summary = df.groupby('scoring_environment').agg({
            'game_id': 'count',
            'ppp': 'mean',
            'pace': 'mean',
            'game_win': 'mean'  # Win rate per environment
        }).round(3)

        summary.columns = ['count', 'avg_ppp', 'avg_pace', 'win_rate']
        summary = summary.sort_values('count', ascending=False)

        logger.info(f"[possession_metrics] Environment summary:\n{summary}")

        return summary.to_dict('index')

    except Exception as e:
        logger.error(f"[possession_metrics] Error summarizing environments: {e}")
        return {}


def calculate_team_archetype_percentiles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate team-level percentiles for possession behavior clustering.

    CRITICAL: Cluster ONLY on TO%, OREB%, FTr (NOT pace or PPP).

    Args:
        df: DataFrame with team_id and core levers

    Returns:
        DataFrame with team-level percentiles for TO_pct, OREB_pct, FTr
    """
    try:
        # Group by team
        team_stats = df.groupby('team_id').agg({
            'TO_pct': 'mean',
            'OREB_pct': 'mean',
            'FTr': 'mean',
            'game_id': 'count'  # Games played
        }).reset_index()

        team_stats.columns = ['team_id', 'avg_TO_pct', 'avg_OREB_pct', 'avg_FTr', 'games']

        # Calculate percentiles (0-100 scale)
        team_stats['TO_pct_percentile'] = team_stats['avg_TO_pct'].rank(pct=True) * 100
        team_stats['OREB_pct_percentile'] = team_stats['avg_OREB_pct'].rank(pct=True) * 100
        team_stats['FTr_percentile'] = team_stats['avg_FTr'].rank(pct=True) * 100

        # Round
        team_stats = team_stats.round(2)

        logger.info(f"[possession_metrics] Calculated percentiles for {len(team_stats)} teams")

        return team_stats

    except Exception as e:
        logger.error(f"[possession_metrics] Error calculating team percentiles: {e}")
        return pd.DataFrame()
