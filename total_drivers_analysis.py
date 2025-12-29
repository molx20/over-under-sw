"""
NBA Game Totals Analysis - Statistical Drivers Across Total Ranges

Analyzes what drives final game totals across 7 bins (<=200 to 250+)
Focus: 6 core drivers + archetype matchups + opponent rank splits
"""

import sqlite3
import json
from typing import Dict, List, Tuple
from collections import defaultdict
import math

# Database paths
NBA_DB = 'api/data/nba_data.db'
SIMILARITY_DB = 'api/data/team_similarity.db'
PREDICTIONS_DB = 'api/data/predictions.db'

SEASON = '2025-26'

# Total bins
BINS = [
    ('A', 0, 200, '≤200'),
    ('B', 201, 210, '200-210'),
    ('C', 211, 220, '210-220'),
    ('D', 221, 230, '220-230'),
    ('E', 231, 240, '230-240'),
    ('F', 241, 250, '240-250'),
    ('G', 251, 999, '250+')
]


def get_archetype_name(cluster_id: int) -> str:
    """Map cluster ID to archetype name"""
    archetypes = {
        1: "Elite Pace Pushers",
        2: "Paint Dominators",
        3: "Three-Point Hunters",
        4: "Defensive Grinders",
        5: "Balanced High-Assist",
        6: "ISO-Heavy"
    }
    return archetypes.get(cluster_id, f"Cluster {cluster_id}")


def compute_percentile(values: List[float], p: float) -> float:
    """Compute percentile from list of values"""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    d0 = sorted_vals[int(f)] * (c - k)
    d1 = sorted_vals[int(c)] * (k - f)
    return d0 + d1


def fetch_game_data():
    """
    Fetch all completed games with full stats

    Returns list of dicts with:
    - game_id, date, home_team_id, away_team_id
    - final_total
    - all 6 core driver metrics
    - archetype info for both teams
    - opponent rank info for both teams
    """

    conn_nba = sqlite3.connect(NBA_DB)
    conn_nba.row_factory = sqlite3.Row

    # Query to get game-level aggregated stats
    # team_game_logs has one row per team per game, so we join on game_id
    query = """
    SELECT
        h.game_id,
        h.game_date,
        h.team_id as home_team_id,
        a.team_id as away_team_id,

        -- Scores and total
        h.team_pts as home_score,
        a.team_pts as away_score,
        (h.team_pts + a.team_pts) as final_total,

        -- Margin (for blowout risk)
        ABS(h.team_pts - a.team_pts) as margin,

        -- DRIVER 1: Shot conversion
        h.fgm as home_fgm,
        h.fga as home_fga,
        h.fg_pct as home_fg_pct,
        h.fg3m as home_3pm,
        h.fg3a as home_3pa,
        h.ftm as home_ftm,
        a.fgm as away_fgm,
        a.fga as away_fga,
        a.fg_pct as away_fg_pct,
        a.fg3m as away_3pm,
        a.fg3a as away_3pa,
        a.ftm as away_ftm,

        -- DRIVER 2: Paint dominance
        h.points_in_paint as home_pitp,
        a.points_in_paint as away_pitp,

        -- DRIVER 3: Free throw efficiency
        h.fta as home_fta,
        h.ft_pct as home_ft_pct,
        a.fta as away_fta,
        a.ft_pct as away_ft_pct,

        -- DRIVER 5: Turnover conversion
        h.points_off_turnovers as home_pts_off_to,
        a.points_off_turnovers as away_pts_off_to,
        h.turnovers as home_to,
        a.turnovers as away_to,

        -- DRIVER 6: Second-chance efficiency
        h.second_chance_points as home_2nd_chance,
        a.second_chance_points as away_2nd_chance,
        h.offensive_rebounds as home_oreb,
        a.offensive_rebounds as away_oreb,

        -- Context
        h.pace as home_pace,
        a.pace as away_pace

    FROM team_game_logs h
    INNER JOIN team_game_logs a
        ON h.game_id = a.game_id
        AND h.is_home = 1
        AND a.is_home = 0
    WHERE h.season = ?
        AND h.team_pts IS NOT NULL
        AND a.team_pts IS NOT NULL
        AND h.game_date >= '2025-10-21'
    ORDER BY h.game_date, h.game_id
    """

    cursor = conn_nba.cursor()
    cursor.execute(query, (SEASON,))
    rows = cursor.fetchall()

    games = []
    for row in rows:
        # Compute combined metrics
        combined_fgm = (row['home_fgm'] or 0) + (row['away_fgm'] or 0)
        combined_fga = (row['home_fga'] or 0) + (row['away_fga'] or 0)
        combined_fg_pct = combined_fgm / combined_fga if combined_fga > 0 else 0

        combined_3pm = (row['home_3pm'] or 0) + (row['away_3pm'] or 0)
        combined_3pa = (row['home_3pa'] or 0) + (row['away_3pa'] or 0)
        combined_3p_pct = combined_3pm / combined_3pa if combined_3pa > 0 else 0

        combined_ftm = (row['home_ftm'] or 0) + (row['away_ftm'] or 0)
        combined_fta = (row['home_fta'] or 0) + (row['away_fta'] or 0)
        combined_ft_pct = combined_ftm / combined_fta if combined_fta > 0 else 0

        # eFG% = (FGM + 0.5 * 3PM) / FGA
        home_efg = ((row['home_fgm'] or 0) + 0.5 * (row['home_3pm'] or 0)) / (row['home_fga'] or 1) if row['home_fga'] else 0
        away_efg = ((row['away_fgm'] or 0) + 0.5 * (row['away_3pm'] or 0)) / (row['away_fga'] or 1) if row['away_fga'] else 0
        combined_efg = (home_efg + away_efg) / 2

        # TS% approximation: PTS / (2 * (FGA + 0.44 * FTA))
        home_ts = (row['home_score']) / (2 * ((row['home_fga'] or 0) + 0.44 * (row['home_fta'] or 0))) if (row['home_fga'] or 0) + (row['home_fta'] or 0) > 0 else 0
        away_ts = (row['away_score']) / (2 * ((row['away_fga'] or 0) + 0.44 * (row['away_fta'] or 0))) if (row['away_fga'] or 0) + (row['away_fta'] or 0) > 0 else 0
        combined_ts = (home_ts + away_ts) / 2

        game = {
            'game_id': row['game_id'],
            'date': row['game_date'],
            'home_team_id': row['home_team_id'],
            'away_team_id': row['away_team_id'],
            'home_score': row['home_score'],
            'away_score': row['away_score'],
            'final_total': row['final_total'],
            'margin': row['margin'],

            # Driver 1: Shot conversion
            'combined_fg_pct': combined_fg_pct,
            'combined_efg': combined_efg,
            'combined_ts': combined_ts,
            'combined_3p_pct': combined_3p_pct,

            # Driver 2: Paint dominance
            'combined_pitp': (row['home_pitp'] or 0) + (row['away_pitp'] or 0),
            'pitp_rate': ((row['home_pitp'] or 0) + (row['away_pitp'] or 0)) / row['final_total'] if row['final_total'] > 0 else 0,

            # Driver 3: Free throw efficiency
            'ft_points': combined_ftm,
            'combined_fta': combined_fta,
            'combined_ft_pct': combined_ft_pct,
            'ft_rate': combined_fta / combined_fga if combined_fga > 0 else 0,

            # Driver 4: Game symmetry (margin is blowout risk)
            'blowout_10': row['margin'] >= 10,
            'blowout_15': row['margin'] >= 15,
            'blowout_20': row['margin'] >= 20,

            # Driver 5: Turnover conversion
            'points_off_to': (row['home_pts_off_to'] or 0) + (row['away_pts_off_to'] or 0),
            'combined_to': (row['home_to'] or 0) + (row['away_to'] or 0),
            'to_conversion': ((row['home_pts_off_to'] or 0) + (row['away_pts_off_to'] or 0)) / ((row['home_to'] or 0) + (row['away_to'] or 0)) if ((row['home_to'] or 0) + (row['away_to'] or 0)) > 0 else 0,

            # Driver 6: Second-chance efficiency
            'second_chance_pts': (row['home_2nd_chance'] or 0) + (row['away_2nd_chance'] or 0),
            'combined_oreb': (row['home_oreb'] or 0) + (row['away_oreb'] or 0),
            '2nd_chance_conversion': ((row['home_2nd_chance'] or 0) + (row['away_2nd_chance'] or 0)) / ((row['home_oreb'] or 0) + (row['away_oreb'] or 0)) if ((row['home_oreb'] or 0) + (row['away_oreb'] or 0)) > 0 else 0,

            # Context
            'avg_pace': ((row['home_pace'] or 0) + (row['away_pace'] or 0)) / 2 if row['home_pace'] and row['away_pace'] else None
        }

        games.append(game)

    conn_nba.close()

    return games


def enrich_with_archetypes(games: List[Dict]):
    """
    Add archetype info for home and away teams
    Modifies games in-place
    """
    conn_sim = sqlite3.connect(SIMILARITY_DB)
    conn_sim.row_factory = sqlite3.Row
    cursor = conn_sim.cursor()

    # Get all cluster assignments for this season
    cursor.execute("""
        SELECT team_id, cluster_id
        FROM team_cluster_assignments
        WHERE season = ?
    """, (SEASON,))

    cluster_map = {}
    for row in cursor.fetchall():
        cluster_map[row['team_id']] = row['cluster_id']

    conn_sim.close()

    # Enrich games
    for game in games:
        game['home_archetype'] = cluster_map.get(game['home_team_id'])
        game['away_archetype'] = cluster_map.get(game['away_team_id'])
        game['home_archetype_name'] = get_archetype_name(game['home_archetype']) if game['home_archetype'] else 'Unknown'
        game['away_archetype_name'] = get_archetype_name(game['away_archetype']) if game['away_archetype'] else 'Unknown'


def enrich_with_opponent_ranks(games: List[Dict]):
    """
    Add opponent rank info from team_game_history
    Modifies games in-place
    """
    conn_pred = sqlite3.connect(PREDICTIONS_DB)
    conn_pred.row_factory = sqlite3.Row
    cursor = conn_pred.cursor()

    # Get opponent ranks for all games
    cursor.execute("""
        SELECT
            game_id,
            team_id,
            opp_ppg_rank,
            opp_pace_rank,
            opp_off_rtg_rank,
            opp_def_rtg_rank
        FROM team_game_history
    """)

    rank_map = {}  # (game_id, team_id) -> rank dict
    for row in cursor.fetchall():
        key = (row['game_id'], row['team_id'])
        rank_map[key] = {
            'opp_ppg_rank': row['opp_ppg_rank'],
            'opp_pace_rank': row['opp_pace_rank'],
            'opp_off_rtg_rank': row['opp_off_rtg_rank'],
            'opp_def_rtg_rank': row['opp_def_rtg_rank']
        }

    conn_pred.close()

    # Enrich games
    for game in games:
        home_key = (game['game_id'], game['home_team_id'])
        away_key = (game['game_id'], game['away_team_id'])

        game['home_opp_ranks'] = rank_map.get(home_key, {})
        game['away_opp_ranks'] = rank_map.get(away_key, {})


def bucket_rank(rank: int) -> str:
    """Convert rank (1-30) to tier bucket"""
    if rank is None:
        return 'Unknown'
    if rank <= 10:
        return 'Top 10'
    elif rank <= 20:
        return 'Mid (11-20)'
    else:
        return 'Bottom (21-30)'


def assign_bins(games: List[Dict]):
    """Assign each game to a total bin (A-G)"""
    for game in games:
        total = game['final_total']
        for bin_letter, min_val, max_val, label in BINS:
            if min_val <= total <= max_val:
                game['bin'] = bin_letter
                game['bin_label'] = label
                break


def compute_bin_statistics(games: List[Dict]):
    """
    Compute comprehensive statistics per bin

    Returns dict with bin_letter as key and stats as value
    """

    # Group games by bin
    bins_dict = defaultdict(list)
    for game in games:
        if 'bin' in game:
            bins_dict[game['bin']].append(game)

    results = {}

    # Compute baseline probabilities (for lift calculation)
    total_games = len(games)
    baseline_probs = {}
    for bin_letter in bins_dict.keys():
        baseline_probs[bin_letter] = len(bins_dict[bin_letter]) / total_games

    # Feature names for the 6 core drivers
    core_features = [
        ('combined_efg', 'eFG%', 'percentage'),
        ('combined_ts', 'TS%', 'percentage'),
        ('combined_pitp', 'Paint Points', 'points'),
        ('ft_points', 'FT Points', 'points'),
        ('margin', 'Margin (Blowout Risk)', 'points'),
        ('points_off_to', 'Points off TO', 'points'),
        ('second_chance_pts', '2nd Chance Points', 'points')
    ]

    for bin_letter, bin_games in bins_dict.items():
        bin_stats = {
            'bin': bin_letter,
            'bin_label': next(label for letter, _, _, label in BINS if letter == bin_letter),
            'count': len(bin_games),
            'pct_of_season': len(bin_games) / total_games * 100,
            'core_drivers': {},
            'archetype_analysis': {},
            'rank_analysis': {}
        }

        # ===========================================
        # PART 1: CORE DRIVERS ANALYSIS
        # ===========================================

        for feature_name, display_name, value_type in core_features:
            values = [g[feature_name] for g in bin_games if feature_name in g and g[feature_name] is not None]

            if not values:
                continue

            # Compute percentiles
            p25 = compute_percentile(values, 0.25)
            p50 = compute_percentile(values, 0.50)
            p75 = compute_percentile(values, 0.75)
            mean = sum(values) / len(values)

            # Compute lift vs season average
            all_values = [g[feature_name] for g in games if feature_name in g and g[feature_name] is not None]
            season_mean = sum(all_values) / len(all_values) if all_values else 0
            lift = ((mean - season_mean) / season_mean * 100) if season_mean > 0 else 0

            bin_stats['core_drivers'][feature_name] = {
                'name': display_name,
                'mean': round(mean, 3),
                'median': round(p50, 3),
                'p25': round(p25, 3),
                'p75': round(p75, 3),
                'lift_pct': round(lift, 1)
            }

        # Sort drivers by absolute lift to identify top 3
        sorted_drivers = sorted(
            bin_stats['core_drivers'].items(),
            key=lambda x: abs(x[1]['lift_pct']),
            reverse=True
        )
        bin_stats['top_3_drivers'] = [
            {
                'feature': k,
                'name': v['name'],
                'lift': v['lift_pct']
            }
            for k, v in sorted_drivers[:3]
        ]

        # ===========================================
        # PART 2: ARCHETYPE MATCHUP ANALYSIS
        # ===========================================

        archetype_matchups = defaultdict(int)
        for game in bin_games:
            if game.get('home_archetype') and game.get('away_archetype'):
                # Create matchup key (order-independent for now, can change)
                matchup = f"{game['home_archetype_name']} vs {game['away_archetype_name']}"
                archetype_matchups[matchup] += 1

        # Compute lift for each matchup
        archetype_lifts = []
        for matchup, count in archetype_matchups.items():
            # Count total games with this matchup
            total_matchup_games = sum(1 for g in games
                                     if f"{g.get('home_archetype_name', '')} vs {g.get('away_archetype_name', '')}" == matchup)

            if total_matchup_games > 0:
                prob_bin_given_matchup = count / total_matchup_games
                baseline = baseline_probs[bin_letter]
                lift = (prob_bin_given_matchup / baseline - 1) * 100 if baseline > 0 else 0

                archetype_lifts.append({
                    'matchup': matchup,
                    'count_in_bin': count,
                    'total_matchup_games': total_matchup_games,
                    'prob': round(prob_bin_given_matchup * 100, 1),
                    'lift': round(lift, 1)
                })

        # Sort by lift
        archetype_lifts.sort(key=lambda x: abs(x['lift']), reverse=True)
        bin_stats['archetype_analysis']['top_matchups'] = archetype_lifts[:5]

        # ===========================================
        # PART 3: OPPONENT RANK SPLITS ANALYSIS
        # ===========================================

        rank_categories = [
            'opp_ppg_rank',
            'opp_pace_rank',
            'opp_off_rtg_rank',
            'opp_def_rtg_rank'
        ]

        for rank_cat in rank_categories:
            # Aggregate both home and away opponent ranks
            rank_buckets = defaultdict(int)

            for game in bin_games:
                # Home team's opponent (away team) rank
                home_opp_rank = game.get('home_opp_ranks', {}).get(rank_cat)
                if home_opp_rank:
                    bucket = bucket_rank(home_opp_rank)
                    rank_buckets[bucket] += 1

                # Away team's opponent (home team) rank
                away_opp_rank = game.get('away_opp_ranks', {}).get(rank_cat)
                if away_opp_rank:
                    bucket = bucket_rank(away_opp_rank)
                    rank_buckets[bucket] += 1

            # Compute lift for each bucket
            bucket_lifts = []
            for bucket, count in rank_buckets.items():
                # Total season occurrences of this bucket in this category
                total_bucket = 0
                for g in games:
                    if g.get('home_opp_ranks', {}).get(rank_cat):
                        if bucket_rank(g['home_opp_ranks'][rank_cat]) == bucket:
                            total_bucket += 1
                    if g.get('away_opp_ranks', {}).get(rank_cat):
                        if bucket_rank(g['away_opp_ranks'][rank_cat]) == bucket:
                            total_bucket += 1

                if total_bucket > 0:
                    # Expected count in this bin if no correlation
                    expected = total_bucket * baseline_probs[bin_letter] * 2  # *2 because we count both teams
                    lift = (count / expected - 1) * 100 if expected > 0 else 0

                    bucket_lifts.append({
                        'bucket': bucket,
                        'count': count,
                        'lift': round(lift, 1)
                    })

            bucket_lifts.sort(key=lambda x: abs(x['lift']), reverse=True)
            bin_stats['rank_analysis'][rank_cat] = bucket_lifts

        results[bin_letter] = bin_stats

    return results


def generate_cross_bin_insights(bin_results: Dict):
    """
    Identify what changes as you move across bins
    """

    insights = []

    # Compare extreme bins
    if 'A' in bin_results and 'G' in bin_results:
        low_bin = bin_results['A']
        high_bin = bin_results['G']

        # What flips from low to high?
        insights.append("## What Separates Low Totals (≤200) from Extreme Totals (250+)")

        # Compare top drivers
        for driver_key in ['combined_efg', 'combined_pitp', 'ft_points']:
            if driver_key in low_bin['core_drivers'] and driver_key in high_bin['core_drivers']:
                low_val = low_bin['core_drivers'][driver_key]['mean']
                high_val = high_bin['core_drivers'][driver_key]['mean']
                diff = high_val - low_val
                pct_change = (diff / low_val * 100) if low_val > 0 else 0

                insights.append(f"- {low_bin['core_drivers'][driver_key]['name']}: {low_val:.3f} → {high_val:.3f} (+{pct_change:.1f}%)")

    return "\n".join(insights)


def generate_ui_recommendations(bin_results: Dict):
    """
    Produce actionable UI recommendations
    """

    # Collect all driver lifts across all bins
    driver_lifts = defaultdict(list)
    for bin_stats in bin_results.values():
        for driver_key, driver_data in bin_stats['core_drivers'].items():
            driver_lifts[driver_key].append(abs(driver_data['lift_pct']))

    # Average absolute lift for each driver
    driver_importance = {}
    for driver_key, lifts in driver_lifts.items():
        avg_lift = sum(lifts) / len(lifts) if lifts else 0
        driver_importance[driver_key] = avg_lift

    # Sort by importance
    sorted_drivers = sorted(driver_importance.items(), key=lambda x: x[1], reverse=True)

    # Check archetype importance
    archetype_lifts = []
    for bin_stats in bin_results.values():
        for matchup_data in bin_stats['archetype_analysis'].get('top_matchups', []):
            archetype_lifts.append(abs(matchup_data['lift']))

    avg_archetype_lift = sum(archetype_lifts) / len(archetype_lifts) if archetype_lifts else 0

    # Check rank category importance
    rank_lifts = defaultdict(list)
    for bin_stats in bin_results.values():
        for rank_cat, bucket_data in bin_stats['rank_analysis'].items():
            for bucket in bucket_data:
                rank_lifts[rank_cat].append(abs(bucket['lift']))

    rank_importance = {}
    for rank_cat, lifts in rank_lifts.items():
        rank_importance[rank_cat] = sum(lifts) / len(lifts) if lifts else 0

    # Generate recommendations
    output = []
    output.append("# UI RECOMMENDATIONS")
    output.append("")
    output.append("## A) Decision View (MAX 6 metrics)")
    output.append("Show these on the main decision screen:")
    output.append("")

    # Top 4 drivers
    for i, (driver_key, lift) in enumerate(sorted_drivers[:4], 1):
        # Get display name from any bin
        display_name = next((bin_stats['core_drivers'][driver_key]['name']
                           for bin_stats in bin_results.values()
                           if driver_key in bin_stats['core_drivers']), driver_key)
        output.append(f"{i}. **{display_name}** (avg lift: {lift:.1f}%)")

    output.append(f"5. **Final Total Prediction** (obviously)")
    output.append(f"6. **Margin Risk Indicator** (blowout = lower total)")
    output.append("")

    output.append("## B) Why View (Collapsible)")
    output.append("Show behind a 'Why' button:")
    output.append("")
    output.append(f"- **Archetype Matchup Impact** (avg lift: {avg_archetype_lift:.1f}%)")

    for rank_cat, lift in sorted(rank_importance.items(), key=lambda x: x[1], reverse=True):
        cat_name = rank_cat.replace('opp_', 'Opponent ').replace('_', ' ').title()
        output.append(f"- **{cat_name} Split** (avg lift: {lift:.1f}%)")

    output.append("- Supporting stats (3P%, TO conversion, 2nd chance)")
    output.append("")

    output.append("## C) Deep Dive")
    output.append("Full analysis view:")
    output.append("")
    output.append("- Similar opponents table with historical totals")
    output.append("- Archetype vs archetype performance matrix")
    output.append("- Full rank-split breakdown charts")
    output.append("- Game-by-game trends")
    output.append("")

    output.append("## D) Remove/Deprioritize")
    output.append("Low-lift metrics to hide or remove:")
    output.append("")

    # Bottom drivers
    for driver_key, lift in sorted_drivers[-2:]:
        if lift < 5.0:  # Threshold for "low lift"
            display_name = next((bin_stats['core_drivers'][driver_key]['name']
                               for bin_stats in bin_results.values()
                               if driver_key in bin_stats['core_drivers']), driver_key)
            output.append(f"- {display_name} (only {lift:.1f}% avg lift)")

    # Low-lift rank categories
    for rank_cat, lift in rank_importance.items():
        if lift < 10.0:
            cat_name = rank_cat.replace('opp_', 'Opponent ').replace('_', ' ').title()
            output.append(f"- {cat_name} (only {lift:.1f}% avg lift)")

    return "\n".join(output)


def print_full_report(games: List[Dict], bin_results: Dict):
    """
    Print comprehensive report
    """

    print("=" * 80)
    print("NBA GAME TOTALS ANALYSIS - STATISTICAL DRIVERS")
    print("=" * 80)
    print()

    # 1. Data Completeness
    print("## 1. DATA COMPLETENESS")
    print()
    print(f"**Season:** {SEASON}")
    print(f"**Date Filter:** Games from 2025-10-21 onwards (excludes preseason)")
    print(f"**Total Games Analyzed:** {len(games)}")
    print()
    print("**Tables Used:**")
    print(f"- nba_data.db::team_game_logs (primary game stats)")
    print(f"- team_similarity.db::team_cluster_assignments (archetypes)")
    print(f"- predictions.db::team_game_history (opponent ranks)")
    print()
    print("**Available Metrics:**")
    print("- Shot Conversion: FG%, eFG%, TS% ✓")
    print("- Paint Dominance: Points in Paint ✓")
    print("- Free Throws: FTM, FTA, FT% ✓")
    print("- Game Symmetry: Margin ✓")
    print("- Turnover Conversion: Points off TO ✓")
    print("- Second-Chance: 2nd Chance Points, OREB ✓")
    print("- Archetypes: 6 cluster assignments ✓")
    print("- Opponent Ranks: PPG, Pace, Off Rtg, Def Rtg ✓")
    print()
    print("**Missing/Derived:**")
    print("- Rim attempt rate: Not available (using Paint Points as proxy)")
    print("- True Shooting: Derived from formula (PTS / (2 * (FGA + 0.44*FTA)))")
    print()

    # 2. Season-wide distributions
    print("## 2. SEASON-WIDE DISTRIBUTIONS")
    print()

    features_to_show = [
        ('final_total', 'Final Total'),
        ('combined_efg', 'eFG%'),
        ('combined_ts', 'TS%'),
        ('combined_pitp', 'Paint Points'),
        ('ft_points', 'FT Points'),
        ('margin', 'Margin'),
        ('points_off_to', 'Points off TO'),
        ('second_chance_pts', '2nd Chance Pts')
    ]

    for feature, name in features_to_show:
        values = [g[feature] for g in games if g.get(feature) is not None]
        if values:
            print(f"**{name}:**")
            print(f"  Mean: {sum(values)/len(values):.2f} | "
                  f"Median: {compute_percentile(values, 0.5):.2f} | "
                  f"P25: {compute_percentile(values, 0.25):.2f} | "
                  f"P75: {compute_percentile(values, 0.75):.2f}")
    print()

    # 3. Bin Results
    print("## 3. BIN RESULTS (A-G)")
    print()

    for bin_letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
        if bin_letter not in bin_results:
            continue

        bin_stats = bin_results[bin_letter]

        print(f"### BIN {bin_letter}: {bin_stats['bin_label']}")
        print(f"**Sample Size:** {bin_stats['count']} games ({bin_stats['pct_of_season']:.1f}% of season)")
        print()

        print("**Top 3 Core Drivers (by lift):**")
        for i, driver in enumerate(bin_stats['top_3_drivers'], 1):
            print(f"  {i}. {driver['name']}: {driver['lift']:+.1f}% lift")
        print()

        print("**Top Archetype Matchups:**")
        for matchup in bin_stats['archetype_analysis']['top_matchups'][:3]:
            print(f"  - {matchup['matchup']}: {matchup['count_in_bin']} games, {matchup['lift']:+.1f}% lift")
        print()

        print("**Opponent Rank Splits (strongest category):**")
        # Find category with highest lift
        best_cat = None
        best_lift = 0
        for rank_cat, bucket_data in bin_stats['rank_analysis'].items():
            if bucket_data:
                max_lift = max(abs(b['lift']) for b in bucket_data)
                if max_lift > best_lift:
                    best_lift = max_lift
                    best_cat = rank_cat

        if best_cat:
            cat_name = best_cat.replace('opp_', 'Opp ').replace('_', ' ').title()
            print(f"  {cat_name}:")
            for bucket in bin_stats['rank_analysis'][best_cat]:
                print(f"    - {bucket['bucket']}: {bucket['count']} occurrences, {bucket['lift']:+.1f}% lift")
        print()

        # Typical ranges
        print("**Typical Ranges (P25-P75):**")
        for driver in bin_stats['top_3_drivers'][:3]:
            key = driver['feature']
            if key in bin_stats['core_drivers']:
                d = bin_stats['core_drivers'][key]
                print(f"  - {d['name']}: {d['p25']:.3f} - {d['p75']:.3f}")
        print()
        print("-" * 80)
        print()

    # 4. Cross-bin insights
    print("## 4. CROSS-BIN INSIGHTS")
    print()
    print(generate_cross_bin_insights(bin_results))
    print()

    # 5. UI Recommendations
    print()
    print(generate_ui_recommendations(bin_results))
    print()
    print("=" * 80)


def main():
    """Main analysis pipeline"""

    print("Loading game data...")
    games = fetch_game_data()
    print(f"Loaded {len(games)} games")

    print("Enriching with archetype data...")
    enrich_with_archetypes(games)

    print("Enriching with opponent rank data...")
    enrich_with_opponent_ranks(games)

    print("Assigning bins...")
    assign_bins(games)

    print("Computing bin statistics...")
    bin_results = compute_bin_statistics(games)

    print()
    print_full_report(games, bin_results)

    # Save detailed results to JSON for further analysis
    output_file = 'total_drivers_analysis_results.json'
    with open(output_file, 'w') as f:
        # Convert to serializable format
        serializable_results = {}
        for bin_letter, bin_data in bin_results.items():
            serializable_results[bin_letter] = bin_data

        json.dump({
            'season': SEASON,
            'total_games': len(games),
            'bin_results': serializable_results
        }, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")


if __name__ == '__main__':
    main()
