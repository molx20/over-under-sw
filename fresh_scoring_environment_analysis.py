"""
FRESH NBA Scoring Environment Analysis
Discovers the statistical DNA of extreme high, extreme low, and mid-range scoring games
"""

import sqlite3
import pandas as pd
import numpy as np

DB_PATH = "api/data/nba_data.db"

def get_all_completed_games():
    """Extract ALL completed games with full team stats."""
    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT
        g.id as game_id,
        g.game_date,
        g.season,
        g.actual_total_points,
        g.home_score,
        g.away_score,

        -- Home team stats
        h.team_id as home_team_id,
        h.pace as home_pace,
        h.off_rating as home_ortg,
        h.def_rating as home_drtg,
        h.team_pts as home_pts,
        h.fg3a as home_fg3a,
        h.fg3m as home_fg3m,
        h.fg3_pct as home_fg3_pct,
        h.fta as home_fta,
        h.ftm as home_ftm,
        h.ft_pct as home_ft_pct,
        h.turnovers as home_tov,
        h.assists as home_ast,
        h.possessions as home_poss,
        h.points_in_paint as home_paint_pts,
        h.fast_break_points as home_fastbreak_pts,

        -- Away team stats
        a.team_id as away_team_id,
        a.pace as away_pace,
        a.off_rating as away_ortg,
        a.def_rating as away_drtg,
        a.team_pts as away_pts,
        a.fg3a as away_fg3a,
        a.fg3m as away_fg3m,
        a.fg3_pct as away_fg3_pct,
        a.fta as away_fta,
        a.ftm as away_ftm,
        a.ft_pct as away_ft_pct,
        a.turnovers as away_tov,
        a.assists as away_ast,
        a.possessions as away_poss,
        a.points_in_paint as away_paint_pts,
        a.fast_break_points as away_fastbreak_pts

    FROM games g
    JOIN team_game_logs h ON g.id = h.game_id AND g.home_team_id = h.team_id
    JOIN team_game_logs a ON g.id = a.game_id AND g.away_team_id = a.team_id
    WHERE g.actual_total_points IS NOT NULL
    AND h.pace IS NOT NULL
    AND a.pace IS NOT NULL
    ORDER BY g.game_date DESC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df

def calculate_combined_metrics(df):
    """Calculate all combined team statistics."""

    # Basic combined stats
    df['combined_pace'] = (df['home_pace'] + df['away_pace']) / 2
    df['combined_ortg'] = (df['home_ortg'] + df['away_ortg']) / 2
    df['combined_drtg'] = (df['home_drtg'] + df['away_drtg']) / 2

    # Shooting metrics
    df['combined_fg3a'] = df['home_fg3a'] + df['away_fg3a']
    df['combined_fg3m'] = df['home_fg3m'] + df['away_fg3m']
    df['combined_fg3_pct'] = (df['combined_fg3m'] / df['combined_fg3a'].replace(0, np.nan)) * 100

    # Free throw metrics
    df['combined_fta'] = df['home_fta'] + df['away_fta']
    df['combined_ftm'] = df['home_ftm'] + df['away_ftm']
    df['combined_ft_pct'] = (df['combined_ftm'] / df['combined_fta'].replace(0, np.nan)) * 100

    # Ball control metrics
    df['combined_tov'] = df['home_tov'] + df['away_tov']
    df['combined_ast'] = df['home_ast'] + df['away_ast']
    df['ast_to_tov_ratio'] = df['combined_ast'] / df['combined_tov'].replace(0, np.nan)

    # Possessions and efficiency
    df['combined_poss'] = (df['home_poss'] + df['away_poss']) / 2
    df['points_per_poss'] = df['actual_total_points'] / df['combined_poss']
    df['tov_rate'] = (df['combined_tov'] / df['combined_poss']) * 100

    # Paint and transition scoring
    df['combined_paint_pts'] = df['home_paint_pts'].fillna(0) + df['away_paint_pts'].fillna(0)
    df['combined_fastbreak_pts'] = df['home_fastbreak_pts'].fillna(0) + df['away_fastbreak_pts'].fillna(0)

    # Efficiency differential
    df['ortg_drtg_diff'] = df['combined_ortg'] - df['combined_drtg']

    # Pace indicators
    df['both_teams_fast'] = ((df['home_pace'] > 100) & (df['away_pace'] > 100)).astype(int)
    df['both_teams_slow'] = ((df['home_pace'] < 98) & (df['away_pace'] < 98)).astype(int)

    # Classify into scoring buckets
    df['scoring_bucket'] = pd.cut(
        df['actual_total_points'],
        bins=[0, 220, 239, 1000],
        labels=['EXTREME_LOW', 'MID_RANGE', 'EXTREME_HIGH'],
        include_lowest=True
    )

    return df

def get_league_averages(df):
    """Calculate league-wide averages for comparison."""
    return {
        'pace': df['combined_pace'].mean(),
        'ortg': df['combined_ortg'].mean(),
        'drtg': df['combined_drtg'].mean(),
        'fg3a': df['combined_fg3a'].mean(),
        'fg3_pct': df['combined_fg3_pct'].mean(),
        'fta': df['combined_fta'].mean(),
        'ft_pct': df['combined_ft_pct'].mean(),
        'tov': df['combined_tov'].mean(),
        'ast': df['combined_ast'].mean(),
        'points_per_poss': df['points_per_poss'].mean(),
    }

def analyze_scoring_bucket(df, bucket_name, league_avg):
    """Comprehensive analysis of a scoring bucket."""

    bucket_df = df[df['scoring_bucket'] == bucket_name].copy()
    n = len(bucket_df)

    if n == 0:
        return None

    analysis = {
        'bucket': bucket_name,
        'n_games': n,
        'pct_of_total': (n / len(df)) * 100,
        'total_min': bucket_df['actual_total_points'].min(),
        'total_max': bucket_df['actual_total_points'].max(),
        'total_avg': bucket_df['actual_total_points'].mean(),
        'total_std': bucket_df['actual_total_points'].std(),

        # TEMPO
        'avg_pace': bucket_df['combined_pace'].mean(),
        'pace_vs_league': bucket_df['combined_pace'].mean() - league_avg['pace'],
        'pace_std': bucket_df['combined_pace'].std(),
        'pct_both_fast': (bucket_df['both_teams_fast'].sum() / n) * 100,
        'pct_both_slow': (bucket_df['both_teams_slow'].sum() / n) * 100,
        'pace_25th': bucket_df['combined_pace'].quantile(0.25),
        'pace_75th': bucket_df['combined_pace'].quantile(0.75),

        # EFFICIENCY
        'avg_ortg': bucket_df['combined_ortg'].mean(),
        'ortg_vs_league': bucket_df['combined_ortg'].mean() - league_avg['ortg'],
        'avg_drtg': bucket_df['combined_drtg'].mean(),
        'drtg_vs_league': bucket_df['combined_drtg'].mean() - league_avg['drtg'],
        'avg_ortg_drtg_diff': bucket_df['ortg_drtg_diff'].mean(),
        'avg_pts_per_poss': bucket_df['points_per_poss'].mean(),
        'pts_per_poss_vs_league': bucket_df['points_per_poss'].mean() - league_avg['points_per_poss'],
        'ortg_75th': bucket_df['combined_ortg'].quantile(0.75),
        'ortg_25th': bucket_df['combined_ortg'].quantile(0.25),

        # SHOOTING
        'avg_3pa': bucket_df['combined_fg3a'].mean(),
        'fg3a_vs_league': bucket_df['combined_fg3a'].mean() - league_avg['fg3a'],
        'avg_3pm': bucket_df['combined_fg3m'].mean(),
        'avg_3p_pct': bucket_df['combined_fg3_pct'].mean(),
        'fg3_pct_vs_league': bucket_df['combined_fg3_pct'].mean() - league_avg['fg3_pct'],
        'fg3a_75th': bucket_df['combined_fg3a'].quantile(0.75),
        'fg3a_25th': bucket_df['combined_fg3a'].quantile(0.25),

        # FREE THROWS
        'avg_fta': bucket_df['combined_fta'].mean(),
        'fta_vs_league': bucket_df['combined_fta'].mean() - league_avg['fta'],
        'avg_ftm': bucket_df['combined_ftm'].mean(),
        'avg_ft_pct': bucket_df['combined_ft_pct'].mean(),
        'fta_75th': bucket_df['combined_fta'].quantile(0.75),

        # BALL CONTROL
        'avg_tov': bucket_df['combined_tov'].mean(),
        'tov_vs_league': bucket_df['combined_tov'].mean() - league_avg['tov'],
        'avg_tov_rate': bucket_df['tov_rate'].mean(),
        'avg_ast': bucket_df['combined_ast'].mean(),
        'ast_vs_league': bucket_df['combined_ast'].mean() - league_avg['ast'],
        'avg_ast_tov_ratio': bucket_df['ast_to_tov_ratio'].mean(),

        # SCORING BREAKDOWN
        'avg_paint_pts': bucket_df['combined_paint_pts'].mean(),
        'avg_fastbreak_pts': bucket_df['combined_fastbreak_pts'].mean(),
    }

    return analysis

def find_deterministic_thresholds(df):
    """Find combinations that predict scoring environments with high accuracy."""

    results = []

    # Test pace + ORTG combinations for EXTREME HIGH
    for pace_thresh in [100, 102, 104, 105, 106, 108, 110]:
        for ortg_thresh in [110, 112, 115, 118, 120, 122, 125]:
            mask = (df['combined_pace'] >= pace_thresh) & (df['combined_ortg'] >= ortg_thresh)
            if mask.sum() >= 10:
                subset = df[mask]
                pct_high = (subset['scoring_bucket'] == 'EXTREME_HIGH').sum() / len(subset) * 100
                pct_low = (subset['scoring_bucket'] == 'EXTREME_LOW').sum() / len(subset) * 100

                if pct_high >= 80 or pct_low >= 80:
                    results.append({
                        'condition': f"Pace ≥ {pace_thresh} AND ORTG ≥ {ortg_thresh}",
                        'n_games': len(subset),
                        'pct_extreme_high': pct_high,
                        'pct_mid_range': (subset['scoring_bucket'] == 'MID_RANGE').sum() / len(subset) * 100,
                        'pct_extreme_low': pct_low,
                        'avg_total': subset['actual_total_points'].mean(),
                        'signal_type': 'HIGH' if pct_high > pct_low else 'LOW'
                    })

    # Test pace + 3PA combinations for EXTREME LOW
    for pace_thresh in [88, 90, 92, 95, 98, 100]:
        for fg3a_thresh in [60, 62, 65, 68, 70, 72, 75]:
            mask = (df['combined_pace'] <= pace_thresh) & (df['combined_fg3a'] <= fg3a_thresh)
            if mask.sum() >= 10:
                subset = df[mask]
                pct_high = (subset['scoring_bucket'] == 'EXTREME_HIGH').sum() / len(subset) * 100
                pct_low = (subset['scoring_bucket'] == 'EXTREME_LOW').sum() / len(subset) * 100

                if pct_low >= 80 or pct_high >= 80:
                    results.append({
                        'condition': f"Pace ≤ {pace_thresh} AND 3PA ≤ {fg3a_thresh}",
                        'n_games': len(subset),
                        'pct_extreme_high': pct_high,
                        'pct_mid_range': (subset['scoring_bucket'] == 'MID_RANGE').sum() / len(subset) * 100,
                        'pct_extreme_low': pct_low,
                        'avg_total': subset['actual_total_points'].mean(),
                        'signal_type': 'LOW' if pct_low > pct_high else 'HIGH'
                    })

    # Test ORTG + 3PA for HIGH
    for ortg_thresh in [115, 118, 120, 122]:
        for fg3a_thresh in [75, 78, 80, 82, 85]:
            mask = (df['combined_ortg'] >= ortg_thresh) & (df['combined_fg3a'] >= fg3a_thresh)
            if mask.sum() >= 10:
                subset = df[mask]
                pct_high = (subset['scoring_bucket'] == 'EXTREME_HIGH').sum() / len(subset) * 100

                if pct_high >= 80:
                    results.append({
                        'condition': f"ORTG ≥ {ortg_thresh} AND 3PA ≥ {fg3a_thresh}",
                        'n_games': len(subset),
                        'pct_extreme_high': pct_high,
                        'pct_mid_range': (subset['scoring_bucket'] == 'MID_RANGE').sum() / len(subset) * 100,
                        'pct_extreme_low': (subset['scoring_bucket'] == 'EXTREME_LOW').sum() / len(subset) * 100,
                        'avg_total': subset['actual_total_points'].mean(),
                        'signal_type': 'HIGH'
                    })

    return pd.DataFrame(results)

def print_analysis_report(analyses, league_avg, df):
    """Print comprehensive analysis report."""

    print("\n" + "=" * 100)
    print("NBA SCORING ENVIRONMENT ANALYSIS - COMPLETE STATISTICAL PROFILE")
    print("=" * 100)
    print(f"\nTotal Games Analyzed: {len(df)}")
    print(f"Date Range: {df['game_date'].min()} to {df['game_date'].max()}")

    print(f"\n{'=' * 100}")
    print("LEAGUE-WIDE AVERAGES (Baseline)")
    print(f"{'=' * 100}")
    print(f"Pace: {league_avg['pace']:.2f}")
    print(f"Combined ORTG: {league_avg['ortg']:.2f}")
    print(f"Combined DRTG: {league_avg['drtg']:.2f}")
    print(f"Points/Possession: {league_avg['points_per_poss']:.3f}")
    print(f"Combined 3PA: {league_avg['fg3a']:.1f}")
    print(f"Combined 3P%: {league_avg['fg3_pct']:.1f}%")
    print(f"Combined FTA: {league_avg['fta']:.1f}")

    bucket_order = ['EXTREME_HIGH', 'MID_RANGE', 'EXTREME_LOW']
    bucket_labels = {
        'EXTREME_HIGH': '🔥 EXTREME HIGH SCORING (≥240 Points)',
        'MID_RANGE': '⚠️  MID-RANGE SCORING (221-239 Points)',
        'EXTREME_LOW': '🧊 EXTREME LOW SCORING (≤220 Points)'
    }

    for bucket_name in bucket_order:
        analysis = next((a for a in analyses if a['bucket'] == bucket_name), None)
        if not analysis:
            continue

        print(f"\n\n{'=' * 100}")
        print(bucket_labels[bucket_name])
        print(f"{'=' * 100}")
        print(f"\nSample Size: {analysis['n_games']} games ({analysis['pct_of_total']:.1f}% of total)")
        print(f"Total Points Range: {analysis['total_min']:.0f} - {analysis['total_max']:.0f}")
        print(f"Average Total: {analysis['total_avg']:.1f}")
        print(f"Standard Deviation: {analysis['total_std']:.1f} points")

        print(f"\n{'-' * 50}")
        print("TEMPO PROFILE")
        print(f"{'-' * 50}")
        print(f"Average Combined Pace: {analysis['avg_pace']:.2f} ({analysis['pace_vs_league']:+.2f} vs league)")
        print(f"Pace Range (25th-75th): {analysis['pace_25th']:.1f} - {analysis['pace_75th']:.1f}")
        print(f"Pace Volatility (Std Dev): {analysis['pace_std']:.2f}")
        print(f"Both Teams Fast (>100): {analysis['pct_both_fast']:.1f}%")
        print(f"Both Teams Slow (<98): {analysis['pct_both_slow']:.1f}%")

        print(f"\n{'-' * 50}")
        print("EFFICIENCY PROFILE")
        print(f"{'-' * 50}")
        print(f"Average Combined ORTG: {analysis['avg_ortg']:.2f} ({analysis['ortg_vs_league']:+.2f} vs league)")
        print(f"ORTG Range (25th-75th): {analysis['ortg_25th']:.1f} - {analysis['ortg_75th']:.1f}")
        print(f"Average Combined DRTG: {analysis['avg_drtg']:.2f} ({analysis['drtg_vs_league']:+.2f} vs league)")
        print(f"ORTG - DRTG Differential: {analysis['avg_ortg_drtg_diff']:+.2f}")
        print(f"Points Per Possession: {analysis['avg_pts_per_poss']:.3f} ({analysis['pts_per_poss_vs_league']:+.3f} vs league)")

        print(f"\n{'-' * 50}")
        print("SHOT PROFILE")
        print(f"{'-' * 50}")
        print(f"Average Combined 3PA: {analysis['avg_3pa']:.1f} ({analysis['fg3a_vs_league']:+.1f} vs league)")
        print(f"3PA Range (25th-75th): {analysis['fg3a_25th']:.1f} - {analysis['fg3a_75th']:.1f}")
        print(f"Average Combined 3PM: {analysis['avg_3pm']:.1f}")
        print(f"Average Combined 3P%: {analysis['avg_3p_pct']:.1f}% ({analysis['fg3_pct_vs_league']:+.1f}% vs league)")
        print(f"Average Paint Points: {analysis['avg_paint_pts']:.1f}")
        print(f"Average Fastbreak Points: {analysis['avg_fastbreak_pts']:.1f}")

        print(f"\n{'-' * 50}")
        print("FREE THROW PROFILE")
        print(f"{'-' * 50}")
        print(f"Average Combined FTA: {analysis['avg_fta']:.1f} ({analysis['fta_vs_league']:+.1f} vs league)")
        print(f"Average Combined FTM: {analysis['avg_ftm']:.1f}")
        print(f"Average FT%: {analysis['avg_ft_pct']:.1f}%")

        print(f"\n{'-' * 50}")
        print("BALL CONTROL PROFILE")
        print(f"{'-' * 50}")
        print(f"Average Turnovers: {analysis['avg_tov']:.1f} ({analysis['tov_vs_league']:+.1f} vs league)")
        print(f"Turnover Rate: {analysis['avg_tov_rate']:.2f} per 100 possessions")
        print(f"Average Assists: {analysis['avg_ast']:.1f} ({analysis['ast_vs_league']:+.1f} vs league)")
        print(f"Assist/Turnover Ratio: {analysis['avg_ast_tov_ratio']:.2f}")

def main():
    print("Extracting all completed games from database...")
    df = get_all_completed_games()
    print(f"✓ Loaded {len(df)} completed games")

    print("\nCalculating combined metrics...")
    df = calculate_combined_metrics(df)
    print("✓ Combined metrics calculated")

    print("\nCalculating league averages...")
    league_avg = get_league_averages(df)
    print("✓ League averages calculated")

    print("\nDistribution by Scoring Bucket:")
    print(df['scoring_bucket'].value_counts().sort_index())

    # Analyze each bucket
    analyses = []
    for bucket in ['EXTREME_HIGH', 'MID_RANGE', 'EXTREME_LOW']:
        analysis = analyze_scoring_bucket(df, bucket, league_avg)
        if analysis:
            analyses.append(analysis)

    # Print full statistical report
    print_analysis_report(analyses, league_avg, df)

    # Find deterministic thresholds
    print(f"\n\n{'=' * 100}")
    print("DETERMINISTIC THRESHOLD ANALYSIS - HIGH ACCURACY RULES")
    print(f"{'=' * 100}")

    thresholds = find_deterministic_thresholds(df)

    if len(thresholds) > 0:
        print(f"\n{'-' * 100}")
        print("EXTREME HIGH SCORING RULES (≥80% Accuracy)")
        print(f"{'-' * 100}")
        high_rules = thresholds[thresholds['signal_type'] == 'HIGH'].sort_values('pct_extreme_high', ascending=False)
        for _, row in high_rules.head(10).iterrows():
            print(f"\nIF {row['condition']}")
            print(f"   → {row['pct_extreme_high']:.1f}% hit EXTREME HIGH")
            print(f"   → Sample: {row['n_games']} games, Avg Total: {row['avg_total']:.1f}")

        print(f"\n\n{'-' * 100}")
        print("EXTREME LOW SCORING RULES (≥80% Accuracy)")
        print(f"{'-' * 100}")
        low_rules = thresholds[thresholds['signal_type'] == 'LOW'].sort_values('pct_extreme_low', ascending=False)
        for _, row in low_rules.head(10).iterrows():
            print(f"\nIF {row['condition']}")
            print(f"   → {row['pct_extreme_low']:.1f}% hit EXTREME LOW")
            print(f"   → Sample: {row['n_games']} games, Avg Total: {row['avg_total']:.1f}")

    # Save detailed CSV for further analysis
    output_file = "scoring_environment_data.csv"
    df.to_csv(output_file, index=False)
    print(f"\n\n{'=' * 100}")
    print(f"✓ Full dataset saved to: {output_file}")
    print(f"{'=' * 100}")

if __name__ == "__main__":
    main()
