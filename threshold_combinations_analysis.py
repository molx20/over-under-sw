"""
Advanced Threshold Combinations Analysis
Identifies combinations of factors that strongly predict each scoring environment
"""

import sqlite3
import pandas as pd
import numpy as np

DB_PATH = "api/data/nba_data.db"

def get_completed_games():
    """Extract all completed games with full stats from both teams."""
    conn = sqlite3.connect(DB_PATH)

    query = """
    WITH game_totals AS (
        SELECT
            g.id as game_id,
            g.game_date,
            g.actual_total_points,

            -- Home team stats
            h.pace as home_pace,
            h.off_rating as home_ortg,
            h.def_rating as home_drtg,
            h.fg3a as home_fg3a,
            h.fg3_pct as home_fg3_pct,
            h.fta as home_fta,

            -- Away team stats
            a.pace as away_pace,
            a.off_rating as away_ortg,
            a.def_rating as away_drtg,
            a.fg3a as away_fg3a,
            a.fg3_pct as away_fg3_pct,
            a.fta as away_fta

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

def calculate_combined_stats(df):
    """Calculate combined team statistics for each game."""
    df['combined_pace'] = (df['home_pace'] + df['away_pace']) / 2
    df['combined_ortg'] = (df['home_ortg'] + df['away_ortg']) / 2
    df['combined_drtg'] = (df['home_drtg'] + df['away_drtg']) / 2
    df['combined_fg3a'] = df['home_fg3a'] + df['away_fg3a']
    df['combined_fta'] = df['home_fta'] + df['away_fta']

    # Calculate additional metrics
    df['both_teams_fast'] = ((df['home_pace'] > 100) & (df['away_pace'] > 100)).astype(int)
    df['avg_fg3_pct'] = (df['home_fg3_pct'] + df['away_fg3_pct']) / 2

    # Classify
    df['scoring_bucket'] = pd.cut(
        df['actual_total_points'],
        bins=[0, 220, 239, 1000],
        labels=['EXTREME_LOW', 'MID_RANGE', 'EXTREME_HIGH'],
        include_lowest=True
    )

    return df

def find_strong_predictors(df):
    """Find combinations of factors that strongly predict each scoring environment."""

    results = []

    # Define thresholds to test
    pace_thresholds = [95, 98, 100, 102, 105, 108, 110]
    ortg_thresholds = [105, 110, 112, 115, 118, 120, 122]
    fg3a_thresholds = [65, 70, 72, 75, 78, 80, 85]
    fta_thresholds = [42, 45, 48, 50, 52, 55, 60]

    # TEST: High Pace + High ORTG
    for pace_thresh in pace_thresholds:
        for ortg_thresh in ortg_thresholds:
            mask = (df['combined_pace'] >= pace_thresh) & (df['combined_ortg'] >= ortg_thresh)
            if mask.sum() >= 10:  # Only if we have enough samples
                subset = df[mask]
                pct_high = (subset['scoring_bucket'] == 'EXTREME_HIGH').sum() / len(subset) * 100
                pct_low = (subset['scoring_bucket'] == 'EXTREME_LOW').sum() / len(subset) * 100

                if pct_high > 50 or pct_low > 50:  # Strong signal
                    results.append({
                        'condition': f"Pace ≥ {pace_thresh} AND ORTG ≥ {ortg_thresh}",
                        'n_games': len(subset),
                        'pct_extreme_high': pct_high,
                        'pct_mid_range': (subset['scoring_bucket'] == 'MID_RANGE').sum() / len(subset) * 100,
                        'pct_extreme_low': pct_low,
                        'avg_total': subset['actual_total_points'].mean(),
                        'signal_strength': max(pct_high, pct_low)
                    })

    # TEST: Low Pace + Low 3PA
    for pace_thresh in [90, 92, 95, 98, 100]:
        for fg3a_thresh in [60, 65, 68, 70, 72]:
            mask = (df['combined_pace'] <= pace_thresh) & (df['combined_fg3a'] <= fg3a_thresh)
            if mask.sum() >= 10:
                subset = df[mask]
                pct_high = (subset['scoring_bucket'] == 'EXTREME_HIGH').sum() / len(subset) * 100
                pct_low = (subset['scoring_bucket'] == 'EXTREME_LOW').sum() / len(subset) * 100

                if pct_high > 50 or pct_low > 50:
                    results.append({
                        'condition': f"Pace ≤ {pace_thresh} AND 3PA ≤ {fg3a_thresh}",
                        'n_games': len(subset),
                        'pct_extreme_high': pct_high,
                        'pct_mid_range': (subset['scoring_bucket'] == 'MID_RANGE').sum() / len(subset) * 100,
                        'pct_extreme_low': pct_low,
                        'avg_total': subset['actual_total_points'].mean(),
                        'signal_strength': max(pct_high, pct_low)
                    })

    # TEST: High 3PA + High FTA (shootout indicator)
    for fg3a_thresh in fg3a_thresholds:
        for fta_thresh in fta_thresholds:
            mask = (df['combined_fg3a'] >= fg3a_thresh) & (df['combined_fta'] >= fta_thresh)
            if mask.sum() >= 10:
                subset = df[mask]
                pct_high = (subset['scoring_bucket'] == 'EXTREME_HIGH').sum() / len(subset) * 100
                pct_low = (subset['scoring_bucket'] == 'EXTREME_LOW').sum() / len(subset) * 100

                if pct_high > 50 or pct_low > 50:
                    results.append({
                        'condition': f"3PA ≥ {fg3a_thresh} AND FTA ≥ {fta_thresh}",
                        'n_games': len(subset),
                        'pct_extreme_high': pct_high,
                        'pct_mid_range': (subset['scoring_bucket'] == 'MID_RANGE').sum() / len(subset) * 100,
                        'pct_extreme_low': pct_low,
                        'avg_total': subset['actual_total_points'].mean(),
                        'signal_strength': max(pct_high, pct_low)
                    })

    # TEST: Both teams fast
    mask = df['both_teams_fast'] == 1
    if mask.sum() >= 10:
        subset = df[mask]
        pct_high = (subset['scoring_bucket'] == 'EXTREME_HIGH').sum() / len(subset) * 100
        pct_low = (subset['scoring_bucket'] == 'EXTREME_LOW').sum() / len(subset) * 100
        results.append({
            'condition': "Both teams pace > 100",
            'n_games': len(subset),
            'pct_extreme_high': pct_high,
            'pct_mid_range': (subset['scoring_bucket'] == 'MID_RANGE').sum() / len(subset) * 100,
            'pct_extreme_low': pct_low,
            'avg_total': subset['actual_total_points'].mean(),
            'signal_strength': max(pct_high, pct_low)
        })

    return pd.DataFrame(results).sort_values('signal_strength', ascending=False)

def main():
    print("Loading completed games...")
    df = get_completed_games()
    print(f"Loaded {len(df)} completed games\n")

    print("Calculating combined statistics...")
    df = calculate_combined_stats(df)

    print("\n" + "=" * 80)
    print("FINDING STRONG THRESHOLD COMBINATIONS")
    print("=" * 80)

    predictors = find_strong_predictors(df)

    print("\n" + "-" * 80)
    print("TOP PREDICTORS FOR EXTREME HIGH SCORING (≥240)")
    print("-" * 80)
    high_predictors = predictors[predictors['pct_extreme_high'] > 40].head(15)
    print(high_predictors.to_string(index=False))

    print("\n\n" + "-" * 80)
    print("TOP PREDICTORS FOR EXTREME LOW SCORING (≤220)")
    print("-" * 80)
    low_predictors = predictors[predictors['pct_extreme_low'] > 40].head(15)
    print(low_predictors.to_string(index=False))

    print("\n\n" + "=" * 80)
    print("DECISION RULES SUMMARY")
    print("=" * 80)

    print("\nRULES FOR 240+ GAMES (High Confidence):")
    for _, row in high_predictors.head(5).iterrows():
        print(f"  IF {row['condition']}")
        print(f"     → {row['pct_extreme_high']:.1f}% hit EXTREME HIGH (n={row['n_games']}, avg={row['avg_total']:.1f})")

    print("\nRULES FOR ≤220 GAMES (High Confidence):")
    for _, row in low_predictors.head(5).iterrows():
        print(f"  IF {row['condition']}")
        print(f"     → {row['pct_extreme_low']:.1f}% hit EXTREME LOW (n={row['n_games']}, avg={row['avg_total']:.1f})")

    # Save to file
    with open("THRESHOLD_COMBINATIONS_ANALYSIS.md", 'w') as f:
        f.write("# Threshold Combinations Analysis\n\n")
        f.write("## Top Predictors for Extreme High Scoring (≥240)\n\n")
        f.write(high_predictors.to_markdown(index=False))
        f.write("\n\n## Top Predictors for Extreme Low Scoring (≤220)\n\n")
        f.write(low_predictors.to_markdown(index=False))

    print("\n\nAnalysis saved to: THRESHOLD_COMBINATIONS_ANALYSIS.md")

if __name__ == "__main__":
    main()
