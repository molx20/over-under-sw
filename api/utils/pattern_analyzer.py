"""
Pattern Analyzer Module

Statistical pattern discovery for 7 research questions:
1. What wins games? (opportunity differential → win rate)
2. Scoring environments (identify FT-driven, rebound-heavy, etc.)
3. Efficiency overrides (conversion rate > possession volume)
4. Opponent context (defensive pressure effects)
5. Data-first archetypes (cluster on TO%, OREB%, FTr ONLY)
6. Prop environments (high assist/rebound/scoring conditions)
7. Failure analysis (games where patterns broke down)

No machine learning - rule-based pattern discovery only.
"""

import pandas as pd
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Import metrics helpers
try:
    from api.utils.possession_metrics import (
        bucket_by_percentile,
        classify_scoring_environment,
        classify_prop_environment,
        identify_failure_games,
        summarize_environment_frequencies,
        calculate_team_archetype_percentiles
    )
except ImportError:
    from possession_metrics import (
        bucket_by_percentile,
        classify_scoring_environment,
        classify_prop_environment,
        identify_failure_games,
        summarize_environment_frequencies,
        calculate_team_archetype_percentiles
    )


def analyze_opportunity_differential_patterns(df: pd.DataFrame) -> Dict:
    """
    Q1: What wins games? Analyze opportunity_diff → win rate correlation.

    Returns:
        Dict with:
            - correlation: Pearson correlation between opportunity_diff and game_win
            - win_rate_by_bucket: Win rate for each quintile of opportunity_diff
            - failure_games: Games where team lost despite opportunity advantage
    """
    try:
        logger.info("[pattern_analyzer] Q1: Analyzing opportunity differential patterns")

        # Calculate correlation
        correlation = df['opportunity_diff'].corr(df['game_win'])

        # Bucket opportunity_diff into quintiles
        df_copy = df.copy()
        df_copy['opp_diff_bucket'] = bucket_by_percentile(df_copy['opportunity_diff'], buckets=5)

        # Calculate win rate per bucket
        win_rate_by_bucket = df_copy.groupby('opp_diff_bucket').agg({
            'game_win': 'mean',
            'game_id': 'count'
        }).round(3)
        win_rate_by_bucket.columns = ['win_rate', 'games']

        # Identify failure games (won opportunity_diff but lost game)
        failure_games = df_copy[
            (df_copy['opportunity_diff'] > 2) & (df_copy['game_win'] == 0)
        ][['game_id', 'team_id', 'opportunity_diff', 'ppp', 'opp_ppp', 'conversion_score']]

        logger.info(f"[pattern_analyzer] Q1: Correlation = {correlation:.3f}, {len(failure_games)} failure games")

        return {
            'correlation': round(correlation, 3),
            'win_rate_by_bucket': win_rate_by_bucket.to_dict('index'),
            'failure_games': failure_games.to_dict('records')
        }

    except Exception as e:
        logger.error(f"[pattern_analyzer] Q1 error: {e}")
        return {}


def analyze_scoring_environments(df: pd.DataFrame) -> Dict:
    """
    Q2: Identify and analyze scoring environments (FT-driven, rebound-heavy, etc.).

    Returns:
        Dict with:
            - frequency: Count per environment
            - avg_ppp: Average PPP per environment
            - avg_pace: Average pace per environment
            - win_rate: Win rate per environment
    """
    try:
        logger.info("[pattern_analyzer] Q2: Analyzing scoring environments")

        # Classify environments
        df_copy = df.copy()
        df_copy['scoring_environment'] = df_copy.apply(classify_scoring_environment, axis=1)

        # Get summary
        environment_summary = summarize_environment_frequencies(df_copy)

        logger.info(f"[pattern_analyzer] Q2: Found {len(environment_summary)} environment types")

        return environment_summary

    except Exception as e:
        logger.error(f"[pattern_analyzer] Q2 error: {e}")
        return {}


def analyze_efficiency_overrides(df: pd.DataFrame) -> Dict:
    """
    Q3: When does conversion rate matter more than possession volume?

    Analyze games where team lost opportunity_diff but won game.

    Returns:
        Dict with:
            - override_games: Games where efficiency overcame volume deficit
            - avg_ppp_advantage: Average PPP advantage in override games
            - avg_conversion_score: Average conversion score in override games
    """
    try:
        logger.info("[pattern_analyzer] Q3: Analyzing efficiency overrides")

        # Filter to games where team won despite losing opportunity_diff
        override_games = df[
            (df['opportunity_diff'] < -1) & (df['game_win'] == 1)
        ].copy()

        if override_games.empty:
            logger.warning("[pattern_analyzer] Q3: No override games found")
            return {
                'override_games': [],
                'avg_ppp_advantage': 0,
                'avg_conversion_score': 0
            }

        # Calculate PPP advantage
        override_games['ppp_advantage'] = override_games['ppp'] - override_games['opp_ppp']

        # Summary stats
        avg_ppp_advantage = override_games['ppp_advantage'].mean()
        avg_conversion_score = override_games['conversion_score'].mean()

        logger.info(f"[pattern_analyzer] Q3: Found {len(override_games)} override games")

        return {
            'override_games': override_games[[
                'game_id', 'team_id', 'opportunity_diff', 'ppp', 'opp_ppp',
                'conversion_score', 'ppp_advantage'
            ]].to_dict('records'),
            'avg_ppp_advantage': round(avg_ppp_advantage, 3),
            'avg_conversion_score': round(avg_conversion_score, 1),
            'total_override_games': len(override_games)
        }

    except Exception as e:
        logger.error(f"[pattern_analyzer] Q3 error: {e}")
        return {}


def analyze_opponent_context_effects(df: pd.DataFrame) -> Dict:
    """
    Q4: How does opponent defensive pressure alter outcomes?

    Analyze:
    - Effect of opponent TO% forcing on team's actual TO%
    - Effect of opponent defensive rebounding on team's OREB%
    - Pace matchup effects (fast vs slow)

    Returns:
        Dict with:
            - to_pressure_effect: Correlation between opp_TO_pct and team TO_pct
            - oreb_pressure_effect: Correlation between opp_OREB_pct and team OREB_pct
            - pace_matchup_bins: Win rate by pace differential buckets
    """
    try:
        logger.info("[pattern_analyzer] Q4: Analyzing opponent context effects")

        # Correlation: Does opponent's defensive pressure affect team's execution?
        to_pressure_corr = df['opp_TO_pct'].corr(df['TO_pct'])
        oreb_pressure_corr = df['opp_OREB_pct'].corr(df['OREB_pct'])

        # Calculate pace differential
        df_copy = df.copy()
        df_copy['pace_diff'] = df_copy['pace'] - df_copy['pace'].median()
        df_copy['pace_matchup_bucket'] = bucket_by_percentile(df_copy['pace_diff'], buckets=3)

        # Win rate by pace matchup
        pace_matchup = df_copy.groupby('pace_matchup_bucket').agg({
            'game_win': 'mean',
            'game_id': 'count',
            'ppp': 'mean'
        }).round(3)
        pace_matchup.columns = ['win_rate', 'games', 'avg_ppp']

        logger.info(f"[pattern_analyzer] Q4: TO pressure corr = {to_pressure_corr:.3f}, OREB pressure corr = {oreb_pressure_corr:.3f}")

        return {
            'to_pressure_effect': round(to_pressure_corr, 3),
            'oreb_pressure_effect': round(oreb_pressure_corr, 3),
            'pace_matchup_bins': pace_matchup.to_dict('index')
        }

    except Exception as e:
        logger.error(f"[pattern_analyzer] Q4 error: {e}")
        return {}


def cluster_by_possession_behavior(df: pd.DataFrame) -> Dict:
    """
    Q5: Data-first archetypes - cluster teams by possession behavior.

    CRITICAL: Cluster ONLY on TO%, OREB%, FTr (NOT pace or PPP).

    Simple percentile-based clustering:
    - High/Med/Low for each metric
    - 27 possible archetypes (3^3)

    Returns:
        Dict with:
            - team_percentiles: Team-level percentiles for TO%, OREB%, FTr
            - archetype_distribution: Count per archetype
            - sample_archetypes: Example teams for top 5 archetypes
    """
    try:
        logger.info("[pattern_analyzer] Q5: Clustering by possession behavior (TO%, OREB%, FTr only)")

        # Calculate team-level percentiles
        team_stats = calculate_team_archetype_percentiles(df)

        if team_stats.empty:
            logger.warning("[pattern_analyzer] Q5: No team stats calculated")
            return {}

        # Simple clustering: High (>66%), Med (33-66%), Low (<33%)
        def percentile_to_label(pct):
            if pct >= 66:
                return 'High'
            elif pct >= 33:
                return 'Med'
            else:
                return 'Low'

        team_stats['TO_label'] = team_stats['TO_pct_percentile'].apply(percentile_to_label)
        team_stats['OREB_label'] = team_stats['OREB_pct_percentile'].apply(percentile_to_label)
        team_stats['FTr_label'] = team_stats['FTr_percentile'].apply(percentile_to_label)

        # Create archetype label
        team_stats['archetype'] = (
            team_stats['TO_label'] + '_TO/' +
            team_stats['OREB_label'] + '_OREB/' +
            team_stats['FTr_label'] + '_FTr'
        )

        # Archetype distribution
        archetype_dist = team_stats['archetype'].value_counts().to_dict()

        # Sample teams for top 5 archetypes
        top_archetypes = team_stats['archetype'].value_counts().head(5).index.tolist()
        sample_archetypes = {}

        for archetype in top_archetypes:
            sample_teams = team_stats[team_stats['archetype'] == archetype][
                ['team_id', 'avg_TO_pct', 'avg_OREB_pct', 'avg_FTr', 'games']
            ].to_dict('records')
            sample_archetypes[archetype] = sample_teams

        logger.info(f"[pattern_analyzer] Q5: Found {len(archetype_dist)} archetypes across {len(team_stats)} teams")

        return {
            'team_percentiles': team_stats.to_dict('records'),
            'archetype_distribution': archetype_dist,
            'sample_archetypes': sample_archetypes
        }

    except Exception as e:
        logger.error(f"[pattern_analyzer] Q5 error: {e}")
        return {}


def identify_prop_environments(df: pd.DataFrame) -> Dict:
    """
    Q6: Identify high assist/rebound/scoring prop environments.

    Returns games meeting thresholds for player prop categories (player-agnostic).

    Returns:
        Dict with:
            - high_scoring_games: Games with pace > 102 AND off_rating > 115
            - high_assist_games: Games with assists > 27
            - high_rebound_games: Games with OREB% > 28
            - multi_prop_games: Games tagged with multiple prop types
    """
    try:
        logger.info("[pattern_analyzer] Q6: Identifying prop environments")

        df_copy = df.copy()

        # Apply prop classification
        df_copy['prop_tags'] = df_copy.apply(classify_prop_environment, axis=1)

        # Extract specific prop types
        high_scoring = df_copy[df_copy['prop_tags'].apply(lambda x: 'High Scoring' in x)][
            ['game_id', 'team_id', 'pace', 'off_rating', 'ppp']
        ]

        high_assist = df_copy[df_copy['prop_tags'].apply(lambda x: 'High Assists' in x)][
            ['game_id', 'team_id', 'assists', 'pace']
        ]

        high_rebound = df_copy[df_copy['prop_tags'].apply(lambda x: 'High Rebounds' in x)][
            ['game_id', 'team_id', 'OREB_pct', 'pace']
        ]

        # Multi-prop games (2+ tags)
        multi_prop = df_copy[df_copy['prop_tags'].apply(lambda x: len(x) >= 2)][
            ['game_id', 'team_id', 'prop_tags', 'pace', 'ppp']
        ]

        logger.info(f"[pattern_analyzer] Q6: High scoring={len(high_scoring)}, Assists={len(high_assist)}, Rebounds={len(high_rebound)}, Multi-prop={len(multi_prop)}")

        return {
            'high_scoring_games': high_scoring.to_dict('records'),
            'high_assist_games': high_assist.to_dict('records'),
            'high_rebound_games': high_rebound.to_dict('records'),
            'multi_prop_games': multi_prop.to_dict('records')
        }

    except Exception as e:
        logger.error(f"[pattern_analyzer] Q6 error: {e}")
        return {}


def analyze_failure_cases(df: pd.DataFrame) -> Dict:
    """
    Q7: Analyze games where possession patterns broke down.

    Identify outliers and expected wins that lost.

    Returns:
        Dict with:
            - failure_games: Games where team had all advantages but lost
            - avg_failure_severity: Average severity score
            - common_patterns: Commonalities among failure games
    """
    try:
        logger.info("[pattern_analyzer] Q7: Analyzing failure cases")

        # Use metrics helper to identify failures
        failure_df = identify_failure_games(df, threshold_pct=100)  # Get all failures

        if failure_df.empty:
            logger.warning("[pattern_analyzer] Q7: No failure games found")
            return {
                'failure_games': [],
                'avg_failure_severity': 0,
                'common_patterns': {}
            }

        # Calculate average severity
        avg_severity = failure_df['failure_severity'].mean()

        # Analyze common patterns in failures
        common_patterns = {}

        # Check if failures cluster in specific environments
        if 'scoring_environment' not in failure_df.columns:
            failure_df['scoring_environment'] = failure_df.apply(classify_scoring_environment, axis=1)

        env_dist = failure_df['scoring_environment'].value_counts().to_dict()
        common_patterns['environment_distribution'] = env_dist

        # Check pace patterns
        common_patterns['avg_pace'] = round(failure_df['pace'].mean(), 1)
        common_patterns['avg_opp_ppp_advantage'] = round(
            (failure_df['opp_ppp'] - failure_df['ppp']).mean(), 3
        )

        logger.info(f"[pattern_analyzer] Q7: Found {len(failure_df)} failure games, avg severity = {avg_severity:.1f}")

        return {
            'failure_games': failure_df[[
                'game_id', 'team_id', 'opportunity_diff', 'conversion_score',
                'ppp', 'opp_ppp', 'failure_severity'
            ]].to_dict('records'),
            'avg_failure_severity': round(avg_severity, 1),
            'common_patterns': common_patterns,
            'total_failures': len(failure_df)
        }

    except Exception as e:
        logger.error(f"[pattern_analyzer] Q7 error: {e}")
        return {}


def run_all_analyses(df: pd.DataFrame) -> Dict:
    """
    Orchestration function to run all 7 pattern analyses.

    Args:
        df: DataFrame from build_possession_dataset()

    Returns:
        Dict with results from all 7 analyses
    """
    try:
        logger.info("[pattern_analyzer] Running all 7 analyses")

        results = {
            'q1_opportunity_differential': analyze_opportunity_differential_patterns(df),
            'q2_scoring_environments': analyze_scoring_environments(df),
            'q3_efficiency_overrides': analyze_efficiency_overrides(df),
            'q4_opponent_context': analyze_opponent_context_effects(df),
            'q5_possession_archetypes': cluster_by_possession_behavior(df),
            'q6_prop_environments': identify_prop_environments(df),
            'q7_failure_analysis': analyze_failure_cases(df)
        }

        logger.info("[pattern_analyzer] All analyses complete")

        return results

    except Exception as e:
        logger.error(f"[pattern_analyzer] Error in run_all_analyses: {e}")
        return {}
