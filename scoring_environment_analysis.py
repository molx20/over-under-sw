"""
NBA Scoring Environment Analysis
Classifies games into extreme high, extreme low, and mid-range scoring environments
and identifies the statistical DNA of each.
"""

import sqlite3
import pandas as pd
import numpy as np
from collections import defaultdict

DB_PATH = "api/data/nba_data.db"

def get_completed_games():
    """Extract all completed games with full stats from both teams."""
    conn = sqlite3.connect(DB_PATH)

    # Get all game data with stats from both teams
    query = """
    WITH game_totals AS (
        SELECT
            g.id as game_id,
            g.game_date,
            g.season,
            g.home_score,
            g.away_score,
            g.actual_total_points,
            g.game_pace,

            -- Home team stats
            h.team_id as home_team_id,
            h.pace as home_pace,
            h.off_rating as home_ortg,
            h.def_rating as home_drtg,
            h.fg3a as home_fg3a,
            h.fg3m as home_fg3m,
            h.fg3_pct as home_fg3_pct,
            h.fta as home_fta,
            h.ftm as home_ftm,
            h.turnovers as home_tov,
            h.assists as home_ast,
            h.possessions as home_poss,

            -- Away team stats
            a.team_id as away_team_id,
            a.pace as away_pace,
            a.off_rating as away_ortg,
            a.def_rating as away_drtg,
            a.fg3a as away_fg3a,
            a.fg3m as away_fg3m,
            a.fg3_pct as away_fg3_pct,
            a.fta as away_fta,
            a.ftm as away_ftm,
            a.turnovers as away_tov,
            a.assists as away_ast,
            a.possessions as away_poss

        FROM games g
        JOIN team_game_logs h ON g.id = h.game_id AND g.home_team_id = h.team_id
        JOIN team_game_logs a ON g.id = a.game_id AND g.away_team_id = a.team_id
        WHERE g.actual_total_points IS NOT NULL
        AND h.pace IS NOT NULL
        AND a.pace IS NOT NULL
    )
    SELECT * FROM game_totals
    ORDER BY game_date DESC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df

def get_season_averages(df):
    """Calculate season-level averages for comparison."""
    return {
        'pace': df['home_pace'].mean(),  # Approximate league pace
        'ortg': pd.concat([df['home_ortg'], df['away_ortg']]).mean(),
        'drtg': pd.concat([df['home_drtg'], df['away_drtg']]).mean(),
        'fg3a': pd.concat([df['home_fg3a'], df['away_fg3a']]).mean(),
        'fta': pd.concat([df['home_fta'], df['away_fta']]).mean(),
    }

def classify_games(df):
    """Classify games into three scoring buckets."""
    df['scoring_bucket'] = pd.cut(
        df['actual_total_points'],
        bins=[0, 220, 239, 1000],
        labels=['EXTREME_LOW', 'MID_RANGE', 'EXTREME_HIGH'],
        include_lowest=True
    )
    return df

def calculate_combined_stats(df):
    """Calculate combined team statistics for each game."""
    df['combined_pace'] = (df['home_pace'] + df['away_pace']) / 2
    df['combined_ortg'] = (df['home_ortg'] + df['away_ortg']) / 2
    df['combined_drtg'] = (df['home_drtg'] + df['away_drtg']) / 2
    df['combined_fg3a'] = df['home_fg3a'] + df['away_fg3a']
    df['combined_fg3m'] = df['home_fg3m'] + df['away_fg3m']
    df['combined_fg3_pct'] = df['combined_fg3m'] / df['combined_fg3a'].replace(0, np.nan)
    df['combined_fta'] = df['home_fta'] + df['away_fta']
    df['combined_ftm'] = df['home_ftm'] + df['away_ftm']
    df['combined_tov'] = df['home_tov'] + df['away_tov']
    df['combined_ast'] = df['home_ast'] + df['away_ast']
    df['combined_poss'] = (df['home_poss'] + df['away_poss']) / 2

    # Calculate efficiency metrics
    df['ortg_vs_drtg_diff'] = df['combined_ortg'] - df['combined_drtg']
    df['points_per_poss'] = df['actual_total_points'] / df['combined_poss']

    # Turnover rate (per 100 possessions)
    df['tov_rate'] = (df['combined_tov'] / df['combined_poss']) * 100
    df['ast_to_tov'] = df['combined_ast'] / df['combined_tov'].replace(0, np.nan)

    return df

def analyze_bucket(df_bucket, bucket_name, season_avg):
    """Perform comprehensive statistical analysis on a scoring bucket."""
    n = len(df_bucket)

    analysis = {
        'bucket': bucket_name,
        'game_count': n,
        'total_range': f"{df_bucket['actual_total_points'].min()}-{df_bucket['actual_total_points'].max()}",

        # TEMPO METRICS
        'avg_pace': df_bucket['combined_pace'].mean(),
        'pace_vs_season': df_bucket['combined_pace'].mean() - season_avg['pace'],
        'pct_both_teams_fast': (
            ((df_bucket['home_pace'] > season_avg['pace']) &
             (df_bucket['away_pace'] > season_avg['pace'])).sum() / n * 100
        ),
        'pace_std': df_bucket['combined_pace'].std(),

        # EFFICIENCY METRICS
        'avg_combined_ortg': df_bucket['combined_ortg'].mean(),
        'avg_combined_drtg': df_bucket['combined_drtg'].mean(),
        'avg_ortg_vs_drtg': df_bucket['ortg_vs_drtg_diff'].mean(),
        'avg_points_per_poss': df_bucket['points_per_poss'].mean(),
        'ortg_vs_season': df_bucket['combined_ortg'].mean() - season_avg['ortg'],

        # SHOT PROFILE
        'avg_combined_3pa': df_bucket['combined_fg3a'].mean(),
        'avg_combined_3pm': df_bucket['combined_fg3m'].mean(),
        'avg_combined_3p_pct': df_bucket['combined_fg3_pct'].mean() * 100,
        'three_pa_vs_season': df_bucket['combined_fg3a'].mean() - (2 * season_avg['fg3a']),

        # FREE THROWS
        'avg_combined_fta': df_bucket['combined_fta'].mean(),
        'avg_combined_ftm': df_bucket['combined_ftm'].mean(),
        'fta_vs_season': df_bucket['combined_fta'].mean() - (2 * season_avg['fta']),

        # BALL CONTROL
        'avg_tov_rate': df_bucket['tov_rate'].mean(),
        'avg_ast_to_tov': df_bucket['ast_to_tov'].mean(),
        'avg_combined_tov': df_bucket['combined_tov'].mean(),
        'avg_combined_ast': df_bucket['combined_ast'].mean(),

        # VARIANCE
        'total_points_std': df_bucket['actual_total_points'].std(),
    }

    return analysis

def identify_thresholds(df, bucket_name, percentile=75):
    """Identify key statistical thresholds that define each bucket."""
    df_bucket = df[df['scoring_bucket'] == bucket_name]

    thresholds = {
        'pace_threshold': df_bucket['combined_pace'].quantile(percentile/100),
        'ortg_threshold': df_bucket['combined_ortg'].quantile(percentile/100),
        'fg3a_threshold': df_bucket['combined_fg3a'].quantile(percentile/100),
        'fta_threshold': df_bucket['combined_fta'].quantile(percentile/100),
        'points_per_poss_threshold': df_bucket['points_per_poss'].quantile(percentile/100),
    }

    return thresholds

def format_analysis_report(analyses, thresholds_dict, df):
    """Format the analysis into a readable report."""

    report = []
    report.append("=" * 80)
    report.append("NBA SCORING ENVIRONMENT ANALYSIS")
    report.append("=" * 80)
    report.append(f"\nTotal Games Analyzed: {len(df)}")
    report.append("\n" + "=" * 80)

    bucket_order = ['EXTREME_HIGH', 'MID_RANGE', 'EXTREME_LOW']
    bucket_labels = {
        'EXTREME_HIGH': 'EXTREME HIGH SCORING (≥240 Points)',
        'MID_RANGE': 'MID-RANGE SCORING (221-239 Points)',
        'EXTREME_LOW': 'EXTREME LOW SCORING (≤220 Points)'
    }

    for bucket_name in bucket_order:
        analysis = next((a for a in analyses if a['bucket'] == bucket_name), None)
        if not analysis:
            continue

        thresholds = thresholds_dict[bucket_name]

        report.append(f"\n\n{'=' * 80}")
        report.append(f"{bucket_labels[bucket_name]}")
        report.append(f"{'=' * 80}")
        report.append(f"\nGames: {analysis['game_count']} ({analysis['game_count']/len(df)*100:.1f}% of total)")
        report.append(f"Total Points Range: {analysis['total_range']}")
        report.append(f"Standard Deviation: {analysis['total_points_std']:.1f} points")

        report.append(f"\n{'-' * 40}")
        report.append("TEMPO PROFILE")
        report.append(f"{'-' * 40}")
        report.append(f"Average Combined Pace: {analysis['avg_pace']:.2f}")
        report.append(f"Pace vs Season Average: {analysis['pace_vs_season']:+.2f}")
        report.append(f"Both Teams Above Avg Pace: {analysis['pct_both_teams_fast']:.1f}%")
        report.append(f"Pace Volatility (Std Dev): {analysis['pace_std']:.2f}")
        report.append(f"75th Percentile Pace: {thresholds['pace_threshold']:.2f}")

        report.append(f"\n{'-' * 40}")
        report.append("EFFICIENCY PROFILE")
        report.append(f"{'-' * 40}")
        report.append(f"Average Combined ORTG: {analysis['avg_combined_ortg']:.2f}")
        report.append(f"Average Combined DRTG: {analysis['avg_combined_drtg']:.2f}")
        report.append(f"ORTG vs DRTG Differential: {analysis['avg_ortg_vs_drtg']:+.2f}")
        report.append(f"Points Per Possession: {analysis['avg_points_per_poss']:.3f}")
        report.append(f"ORTG vs Season Average: {analysis['ortg_vs_season']:+.2f}")
        report.append(f"75th Percentile ORTG: {thresholds['ortg_threshold']:.2f}")

        report.append(f"\n{'-' * 40}")
        report.append("SHOT PROFILE")
        report.append(f"{'-' * 40}")
        report.append(f"Average Combined 3PA: {analysis['avg_combined_3pa']:.1f}")
        report.append(f"Average Combined 3PM: {analysis['avg_combined_3pm']:.1f}")
        report.append(f"Average Combined 3P%: {analysis['avg_combined_3p_pct']:.1f}%")
        report.append(f"3PA vs Season Average: {analysis['three_pa_vs_season']:+.1f}")
        report.append(f"75th Percentile 3PA: {thresholds['fg3a_threshold']:.1f}")

        report.append(f"\n{'-' * 40}")
        report.append("FREE THROW PROFILE")
        report.append(f"{'-' * 40}")
        report.append(f"Average Combined FTA: {analysis['avg_combined_fta']:.1f}")
        report.append(f"Average Combined FTM: {analysis['avg_combined_ftm']:.1f}")
        report.append(f"FTA vs Season Average: {analysis['fta_vs_season']:+.1f}")
        report.append(f"75th Percentile FTA: {thresholds['fta_threshold']:.1f}")

        report.append(f"\n{'-' * 40}")
        report.append("BALL CONTROL PROFILE")
        report.append(f"{'-' * 40}")
        report.append(f"Average Turnover Rate: {analysis['avg_tov_rate']:.2f} per 100 poss")
        report.append(f"Average Assist-to-Turnover: {analysis['avg_ast_to_tov']:.2f}")
        report.append(f"Average Combined Turnovers: {analysis['avg_combined_tov']:.1f}")
        report.append(f"Average Combined Assists: {analysis['avg_combined_ast']:.1f}")

    return "\n".join(report)

def generate_basketball_narratives(analyses, df):
    """Generate basketball-intelligent explanations for each scoring environment."""

    narratives = []
    narratives.append("\n" + "=" * 80)
    narratives.append("BASKETBALL INTELLIGENCE: WHY EACH SCORING ENVIRONMENT OCCURS")
    narratives.append("=" * 80)

    # EXTREME HIGH (240+)
    high_analysis = next((a for a in analyses if a['bucket'] == 'EXTREME_HIGH'), None)
    if high_analysis:
        narratives.append(f"\n\n{'=' * 80}")
        narratives.append("240+ GAMES: THE SCORING EXPLOSION")
        narratives.append(f"{'=' * 80}")
        narratives.append("\nWHY POSSESSIONS BALLOON:")
        narratives.append(f"  • Combined pace averages {high_analysis['avg_pace']:.1f}, {high_analysis['pace_vs_season']:+.1f} above season norm")
        narratives.append(f"  • {high_analysis['pct_both_teams_fast']:.0f}% of games have BOTH teams playing above-average pace")
        narratives.append("  • Fast tempo creates compound effect: more possessions × efficient scoring")

        narratives.append("\nWHY EFFICIENCY STAYS HIGH:")
        narratives.append(f"  • Combined ORTG of {high_analysis['avg_combined_ortg']:.1f} ({high_analysis['ortg_vs_season']:+.1f} above season)")
        narratives.append(f"  • Teams score {high_analysis['avg_points_per_poss']:.3f} points per possession")
        narratives.append(f"  • ORTG exceeds DRTG by {high_analysis['avg_ortg_vs_drtg']:.1f} points - offense dominates")

        narratives.append("\nWHY DEFENSES FAIL STRUCTURALLY:")
        narratives.append(f"  • High pace ({high_analysis['avg_pace']:.1f}) limits defensive set time")
        narratives.append("  • Transition opportunities create defensive scrambles")
        narratives.append(f"  • {high_analysis['avg_combined_3pa']:.0f} combined 3PA at {high_analysis['avg_combined_3p_pct']:.1f}% - volume shooting succeeds")
        narratives.append("  • Defenses cannot sustain intensity over increased possessions")

        narratives.append("\nWHY VARIANCE FAVORS THE CEILING:")
        narratives.append(f"  • Both teams shooting efficiently creates multiplicative scoring")
        narratives.append(f"  • {high_analysis['avg_combined_fta']:.0f} FTA indicates aggressive play, bonus situations")
        narratives.append("  • Momentum swings favor offense in up-tempo environments")

    # EXTREME LOW (≤220)
    low_analysis = next((a for a in analyses if a['bucket'] == 'EXTREME_LOW'), None)
    if low_analysis:
        narratives.append(f"\n\n{'=' * 80}")
        narratives.append("≤220 GAMES: THE GRIND-IT-OUT SLUGFEST")
        narratives.append(f"{'=' * 80}")
        narratives.append("\nHOW PACE SUPPRESSION HAPPENS:")
        narratives.append(f"  • Combined pace of {low_analysis['avg_pace']:.1f} ({low_analysis['pace_vs_season']:+.1f} vs season)")
        narratives.append(f"  • Only {low_analysis['pct_both_teams_fast']:.0f}% of games have both teams playing fast")
        narratives.append("  • Deliberate halfcourt offense, long possessions, clock management")
        narratives.append("  • Fewer total possessions = lower ceiling for total points")

        narratives.append("\nHOW DEFENSES CONTROL SHOT QUALITY:")
        narratives.append(f"  • Combined DRTG of {low_analysis['avg_combined_drtg']:.1f} - stout defensive performances")
        narratives.append(f"  • Points per possession drops to {low_analysis['avg_points_per_poss']:.3f}")
        narratives.append(f"  • ORTG vs DRTG differential: {low_analysis['avg_ortg_vs_drtg']:.1f} - defense has edge")
        narratives.append("  • Defenses force contested shots, limit transition")

        narratives.append("\nWHY SCORING FLOORS COLLAPSE:")
        narratives.append(f"  • Combined 3PA only {low_analysis['avg_combined_3pa']:.0f} ({low_analysis['three_pa_vs_season']:+.1f} vs season)")
        narratives.append(f"  • 3P% of {low_analysis['avg_combined_3p_pct']:.1f}% - perimeter offense struggles")
        narratives.append(f"  • {low_analysis['avg_combined_fta']:.0f} FTA - fewer bonus situations, less aggression")
        narratives.append(f"  • Turnover rate: {low_analysis['avg_tov_rate']:.1f} per 100 - ball security over aggression")

        narratives.append("\nWHY VARIANCE FAVORS UNDERS:")
        narratives.append("  • Fewer possessions = smaller sample size, lower variance ceiling")
        narratives.append("  • Defensive intensity sustainable over slower pace")
        narratives.append("  • One cold shooting quarter can crater the total")

    # MID-RANGE (221-239)
    mid_analysis = next((a for a in analyses if a['bucket'] == 'MID_RANGE'), None)
    if mid_analysis:
        narratives.append(f"\n\n{'=' * 80}")
        narratives.append("221-239 GAMES: THE UNPREDICTABLE GRAY ZONE")
        narratives.append(f"{'=' * 80}")
        narratives.append("\nWHY SIGNALS CONFLICT:")
        narratives.append(f"  • Pace of {mid_analysis['avg_pace']:.1f} is neutral ({mid_analysis['pace_vs_season']:+.1f} vs season)")
        narratives.append(f"  • {mid_analysis['pct_both_teams_fast']:.0f}% fast-paced matchups - tempo is mixed")
        narratives.append(f"  • ORTG-DRTG differential of {mid_analysis['avg_ortg_vs_drtg']:.1f} - balanced")
        narratives.append("  • No dominant structural advantage for offense or defense")

        narratives.append("\nWHICH STATS CANCEL EACH OTHER OUT:")
        narratives.append(f"  • {mid_analysis['avg_combined_3pa']:.0f} 3PA at {mid_analysis['avg_combined_3p_pct']:.1f}% - neither volume nor efficiency extreme")
        narratives.append(f"  • {mid_analysis['avg_combined_fta']:.0f} FTA - moderate aggression")
        narratives.append("  • One team's pace can cancel the other's grind tempo")
        narratives.append("  • Offensive efficiency can be offset by defensive resistance")

        narratives.append("\nWHY VOLATILITY MATTERS MORE THAN AVERAGES:")
        narratives.append(f"  • Standard deviation of {mid_analysis['total_points_std']:.1f} points - highest uncertainty")
        narratives.append(f"  • Pace volatility: {mid_analysis['pace_std']:.2f} - games vary wildly")
        narratives.append("  • Style matchups determine outcome more than season averages")
        narratives.append("  • Small momentum shifts can push game over 240 or under 220")

        narratives.append("\nWHY THESE GAMES ARE HARDEST TO TRUST:")
        narratives.append("  • No clear structural advantage")
        narratives.append("  • Execution variance dominates")
        narratives.append("  • Matchup-specific factors (rest, injuries, motivation) become decisive")
        narratives.append("  • Betting markets price these efficiently - less edge available")

    return "\n".join(narratives)

def generate_reusable_summary(analyses, thresholds_dict):
    """Generate clean, reusable profiles for each scoring bucket."""

    summary = []
    summary.append("\n" + "=" * 80)
    summary.append("REUSABLE SCORING ENVIRONMENT PROFILES")
    summary.append("=" * 80)

    # EXTREME HIGH
    high = next((a for a in analyses if a['bucket'] == 'EXTREME_HIGH'), None)
    high_thresh = thresholds_dict['EXTREME_HIGH']
    if high:
        summary.append(f"\n\n{'-' * 80}")
        summary.append("240+ SCORING PROFILE")
        summary.append(f"{'-' * 80}")
        summary.append("\nDEFINING TRAITS:")
        summary.append(f"  ✓ Combined pace ≥ {high_thresh['pace_threshold']:.1f}")
        summary.append(f"  ✓ Combined ORTG ≥ {high_thresh['ortg_threshold']:.1f}")
        summary.append(f"  ✓ Points per possession ≥ {high_thresh['points_per_poss_threshold']:.3f}")
        summary.append(f"  ✓ Combined 3PA ≥ {high_thresh['fg3a_threshold']:.0f}")
        summary.append(f"  ✓ Both teams playing above-average pace (frequent)")
        summary.append(f"  ✓ ORTG significantly exceeds DRTG")

        summary.append("\nKEY STATISTICAL THRESHOLDS:")
        summary.append(f"  • Pace: {high_thresh['pace_threshold']:.1f}+")
        summary.append(f"  • Combined ORTG: {high_thresh['ortg_threshold']:.1f}+")
        summary.append(f"  • Combined 3PA: {high_thresh['fg3a_threshold']:.0f}+")
        summary.append(f"  • Points/Possession: {high_thresh['points_per_poss_threshold']:.3f}+")

        summary.append("\nNARRATIVE:")
        summary.append("  High-scoring games are structural, not random. They occur when two up-tempo")
        summary.append("  offenses meet with defensive limitations. The compound effect of increased")
        summary.append("  possessions × efficient scoring creates explosive totals. Defenses cannot")
        summary.append("  sustain intensity over 100+ possessions. Transition opportunities, 3-point")
        summary.append("  volume, and momentum swings favor ceiling outcomes.")

    # EXTREME LOW
    low = next((a for a in analyses if a['bucket'] == 'EXTREME_LOW'), None)
    low_thresh = thresholds_dict['EXTREME_LOW']
    if low:
        summary.append(f"\n\n{'-' * 80}")
        summary.append("≤220 SCORING PROFILE")
        summary.append(f"{'-' * 80}")
        summary.append("\nDEFINING TRAITS:")
        summary.append(f"  ✓ Combined pace ≤ {100 - (high_thresh['pace_threshold'] - 100):.1f}")
        summary.append(f"  ✓ Points per possession ≤ {low_thresh['points_per_poss_threshold']:.3f}")
        summary.append(f"  ✓ Combined 3PA below season average")
        summary.append(f"  ✓ DRTG meets or exceeds ORTG")
        summary.append(f"  ✓ Slow, deliberate halfcourt offense")
        summary.append(f"  ✓ Limited transition opportunities")

        summary.append("\nKEY STATISTICAL THRESHOLDS:")
        summary.append(f"  • Pace: <{low_thresh['pace_threshold']:.1f}")
        summary.append(f"  • Points/Possession: <{low_thresh['points_per_poss_threshold']:.3f}")
        summary.append(f"  • Combined 3PA: <{low_thresh['fg3a_threshold']:.0f}")
        summary.append(f"  • ORTG-DRTG differential: Negative or near zero")

        summary.append("\nNARRATIVE:")
        summary.append("  Low-scoring games result from pace suppression and defensive dominance.")
        summary.append("  Fewer possessions lower the ceiling. Defenses control shot quality, force")
        summary.append("  contested attempts, and limit transition. Perimeter shooting struggles.")
        summary.append("  The variance floor is low - one cold quarter can crater the total.")
        summary.append("  These are grind-it-out games where defense and execution trump talent.")

    # MID-RANGE
    mid = next((a for a in analyses if a['bucket'] == 'MID_RANGE'), None)
    mid_thresh = thresholds_dict['MID_RANGE']
    if mid:
        summary.append(f"\n\n{'-' * 80}")
        summary.append("221-239 GRAY ZONE PROFILE")
        summary.append(f"{'-' * 80}")
        summary.append("\nCONFLICTING SIGNALS:")
        summary.append(f"  ⚠ Pace is neutral (~{mid['avg_pace']:.1f})")
        summary.append(f"  ⚠ ORTG-DRTG differential near zero")
        summary.append(f"  ⚠ No dominant structural trend")
        summary.append("  ⚠ One team's tendencies can cancel the other's")
        summary.append("  ⚠ Execution variance > structural advantage")

        summary.append("\nCOMMON TRAPS:")
        summary.append("  • Assuming season averages will hold")
        summary.append("  • Ignoring style matchup dynamics")
        summary.append("  • Underweighting pace volatility")
        summary.append("  • Overlooking rest/schedule spots")
        summary.append("  • Trusting models built on stable inputs")

        summary.append("\nWHY PREDICTION ERROR INCREASES:")
        summary.append("  • No clear structural edge = higher variance")
        summary.append("  • Micro factors (officiating, momentum, lineup decisions) matter more")
        summary.append("  • Markets price these games efficiently")
        summary.append("  • Small changes (one hot/cold quarter) swing outcome dramatically")
        summary.append("  • Confidence should be LOWER, not higher, in mid-range totals")

    return "\n".join(summary)

def main():
    print("Loading completed games...")
    df = get_completed_games()
    print(f"Loaded {len(df)} completed games with full stats\n")

    print("Calculating season averages...")
    season_avg = get_season_averages(df)

    print("Classifying games into scoring buckets...")
    df = classify_games(df)

    print("Calculating combined statistics...")
    df = calculate_combined_stats(df)

    print("\nScoring Bucket Distribution:")
    print(df['scoring_bucket'].value_counts().sort_index())
    print()

    # Analyze each bucket
    analyses = []
    thresholds_dict = {}

    for bucket in ['EXTREME_HIGH', 'MID_RANGE', 'EXTREME_LOW']:
        df_bucket = df[df['scoring_bucket'] == bucket]
        if len(df_bucket) > 0:
            analysis = analyze_bucket(df_bucket, bucket, season_avg)
            analyses.append(analysis)

            thresholds = identify_thresholds(df, bucket)
            thresholds_dict[bucket] = thresholds

    # Generate reports
    print("\n" + "=" * 80)
    print("GENERATING ANALYSIS REPORTS")
    print("=" * 80)

    statistical_report = format_analysis_report(analyses, thresholds_dict, df)
    print(statistical_report)

    narrative_report = generate_basketball_narratives(analyses, df)
    print(narrative_report)

    reusable_summary = generate_reusable_summary(analyses, thresholds_dict)
    print(reusable_summary)

    # Save to file
    output_file = "SCORING_ENVIRONMENT_ANALYSIS.md"
    with open(output_file, 'w') as f:
        f.write(statistical_report)
        f.write("\n\n")
        f.write(narrative_report)
        f.write("\n\n")
        f.write(reusable_summary)

    print(f"\n\n{'=' * 80}")
    print(f"Analysis saved to: {output_file}")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    main()
