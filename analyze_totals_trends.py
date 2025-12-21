import sqlite3
import pandas as pd
import numpy as np

# Connect to database
conn = sqlite3.connect('api/data/nba_data.db')

# Load completed games
games = pd.read_sql_query("""
    SELECT
        id as game_id,
        game_date as date,
        home_team_id,
        away_team_id,
        home_score,
        away_score,
        actual_total_points,
        game_pace
    FROM games
    WHERE status = 'final'
    AND actual_total_points IS NOT NULL
    ORDER BY game_date
""", conn)

print(f"Loaded {len(games)} completed games")
print(f"Date range: {games['date'].min()} to {games['date'].max()}")

# Load team season stats (overall split)
season_stats = pd.read_sql_query("""
    SELECT
        team_id,
        off_rtg,
        def_rtg,
        pace,
        assists,
        turnovers,
        fg3m,
        fg3a,
        fg3_pct,
        ftm,
        fta,
        ft_pct,
        ppg,
        opp_ppg,
        off_rtg_rank,
        def_rtg_rank
    FROM team_season_stats
    WHERE season = '2025-26'
    AND split_type = 'overall'
""", conn)

print(f"Loaded season stats for {len(season_stats)} teams")

# Load team game logs for detailed per-game stats
game_logs = pd.read_sql_query("""
    SELECT
        game_id,
        team_id,
        is_home,
        team_pts,
        opp_pts,
        off_rating,
        def_rating,
        pace,
        fg_pct,
        fg3_pct,
        ft_pct,
        rebounds,
        assists,
        turnovers,
        offensive_rebounds,
        defensive_rebounds,
        points_off_turnovers,
        fast_break_points,
        points_in_paint,
        second_chance_points,
        fg3m,
        fg3a,
        ftm,
        fta,
        fgm,
        fga
    FROM team_game_logs
    WHERE season = '2025-26'
""", conn)

print(f"Loaded {len(game_logs)} team game logs")

# Separate home and away game logs
home_logs = game_logs[game_logs['is_home'] == 1].copy()
away_logs = game_logs[game_logs['is_home'] == 0].copy()

# Drop team_id (we'll use home_team_id/away_team_id from games table)
# and rename all other columns with home_ prefix
home_logs = home_logs.drop(columns=['team_id', 'is_home'])
home_logs.columns = ['home_' + col if col != 'game_id' else col for col in home_logs.columns]

# Drop team_id and rename all other columns with away_ prefix
away_logs = away_logs.drop(columns=['team_id', 'is_home'])
away_logs.columns = ['away_' + col if col != 'game_id' else col for col in away_logs.columns]

# Merge home and away logs with games
analysis_df = games.merge(home_logs, on='game_id', how='left')
analysis_df = analysis_df.merge(away_logs, on='game_id', how='left')

# Add season averages for each team
home_season = season_stats.copy()
home_season.columns = ['home_season_' + col if col != 'team_id' else 'home_team_id' for col in home_season.columns]

away_season = season_stats.copy()
away_season.columns = ['away_season_' + col if col != 'team_id' else 'away_team_id' for col in away_season.columns]

analysis_df = analysis_df.merge(home_season, on='home_team_id', how='left')
analysis_df = analysis_df.merge(away_season, on='away_team_id', how='left')

# Calculate combined/matchup metrics
analysis_df['combined_3pa'] = analysis_df['home_fg3a'] + analysis_df['away_fg3a']
analysis_df['combined_3pm'] = analysis_df['home_fg3m'] + analysis_df['away_fg3m']
analysis_df['combined_3p_pct'] = analysis_df['combined_3pm'] / analysis_df['combined_3pa']
analysis_df['combined_assists'] = analysis_df['home_assists'] + analysis_df['away_assists']
analysis_df['combined_turnovers'] = analysis_df['home_turnovers'] + analysis_df['away_turnovers']
analysis_df['combined_fbp'] = analysis_df['home_fast_break_points'] + analysis_df['away_fast_break_points']
analysis_df['combined_pitp'] = analysis_df['home_points_in_paint'] + analysis_df['away_points_in_paint']
analysis_df['combined_pot'] = analysis_df['home_points_off_turnovers'] + analysis_df['away_points_off_turnovers']
analysis_df['combined_second_chance'] = analysis_df['home_second_chance_points'] + analysis_df['away_second_chance_points']
analysis_df['combined_fta'] = analysis_df['home_fta'] + analysis_df['away_fta']
analysis_df['combined_pace'] = (analysis_df['home_pace'] + analysis_df['away_pace']) / 2

# Average ORTG and DRTG
analysis_df['avg_ortg'] = (analysis_df['home_season_off_rtg'] + analysis_df['away_season_off_rtg']) / 2
analysis_df['avg_drtg'] = (analysis_df['home_season_def_rtg'] + analysis_df['away_season_def_rtg']) / 2

# Create flags
analysis_df['under_220'] = analysis_df['actual_total_points'] < 220
analysis_df['over_240'] = analysis_df['actual_total_points'] > 240

print("\n" + "="*80)
print("DATA PREPARATION COMPLETE")
print("="*80)
print(f"\nTotal games analyzed: {len(analysis_df)}")
print(f"Games UNDER 220: {analysis_df['under_220'].sum()} ({analysis_df['under_220'].sum()/len(analysis_df)*100:.1f}%)")
print(f"Games OVER 240: {analysis_df['over_240'].sum()} ({analysis_df['over_240'].sum()/len(analysis_df)*100:.1f}%)")
print(f"Games 220-240: {((~analysis_df['under_220']) & (~analysis_df['over_240'])).sum()}")

# Calculate percentiles for various metrics
for col in ['combined_3pa', 'combined_pitp', 'combined_fbp', 'combined_pace', 'combined_fta']:
    analysis_df[f'{col}_pct'] = analysis_df[col].rank(pct=True)

print("\n" + "="*80)
print("ANALYZING UNDER 220 TRENDS")
print("="*80)

under_220_games = analysis_df[analysis_df['under_220']]

# Trend 1: Both teams have below-average ORTG and strong defense
league_avg_ortg = analysis_df['avg_ortg'].mean()
league_avg_drtg = analysis_df['avg_drtg'].mean()

trend1_condition = (
    (analysis_df['home_season_off_rtg'] < league_avg_ortg) &
    (analysis_df['away_season_off_rtg'] < league_avg_ortg) &
    ((analysis_df['home_season_def_rtg'] < league_avg_drtg) |
     (analysis_df['away_season_def_rtg'] < league_avg_drtg))
)
trend1_games = analysis_df[trend1_condition]
trend1_under = trend1_games['under_220'].sum()
trend1_total = len(trend1_games)
trend1_pct = (trend1_under / trend1_total * 100) if trend1_total > 0 else 0

print(f"\nTrend 1: Both Teams Below-Average ORTG + Strong Defense")
print(f"Games matching: {trend1_total}")
print(f"Under 220: {trend1_under} ({trend1_pct:.1f}%)")
print(f"Avg total in these games: {trend1_games['actual_total_points'].mean():.1f}")

# Trend 2: Low 3PA volume + poor shooting
trend2_condition = (
    (analysis_df['combined_3pa_pct'] < 0.25) &
    (analysis_df['combined_3p_pct'] < analysis_df['combined_3p_pct'].median())
)
trend2_games = analysis_df[trend2_condition]
trend2_under = trend2_games['under_220'].sum()
trend2_total = len(trend2_games)
trend2_pct = (trend2_under / trend2_total * 100) if trend2_total > 0 else 0

print(f"\nTrend 2: Low 3PA Volume (Bottom 25%) + Below-Median 3P%")
print(f"Games matching: {trend2_total}")
print(f"Under 220: {trend2_under} ({trend2_pct:.1f}%)")
print(f"Avg 3PA: {trend2_games['combined_3pa'].mean():.1f}, Avg 3P%: {trend2_games['combined_3p_pct'].mean():.3f}")

# Trend 3: Low pace + strong defense
trend3_condition = (
    (analysis_df['combined_pace'] < analysis_df['combined_pace'].quantile(0.33)) &
    ((analysis_df['home_season_def_rtg_rank'] <= 10) |
     (analysis_df['away_season_def_rtg_rank'] <= 10))
)
trend3_games = analysis_df[trend3_condition]
trend3_under = trend3_games['under_220'].sum()
trend3_total = len(trend3_games)
trend3_pct = (trend3_under / trend3_total * 100) if trend3_total > 0 else 0

print(f"\nTrend 3: Low Pace (Bottom 33%) + Top-10 Defense")
print(f"Games matching: {trend3_total}")
print(f"Under 220: {trend3_under} ({trend3_pct:.1f}%)")
print(f"Avg pace: {trend3_games['combined_pace'].mean():.1f}")

# Trend 4: Low PITP (paint scoring)
trend4_condition = (
    (analysis_df['combined_pitp_pct'] < 0.25)
)
trend4_games = analysis_df[trend4_condition]
trend4_under = trend4_games['under_220'].sum()
trend4_total = len(trend4_games)
trend4_pct = (trend4_under / trend4_total * 100) if trend4_total > 0 else 0

print(f"\nTrend 4: Low Paint Scoring (Bottom 25%)")
print(f"Games matching: {trend4_total}")
print(f"Under 220: {trend4_under} ({trend4_pct:.1f}%)")
print(f"Avg PITP: {trend4_games['combined_pitp'].mean():.1f}")

# Trend 5: Low fastbreak + high turnovers (wasted possessions)
trend5_condition = (
    (analysis_df['combined_fbp_pct'] < 0.33) &
    (analysis_df['combined_turnovers'] > analysis_df['combined_turnovers'].median())
)
trend5_games = analysis_df[trend5_condition]
trend5_under = trend5_games['under_220'].sum()
trend5_total = len(trend5_games)
trend5_pct = (trend5_under / trend5_total * 100) if trend5_total > 0 else 0

print(f"\nTrend 5: Low Fastbreak (Bottom 33%) + High Turnovers")
print(f"Games matching: {trend5_total}")
print(f"Under 220: {trend5_under} ({trend5_pct:.1f}%)")
print(f"Avg FBP: {trend5_games['combined_fbp'].mean():.1f}, Avg TOV: {trend5_games['combined_turnovers'].mean():.1f}")

# Trend 6: Both teams top-15 defense
trend6_condition = (
    (analysis_df['home_season_def_rtg_rank'] <= 15) &
    (analysis_df['away_season_def_rtg_rank'] <= 15)
)
trend6_games = analysis_df[trend6_condition]
trend6_under = trend6_games['under_220'].sum()
trend6_total = len(trend6_games)
trend6_pct = (trend6_under / trend6_total * 100) if trend6_total > 0 else 0

print(f"\nTrend 6: Both Teams Top-15 Defense")
print(f"Games matching: {trend6_total}")
print(f"Under 220: {trend6_under} ({trend6_pct:.1f}%)")

# Trend 7: Low FT volume
trend7_condition = (
    (analysis_df['combined_fta_pct'] < 0.25)
)
trend7_games = analysis_df[trend7_condition]
trend7_under = trend7_games['under_220'].sum()
trend7_total = len(trend7_games)
trend7_pct = (trend7_under / trend7_total * 100) if trend7_total > 0 else 0

print(f"\nTrend 7: Low FT Volume (Bottom 25%)")
print(f"Games matching: {trend7_total}")
print(f"Under 220: {trend7_under} ({trend7_pct:.1f}%)")
print(f"Avg FTA: {trend7_games['combined_fta'].mean():.1f}")

print("\n" + "="*80)
print("ANALYZING OVER 240 TRENDS")
print("="*80)

over_240_games = analysis_df[analysis_df['over_240']]

# Trend 1: Both teams top offense
o_trend1_condition = (
    (analysis_df['home_season_off_rtg_rank'] <= 10) &
    (analysis_df['away_season_off_rtg_rank'] <= 10)
)
o_trend1_games = analysis_df[o_trend1_condition]
o_trend1_over = o_trend1_games['over_240'].sum()
o_trend1_total = len(o_trend1_games)
o_trend1_pct = (o_trend1_over / o_trend1_total * 100) if o_trend1_total > 0 else 0

print(f"\nTrend 1: Both Teams Top-10 Offense")
print(f"Games matching: {o_trend1_total}")
print(f"Over 240: {o_trend1_over} ({o_trend1_pct:.1f}%)")
print(f"Avg total: {o_trend1_games['actual_total_points'].mean():.1f}")

# Trend 2: High ORTG vs weak DRTG
o_trend2_condition = (
    ((analysis_df['home_season_off_rtg_rank'] <= 8) & (analysis_df['away_season_def_rtg_rank'] >= 23)) |
    ((analysis_df['away_season_off_rtg_rank'] <= 8) & (analysis_df['home_season_def_rtg_rank'] >= 23))
)
o_trend2_games = analysis_df[o_trend2_condition]
o_trend2_over = o_trend2_games['over_240'].sum()
o_trend2_total = len(o_trend2_games)
o_trend2_pct = (o_trend2_over / o_trend2_total * 100) if o_trend2_total > 0 else 0

print(f"\nTrend 2: Elite Offense (Top 8) vs Weak Defense (Bottom 8)")
print(f"Games matching: {o_trend2_total}")
print(f"Over 240: {o_trend2_over} ({o_trend2_pct:.1f}%)")
print(f"Avg total: {o_trend2_games['actual_total_points'].mean():.1f}")

# Trend 3: High 3PA volume + good shooting
o_trend3_condition = (
    (analysis_df['combined_3pa_pct'] > 0.75) &
    (analysis_df['combined_3p_pct'] > analysis_df['combined_3p_pct'].quantile(0.6))
)
o_trend3_games = analysis_df[o_trend3_condition]
o_trend3_over = o_trend3_games['over_240'].sum()
o_trend3_total = len(o_trend3_games)
o_trend3_pct = (o_trend3_over / o_trend3_total * 100) if o_trend3_total > 0 else 0

print(f"\nTrend 3: High 3PA Volume (Top 25%) + Good Shooting (Top 40%)")
print(f"Games matching: {o_trend3_total}")
print(f"Over 240: {o_trend3_over} ({o_trend3_pct:.1f}%)")
print(f"Avg 3PA: {o_trend3_games['combined_3pa'].mean():.1f}, Avg 3P%: {o_trend3_games['combined_3p_pct'].mean():.3f}")

# Trend 4: High pace + above-average ORTG
o_trend4_condition = (
    (analysis_df['combined_pace'] > analysis_df['combined_pace'].quantile(0.67)) &
    (analysis_df['avg_ortg'] > league_avg_ortg)
)
o_trend4_games = analysis_df[o_trend4_condition]
o_trend4_over = o_trend4_games['over_240'].sum()
o_trend4_total = len(o_trend4_games)
o_trend4_pct = (o_trend4_over / o_trend4_total * 100) if o_trend4_total > 0 else 0

print(f"\nTrend 4: High Pace (Top 33%) + Above-Average ORTG")
print(f"Games matching: {o_trend4_total}")
print(f"Over 240: {o_trend4_over} ({o_trend4_pct:.1f}%)")
print(f"Avg pace: {o_trend4_games['combined_pace'].mean():.1f}")

# Trend 5: High PITP (paint scoring)
o_trend5_condition = (
    (analysis_df['combined_pitp_pct'] > 0.75)
)
o_trend5_games = analysis_df[o_trend5_condition]
o_trend5_over = o_trend5_games['over_240'].sum()
o_trend5_total = len(o_trend5_games)
o_trend5_pct = (o_trend5_over / o_trend5_total * 100) if o_trend5_total > 0 else 0

print(f"\nTrend 5: High Paint Scoring (Top 25%)")
print(f"Games matching: {o_trend5_total}")
print(f"Over 240: {o_trend5_over} ({o_trend5_pct:.1f}%)")
print(f"Avg PITP: {o_trend5_games['combined_pitp'].mean():.1f}")

# Trend 6: High fastbreak scoring
o_trend6_condition = (
    (analysis_df['combined_fbp_pct'] > 0.75)
)
o_trend6_games = analysis_df[o_trend6_condition]
o_trend6_over = o_trend6_games['over_240'].sum()
o_trend6_total = len(o_trend6_games)
o_trend6_pct = (o_trend6_over / o_trend6_total * 100) if o_trend6_total > 0 else 0

print(f"\nTrend 6: High Fastbreak Scoring (Top 25%)")
print(f"Games matching: {o_trend6_total}")
print(f"Over 240: {o_trend6_over} ({o_trend6_pct:.1f}%)")
print(f"Avg FBP: {o_trend6_games['combined_fbp'].mean():.1f}")

# Trend 7: Both defenses bottom-10
o_trend7_condition = (
    (analysis_df['home_season_def_rtg_rank'] >= 21) &
    (analysis_df['away_season_def_rtg_rank'] >= 21)
)
o_trend7_games = analysis_df[o_trend7_condition]
o_trend7_over = o_trend7_games['over_240'].sum()
o_trend7_total = len(o_trend7_games)
o_trend7_pct = (o_trend7_over / o_trend7_total * 100) if o_trend7_total > 0 else 0

print(f"\nTrend 7: Both Teams Bottom-10 Defense")
print(f"Games matching: {o_trend7_total}")
print(f"Over 240: {o_trend7_over} ({o_trend7_pct:.1f}%)")

# Trend 8: High FT volume
o_trend8_condition = (
    (analysis_df['combined_fta_pct'] > 0.75)
)
o_trend8_games = analysis_df[o_trend8_condition]
o_trend8_over = o_trend8_games['over_240'].sum()
o_trend8_total = len(o_trend8_games)
o_trend8_pct = (o_trend8_over / o_trend8_total * 100) if o_trend8_total > 0 else 0

print(f"\nTrend 8: High FT Volume (Top 25%)")
print(f"Games matching: {o_trend8_total}")
print(f"Over 240: {o_trend8_over} ({o_trend8_pct:.1f}%)")
print(f"Avg FTA: {o_trend8_games['combined_fta'].mean():.1f}")

print("\n" + "="*80)
print("TEAM-SPECIFIC TREND ANALYSIS")
print("="*80)

# Load team names
teams = pd.read_sql_query("SELECT team_id, team_abbreviation, full_name FROM nba_teams", conn)
team_dict = dict(zip(teams['team_id'], teams['team_abbreviation']))

# For each team, look at their under 220 and over 240 patterns
team_trends = []

for team_id in analysis_df['home_team_id'].unique():
    team_name = team_dict.get(team_id, f"Team {team_id}")

    # Get games for this team (home or away)
    team_games = analysis_df[
        (analysis_df['home_team_id'] == team_id) |
        (analysis_df['away_team_id'] == team_id)
    ].copy()

    if len(team_games) < 10:
        continue

    # Check: Does this team go under when facing top-10 defense?
    team_vs_top_def = team_games[
        ((team_games['home_team_id'] == team_id) & (team_games['away_season_def_rtg_rank'] <= 10)) |
        ((team_games['away_team_id'] == team_id) & (team_games['home_season_def_rtg_rank'] <= 10))
    ]

    if len(team_vs_top_def) >= 5:
        under_rate = team_vs_top_def['under_220'].sum() / len(team_vs_top_def) * 100
        if under_rate >= 60:
            team_trends.append({
                'team': team_name,
                'pattern': 'vs Top-10 Defense',
                'trend': 'UNDER 220',
                'hit_rate': under_rate,
                'sample': len(team_vs_top_def),
                'under_count': team_vs_top_def['under_220'].sum()
            })

    # Check: Does this team go over when facing bottom-10 defense?
    team_vs_weak_def = team_games[
        ((team_games['home_team_id'] == team_id) & (team_games['away_season_def_rtg_rank'] >= 21)) |
        ((team_games['away_team_id'] == team_id) & (team_games['home_season_def_rtg_rank'] >= 21))
    ]

    if len(team_vs_weak_def) >= 5:
        over_rate = team_vs_weak_def['over_240'].sum() / len(team_vs_weak_def) * 100
        if over_rate >= 40:
            team_trends.append({
                'team': team_name,
                'pattern': 'vs Bottom-10 Defense',
                'trend': 'OVER 240',
                'hit_rate': over_rate,
                'sample': len(team_vs_weak_def),
                'over_count': team_vs_weak_def['over_240'].sum()
            })

# Sort by hit rate
team_trends = sorted(team_trends, key=lambda x: x['hit_rate'], reverse=True)

# Print top team trends
print("\nTop Team-Specific Trends (min 5 games, strong hit rate):\n")
for i, trend in enumerate(team_trends[:15], 1):
    if trend['trend'] == 'UNDER 220':
        print(f"{i}. {trend['team']} {trend['pattern']}: "
              f"{trend['under_count']}/{trend['sample']} UNDER 220 ({trend['hit_rate']:.1f}%)")
    else:
        print(f"{i}. {trend['team']} {trend['pattern']}: "
              f"{trend['over_count']}/{trend['sample']} OVER 240 ({trend['hit_rate']:.1f}%)")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)

conn.close()
