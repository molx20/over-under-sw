"""
Team Similarity Engine - Core Module

Analyzes playstyle profiles of all NBA teams using season stats and box score data.
Computes similarity scores, assigns clusters, tracks performance vs cluster types.

100% deterministic - no machine learning.
"""

import json
import math
import sqlite3
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from api.utils.db_schema_similarity import get_connection
from api.utils.db_queries import get_all_teams, get_team_by_id


# Feature weights for distance calculation
FEATURE_WEIGHTS = {
    'pace': 2.0,
    'pace_variance': 1.5,
    'three_pt_rate': 1.8,
    'midrange_rate': 1.0,
    'paint_scoring_rate': 1.8,
    'rim_attempt_rate': 1.5,
    'ast_ratio': 1.5,
    'ast_to_ratio': 1.2,
    'turnover_rate': 1.0,
    'fta_rate': 1.0,
    'fouls_drawn_rate': 0.8,
    'fouls_committed_rate': 0.8,
    'oreb_pct': 1.0,
    'dreb_pct': 1.0,
    'def_paint_pts_allowed': 1.2,
    'def_three_pct_allowed': 1.2,
    'steals_per_game': 1.2,
    'blocks_per_game': 1.2,
    'fastbreak_pts_rate': 1.3,
    'second_chance_pts_rate': 1.0
}


def normalize_value(value: float, min_val: float, max_val: float) -> float:
    """Min-max normalization to 0-1 range"""
    if max_val == min_val:
        return 0.5  # If no variance, return middle value
    return (value - min_val) / (max_val - min_val)


def compute_team_feature_vector(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Compute 20-dimensional feature vector for a team.

    Returns:
        {
            'team_id': int,
            'features': [float, ...],  # 20 values, 0-1 normalized
            'feature_names': [str, ...],
            'season': str
        }
    """
    import os
    import sqlite3

    # Get team season stats from NBA database
    nba_db_path = os.path.join(os.path.dirname(__file__), '../data/nba_data.db')
    conn = sqlite3.connect(nba_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch season averages
    cursor.execute("""
        SELECT
            pace, off_rtg, def_rtg,
            fg3a, fg3m, fg3_pct,
            fg2a + fg3a as fga, fg2m + fg3m as fgm,
            fta, ftm,
            assists, turnovers,
            rebounds, steals, blocks,
            ppg
        FROM team_season_stats
        WHERE team_id = ? AND season = ? AND split_type = 'overall'
    """, (team_id, season))

    stats = cursor.fetchone()
    if not stats:
        print(f"[Similarity] No season stats for team {team_id}")
        conn.close()
        return None

    # Fetch box score aggregates AND game-by-game data for variance/advanced stats
    cursor.execute("""
        SELECT
            AVG(points_in_paint) as avg_paint_pts,
            AVG(fast_break_points) as avg_fastbreak_pts,
            AVG(second_chance_points) as avg_second_chance_pts,
            AVG(offensive_rebounds) as avg_oreb,
            AVG(defensive_rebounds) as avg_dreb,
            AVG(opp_offensive_rebounds) as avg_opp_oreb,
            AVG(opp_defensive_rebounds) as avg_opp_dreb,
            SUM(opp_fg3m) * 1.0 / NULLIF(SUM(opp_fg3a), 0) as def_three_pct,
            AVG(team_pts) as avg_pts
        FROM team_game_logs
        WHERE team_id = ? AND season = ?
        GROUP BY team_id
    """, (team_id, season))

    box_stats = cursor.fetchone()

    # Fetch game-by-game pace for variance calculation
    cursor.execute("""
        SELECT pace
        FROM team_game_logs
        WHERE team_id = ? AND season = ? AND pace IS NOT NULL
        ORDER BY game_date
    """, (team_id, season))

    pace_values = [row[0] for row in cursor.fetchall()]

    conn.close()

    # Extract values with defaults
    pace = stats[0] if stats[0] else 98.0
    ortg = stats[1] if stats[1] else 110.0
    drtg = stats[2] if stats[2] else 110.0
    fg3a = stats[3] if stats[3] else 30.0
    fg3m = stats[4] if stats[4] else 11.0
    fga = stats[6] if stats[6] else 85.0
    fgm = stats[7] if stats[7] else 38.0
    fta = stats[8] if stats[8] else 20.0
    ftm = stats[9] if stats[9] else 15.0
    ast = stats[10] if stats[10] else 23.0
    tov = stats[11] if stats[11] else 13.0
    reb = stats[12] if stats[12] else 43.0
    stl = stats[13] if stats[13] else 7.0
    blk = stats[14] if stats[14] else 5.0
    pts_pg = stats[15] if stats[15] else 110.0

    paint_pts = box_stats[0] if box_stats and box_stats[0] else 50.0
    fastbreak_pts = box_stats[1] if box_stats and box_stats[1] else 12.0
    second_chance_pts = box_stats[2] if box_stats and box_stats[2] else 12.0
    avg_oreb = box_stats[3] if box_stats and box_stats[3] else 10.0
    avg_dreb = box_stats[4] if box_stats and box_stats[4] else 33.0
    avg_opp_oreb = box_stats[5] if box_stats and box_stats[5] else 10.0
    avg_opp_dreb = box_stats[6] if box_stats and box_stats[6] else 33.0
    def_three_pct = box_stats[7] if box_stats and box_stats[7] else 0.36
    avg_pts = box_stats[8] if box_stats and box_stats[8] else 110.0

    # ===== REAL FEATURE COMPUTATIONS (replacing 7 placeholders) =====

    # 1) pace_variance: Standard deviation of pace from game logs
    # Use STDDEV if >= 5 games, else 0.0 (insufficient data)
    if len(pace_values) >= 5:
        pace_mean = sum(pace_values) / len(pace_values)
        pace_variance = math.sqrt(sum((p - pace_mean) ** 2 for p in pace_values) / len(pace_values))
    else:
        pace_variance = 0.0

    # 2) oreb_pct: Offensive rebound percentage
    # Formula: OREB / (OREB + Opp_DREB)
    oreb_opportunities = avg_oreb + avg_opp_dreb
    oreb_pct = avg_oreb / oreb_opportunities if oreb_opportunities > 0 else 0.23

    # 3) dreb_pct: Defensive rebound percentage
    # Formula: DREB / (DREB + Opp_OREB)
    dreb_opportunities = avg_dreb + avg_opp_oreb
    dreb_pct = avg_dreb / dreb_opportunities if dreb_opportunities > 0 else 0.77

    # 4) def_three_pct_allowed: Opponent 3PT% allowed
    # Already computed from game logs as SUM(opp_fg3m) / SUM(opp_fg3a)
    # def_three_pct is from box_stats query above

    # 5) rim_attempt_rate: PROXY using points in paint
    # Since we lack shot zone data, estimate rim attempts as:
    # rim_attempt_rate ≈ (points_in_paint / team_pts)
    # This assumes paint scoring correlates with rim attempts
    rim_attempt_rate = paint_pts / avg_pts if avg_pts > 0 else 0.30
    # Clamp to [0, 1]
    rim_attempt_rate = max(0.0, min(1.0, rim_attempt_rate))

    # 6) midrange_rate: PROXY computed as residual
    # midrange ≈ 1 - three_pt_rate - rim_attempt_rate
    # Since 3PT% = FG3A/FGA and rim_rate is paint_pts/pts, this is imperfect but best available
    three_pt_rate = fg3a / fga if fga > 0 else 0.35
    midrange_rate = 1.0 - three_pt_rate - rim_attempt_rate
    # Clamp to [0, 1]
    midrange_rate = max(0.0, min(1.0, midrange_rate))

    # 7) fouls_committed_rate: NO PF data available
    # Proxy: Use turnover rate as weak correlate (high TO teams often play aggressive)
    # Better option: Use league average constant 0.20 with TODO
    # Going with constant since no PF data exists
    fouls_committed_rate = 0.20  # TODO: Add PF column to team_game_logs for real calculation

    # ===== END REAL FEATURE COMPUTATIONS =====

    # Compute remaining features (unchanged)
    paint_scoring_rate = paint_pts / pts_pg if pts_pg > 0 else 0.45
    ast_ratio = ast / fgm if fgm > 0 else 0.6
    ast_to_ratio = ast / tov if tov > 0 else 1.7
    turnover_rate = tov / pace if pace > 0 else 0.13
    fta_rate = fta / fga if fga > 0 else 0.23
    fouls_drawn_rate = fta / pace if pace > 0 else 0.20
    fastbreak_pts_rate = fastbreak_pts / pts_pg if pts_pg > 0 else 0.12
    second_chance_pts_rate = second_chance_pts / pts_pg if pts_pg > 0 else 0.12

    # Build feature vector (will normalize later across all teams)
    raw_features = {
        'pace': pace,
        'pace_variance': pace_variance,  # REAL: STDDEV of pace from game logs
        'three_pt_rate': three_pt_rate,
        'midrange_rate': midrange_rate,  # REAL: Residual proxy (1 - 3pt - rim)
        'paint_scoring_rate': paint_scoring_rate,
        'rim_attempt_rate': rim_attempt_rate,  # REAL: Proxy (paint_pts / pts)
        'ast_ratio': ast_ratio,
        'ast_to_ratio': ast_to_ratio,
        'turnover_rate': turnover_rate,
        'fta_rate': fta_rate,
        'fouls_drawn_rate': fouls_drawn_rate,
        'fouls_committed_rate': fouls_committed_rate,  # Still placeholder (no PF data)
        'oreb_pct': oreb_pct,  # REAL: OREB / (OREB + Opp_DREB)
        'dreb_pct': dreb_pct,  # REAL: DREB / (DREB + Opp_OREB)
        'def_paint_pts_allowed': 115 - drtg,  # Proxy, inverted
        'def_three_pct_allowed': def_three_pct,  # REAL: SUM(opp_fg3m) / SUM(opp_fg3a)
        'steals_per_game': stl,
        'blocks_per_game': blk,
        'fastbreak_pts_rate': fastbreak_pts_rate,
        'second_chance_pts_rate': second_chance_pts_rate
    }

    return {
        'team_id': team_id,
        'raw_features': raw_features,
        'season': season
    }


def compute_team_feature_vector_vs_cluster(
    team_id: int,
    season: str,
    window_mode: str,
    opponent_cluster_id: int
) -> Optional[Dict]:
    """
    Compute feature vector for a team using ONLY games vs a specific opponent cluster.

    Args:
        team_id: Team NBA ID
        season: Season string (e.g., '2025-26')
        window_mode: 'season', 'last20', 'last10'
        opponent_cluster_id: Cluster ID of opponents to filter by (1-6)

    Returns:
        {
            'team_id': int,
            'raw_features': {...},
            'season': str,
            'opponent_cluster_id': int,
            'games_used': int,
            'date_range': (min_date, max_date)
        }
        or None if insufficient games (<5)
    """
    import os
    import sqlite3

    nba_db_path = os.path.join(os.path.dirname(__file__), '../data/nba_data.db')
    sim_db_path = os.path.join(os.path.dirname(__file__), '../data/team_similarity.db')

    nba_conn = sqlite3.connect(nba_db_path)
    nba_conn.row_factory = sqlite3.Row
    nba_cursor = nba_conn.cursor()

    sim_conn = get_connection()
    sim_cursor = sim_conn.cursor()

    # Step 1: Get opponent team IDs that belong to the target cluster
    sim_cursor.execute("""
        SELECT team_id
        FROM team_cluster_assignments
        WHERE cluster_id = ? AND season = ?
    """, (opponent_cluster_id, season))

    opponent_team_ids = [row[0] for row in sim_cursor.fetchall()]
    sim_conn.close()

    if not opponent_team_ids:
        nba_conn.close()
        return None

    # Step 2: Fetch games where opponent is in that cluster
    placeholders = ','.join('?' * len(opponent_team_ids))
    query = f"""
        SELECT game_id, game_date, team_pts, opp_pts, pace,
               fg3a, fg3m, fga, fgm, fta, ftm,
               assists, turnovers, steals, blocks,
               offensive_rebounds, defensive_rebounds,
               opp_offensive_rebounds, opp_defensive_rebounds,
               opp_fg3m, opp_fg3a,
               points_in_paint, fast_break_points, second_chance_points
        FROM team_game_logs
        WHERE team_id = ? AND season = ?
          AND opponent_team_id IN ({placeholders})
          AND team_pts IS NOT NULL
        ORDER BY game_date DESC
    """

    params = [team_id, season] + opponent_team_ids
    nba_cursor.execute(query, params)
    games = nba_cursor.fetchall()

    # Apply window mode
    if window_mode == 'last20':
        games = games[:20]
    elif window_mode == 'last10':
        games = games[:10]
    # else 'season' = use all

    games_count = len(games)

    # Step 3: Check minimum games threshold
    if games_count < 5:
        nba_conn.close()
        return None

    # Step 4: Aggregate stats from filtered games
    if games_count == 0:
        nba_conn.close()
        return None

    # Calculate averages
    total_pts = sum(g['team_pts'] for g in games)
    avg_pace = sum(g['pace'] for g in games if g['pace']) / games_count
    avg_fg3a = sum(g['fg3a'] for g in games if g['fg3a']) / games_count
    avg_fg3m = sum(g['fg3m'] for g in games if g['fg3m']) / games_count
    avg_fga = sum(g['fga'] for g in games if g['fga']) / games_count
    avg_fgm = sum(g['fgm'] for g in games if g['fgm']) / games_count
    avg_fta = sum(g['fta'] for g in games if g['fta']) / games_count
    avg_ast = sum(g['assists'] for g in games if g['assists']) / games_count
    avg_tov = sum(g['turnovers'] for g in games if g['turnovers']) / games_count
    avg_stl = sum(g['steals'] for g in games if g['steals']) / games_count
    avg_blk = sum(g['blocks'] for g in games if g['blocks']) / games_count
    avg_pts = total_pts / games_count

    avg_oreb = sum(g['offensive_rebounds'] for g in games if g['offensive_rebounds']) / games_count
    avg_dreb = sum(g['defensive_rebounds'] for g in games if g['defensive_rebounds']) / games_count
    avg_opp_oreb = sum(g['opp_offensive_rebounds'] for g in games if g['opp_offensive_rebounds']) / games_count
    avg_opp_dreb = sum(g['opp_defensive_rebounds'] for g in games if g['opp_defensive_rebounds']) / games_count

    avg_opp_fg3m = sum(g['opp_fg3m'] for g in games if g['opp_fg3m']) / games_count
    avg_opp_fg3a = sum(g['opp_fg3a'] for g in games if g['opp_fg3a']) / games_count

    avg_paint_pts = sum(g['points_in_paint'] for g in games if g['points_in_paint']) / games_count
    avg_fastbreak = sum(g['fast_break_points'] for g in games if g['fast_break_points']) / games_count
    avg_second_chance = sum(g['second_chance_points'] for g in games if g['second_chance_points']) / games_count

    # Pace variance
    pace_values = [g['pace'] for g in games if g['pace']]
    if len(pace_values) >= 5:
        pace_mean = sum(pace_values) / len(pace_values)
        pace_variance = math.sqrt(sum((p - pace_mean) ** 2 for p in pace_values) / len(pace_values))
    else:
        pace_variance = 0.0

    # Calculate proxy defensive rating (simplified: avg opponent pts allowed)
    avg_opp_pts = sum(g['opp_pts'] for g in games) / games_count
    # Proxy: higher opp_pts = worse defense, so invert for def_paint_pts_allowed
    def_paint_pts_allowed = 115 - (avg_opp_pts * 110 / 115)  # Rough proxy

    nba_conn.close()

    # Step 5: Compute raw features (same 20D vector as global)
    three_pt_rate = avg_fg3a / avg_fga if avg_fga > 0 else 0.35
    paint_scoring_rate = avg_paint_pts / avg_pts if avg_pts > 0 else 0.45
    rim_attempt_rate = avg_paint_pts / avg_pts if avg_pts > 0 else 0.30
    rim_attempt_rate = max(0.0, min(1.0, rim_attempt_rate))
    midrange_rate = 1.0 - three_pt_rate - rim_attempt_rate
    midrange_rate = max(0.0, min(1.0, midrange_rate))

    ast_ratio = avg_ast / avg_fgm if avg_fgm > 0 else 0.6
    ast_to_ratio = avg_ast / avg_tov if avg_tov > 0 else 1.7
    turnover_rate = avg_tov / avg_pace if avg_pace > 0 else 0.13
    fta_rate = avg_fta / avg_fga if avg_fga > 0 else 0.23
    fouls_drawn_rate = avg_fta / avg_pace if avg_pace > 0 else 0.20

    oreb_opportunities = avg_oreb + avg_opp_dreb
    oreb_pct = avg_oreb / oreb_opportunities if oreb_opportunities > 0 else 0.23

    dreb_opportunities = avg_dreb + avg_opp_oreb
    dreb_pct = avg_dreb / dreb_opportunities if dreb_opportunities > 0 else 0.77

    def_three_pct_allowed = avg_opp_fg3m / avg_opp_fg3a if avg_opp_fg3a > 0 else 0.36

    fastbreak_pts_rate = avg_fastbreak / avg_pts if avg_pts > 0 else 0.12
    second_chance_pts_rate = avg_second_chance / avg_pts if avg_pts > 0 else 0.12

    raw_features = {
        'pace': avg_pace,
        'pace_variance': pace_variance,
        'three_pt_rate': three_pt_rate,
        'midrange_rate': midrange_rate,
        'paint_scoring_rate': paint_scoring_rate,
        'rim_attempt_rate': rim_attempt_rate,
        'ast_ratio': ast_ratio,
        'ast_to_ratio': ast_to_ratio,
        'turnover_rate': turnover_rate,
        'fta_rate': fta_rate,
        'fouls_drawn_rate': fouls_drawn_rate,
        'fouls_committed_rate': 0.20,  # Placeholder
        'oreb_pct': oreb_pct,
        'dreb_pct': dreb_pct,
        'def_paint_pts_allowed': def_paint_pts_allowed,
        'def_three_pct_allowed': def_three_pct_allowed,
        'steals_per_game': avg_stl,
        'blocks_per_game': avg_blk,
        'fastbreak_pts_rate': fastbreak_pts_rate,
        'second_chance_pts_rate': second_chance_pts_rate
    }

    # Date range
    dates = [g['game_date'] for g in games]
    date_range = (min(dates), max(dates)) if dates else (None, None)

    return {
        'team_id': team_id,
        'raw_features': raw_features,
        'season': season,
        'opponent_cluster_id': opponent_cluster_id,
        'games_used': games_count,
        'date_range': date_range
    }


def refresh_conditional_vectors(season: str = '2025-26', window_mode: str = 'season'):
    """
    Compute and store conditional feature vectors for all teams vs each opponent cluster.

    For each opponent_cluster_id (1-6):
      - Compute feature vectors for all teams using ONLY games vs that cluster type
      - Normalize vectors WITHIN that cluster lens (separate normalization per cluster)
      - Store in team_feature_vectors table with opponent_cluster_id set

    Args:
        season: NBA season (e.g., '2025-26')
        window_mode: 'season', 'last20', or 'last10'

    IMPORTANT: Normalization is done separately per opponent_cluster_id.
    Do NOT normalize conditional vectors against global vectors.
    """
    print(f"\n[Conditional Similarity] Starting refresh for season {season}, window_mode={window_mode}")

    conn = get_connection()
    cursor = conn.cursor()

    # Get all teams
    teams = get_all_teams(season)
    if not teams:
        print(f"[Conditional Similarity] No teams found for season {season}")
        return

    # Get all cluster IDs (should be 1-6)
    cursor.execute("""
        SELECT DISTINCT cluster_id
        FROM team_similarity_clusters
        WHERE season = ?
        ORDER BY cluster_id
    """, (season,))

    cluster_ids = [row[0] for row in cursor.fetchall()]

    if not cluster_ids:
        print(f"[Conditional Similarity] No clusters found for season {season}. Run refresh_similarity_engine() first.")
        return

    print(f"[Conditional Similarity] Processing {len(teams)} teams against {len(cluster_ids)} opponent clusters...")

    # Clear old conditional vectors for this season and window_mode
    cursor.execute("""
        DELETE FROM team_feature_vectors
        WHERE season = ? AND window_mode = ? AND opponent_cluster_id IS NOT NULL
    """, (season, window_mode))
    conn.commit()

    feature_names = list(FEATURE_WEIGHTS.keys())
    total_stored = 0
    total_skipped = 0

    # Process each opponent cluster separately
    for opponent_cluster_id in cluster_ids:
        cursor.execute("""
            SELECT cluster_name FROM team_similarity_clusters
            WHERE cluster_id = ? AND season = ?
        """, (opponent_cluster_id, season))

        cluster_row = cursor.fetchone()
        cluster_name = cluster_row[0] if cluster_row else f"Cluster {opponent_cluster_id}"

        print(f"\n[Conditional Similarity] Processing opponent cluster {opponent_cluster_id}: {cluster_name}")

        # Step 1: Compute raw conditional vectors for all teams
        raw_conditional_features = []

        for team in teams:
            team_id = team['id']

            # Compute conditional vector (returns None if <5 games)
            conditional_data = compute_team_feature_vector_vs_cluster(
                team_id=team_id,
                season=season,
                window_mode=window_mode,
                opponent_cluster_id=opponent_cluster_id
            )

            if conditional_data:
                raw_conditional_features.append(conditional_data)

        if not raw_conditional_features:
            print(f"  No teams with sufficient data vs cluster {opponent_cluster_id} (need 5+ games)")
            continue

        print(f"  {len(raw_conditional_features)}/{len(teams)} teams have sufficient data (5+ games)")

        # Step 2: Normalize vectors WITHIN this cluster lens only
        # Find min/max for each feature across teams in THIS cluster lens
        feature_mins = {name: float('inf') for name in feature_names}
        feature_maxs = {name: float('-inf') for name in feature_names}

        for team_data in raw_conditional_features:
            for name in feature_names:
                val = team_data['raw_features'][name]
                feature_mins[name] = min(feature_mins[name], val)
                feature_maxs[name] = max(feature_maxs[name], val)

        # Step 3: Normalize and store each team's conditional vector
        for team_data in raw_conditional_features:
            team_id = team_data['team_id']
            raw_features = team_data['raw_features']

            # Normalize features
            normalized_features = []
            for name in feature_names:
                raw_val = raw_features[name]
                norm_val = normalize_value(raw_val, feature_mins[name], feature_maxs[name])
                normalized_features.append(norm_val)

            # Convert to JSON for storage
            feature_vector_json = json.dumps(normalized_features)

            # Extract specific features for dedicated columns (using actual feature names from FEATURE_WEIGHTS)
            pace_norm = normalized_features[feature_names.index('pace')]
            three_pt_rate = normalized_features[feature_names.index('three_pt_rate')]
            paint_scoring_rate = normalized_features[feature_names.index('paint_scoring_rate')]
            ast_ratio = normalized_features[feature_names.index('ast_ratio')]
            # Use def_paint_pts_allowed as a proxy for defensive rating
            def_rating_norm = normalized_features[feature_names.index('def_paint_pts_allowed')]

            # Store in database
            cursor.execute("""
                INSERT INTO team_feature_vectors
                (team_id, feature_vector, pace_norm, three_pt_rate, paint_scoring_rate,
                 ast_ratio, def_rating_norm, season, window_mode, opponent_cluster_id, games_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                team_id,
                feature_vector_json,
                pace_norm,
                three_pt_rate,
                paint_scoring_rate,
                ast_ratio,
                def_rating_norm,
                season,
                window_mode,
                opponent_cluster_id,
                team_data['games_used']
            ))

            total_stored += 1

        conn.commit()

        # Log teams that were skipped for this cluster
        stored_team_ids = {t['team_id'] for t in raw_conditional_features}
        skipped_teams = [t for t in teams if t['id'] not in stored_team_ids]

        if skipped_teams:
            total_skipped += len(skipped_teams)
            skipped_names = [t['abbreviation'] for t in skipped_teams[:5]]
            if len(skipped_teams) > 5:
                skipped_names.append(f"... and {len(skipped_teams) - 5} more")
            print(f"  Skipped {len(skipped_teams)} teams with <5 games: {', '.join(skipped_names)}")

    conn.close()

    print(f"\n[Conditional Similarity] Complete!")
    print(f"  Total vectors stored: {total_stored}")
    print(f"  Total skipped (insufficient data): {total_skipped}")
    print(f"  Season: {season}, Window: {window_mode}")


def compute_all_similarity_scores_conditional(season: str = '2025-26', window_mode: str = 'season'):
    """
    Compute pairwise similarity scores for teams within each opponent cluster lens.

    For each opponent_cluster_id:
      - Retrieve all conditional vectors for that cluster
      - Compute pairwise similarity ONLY among teams with vectors for that cluster
      - Store top 5 similar teams in team_similarity_scores with opponent_cluster_id set

    Args:
        season: NBA season (e.g., '2025-26')
        window_mode: 'season', 'last20', or 'last10'

    IMPORTANT: Similarity is computed WITHIN each opponent cluster lens.
    Teams are compared using their conditional vectors vs that specific opponent type.
    """
    print(f"\n[Conditional Similarity] Computing similarity scores for season {season}, window_mode={window_mode}")

    conn = get_connection()
    cursor = conn.cursor()

    # Get all opponent cluster IDs that have data
    cursor.execute("""
        SELECT DISTINCT opponent_cluster_id
        FROM team_feature_vectors
        WHERE season = ? AND window_mode = ? AND opponent_cluster_id IS NOT NULL
        ORDER BY opponent_cluster_id
    """, (season, window_mode))

    cluster_ids = [row[0] for row in cursor.fetchall()]

    if not cluster_ids:
        print(f"[Conditional Similarity] No conditional vectors found. Run refresh_conditional_vectors() first.")
        conn.close()
        return

    print(f"[Conditional Similarity] Processing {len(cluster_ids)} opponent clusters...")

    # Clear old conditional similarity scores for this season and window_mode
    cursor.execute("""
        DELETE FROM team_similarity_scores
        WHERE season = ? AND window_mode = ? AND opponent_cluster_id IS NOT NULL
    """, (season, window_mode))
    conn.commit()

    # Compute max possible distance (for normalization to 0-100 scale)
    max_distance = math.sqrt(sum(FEATURE_WEIGHTS.values()))

    total_scores_stored = 0

    # Process each opponent cluster separately
    for opponent_cluster_id in cluster_ids:
        cursor.execute("""
            SELECT cluster_name FROM team_similarity_clusters
            WHERE cluster_id = ? AND season = ?
        """, (opponent_cluster_id, season))

        cluster_row = cursor.fetchone()
        cluster_name = cluster_row[0] if cluster_row else f"Cluster {opponent_cluster_id}"

        print(f"\n  Processing opponent cluster {opponent_cluster_id}: {cluster_name}")

        # Retrieve all conditional vectors for this cluster
        cursor.execute("""
            SELECT team_id, feature_vector
            FROM team_feature_vectors
            WHERE season = ? AND window_mode = ? AND opponent_cluster_id = ?
        """, (season, window_mode, opponent_cluster_id))

        vectors = []
        for row in cursor.fetchall():
            team_id = row[0]
            feature_vector = json.loads(row[1])  # Parse JSON array
            vectors.append({
                'team_id': team_id,
                'features': feature_vector
            })

        if len(vectors) < 2:
            print(f"    Skipped: Need at least 2 teams with vectors (found {len(vectors)})")
            continue

        print(f"    Computing pairwise similarity for {len(vectors)} teams...")

        # Compute pairwise similarities
        similarity_matrix = {}

        for i, team_a in enumerate(vectors):
            similarities = []

            for j, team_b in enumerate(vectors):
                if i == j:
                    continue  # Skip self-comparison

                distance = compute_weighted_distance(team_a['features'], team_b['features'])
                similarity = distance_to_similarity(distance, max_distance)
                similarities.append((team_b['team_id'], similarity))

            # Sort by similarity (descending) and take top 5
            similarities.sort(key=lambda x: x[1], reverse=True)
            similarity_matrix[team_a['team_id']] = similarities[:5]

        # Store in database
        for team_id, top_similar in similarity_matrix.items():
            for rank, (similar_team_id, score) in enumerate(top_similar, start=1):
                cursor.execute("""
                    INSERT INTO team_similarity_scores
                    (team_id, similar_team_id, similarity_score, rank, season, window_mode, opponent_cluster_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (team_id, similar_team_id, score, rank, season, window_mode, opponent_cluster_id))

                total_scores_stored += 1

        conn.commit()

        print(f"    Stored similarity scores for {len(similarity_matrix)} teams")

    conn.close()

    print(f"\n[Conditional Similarity] Complete!")
    print(f"  Total similarity scores stored: {total_scores_stored}")
    print(f"  Processed {len(cluster_ids)} opponent clusters")
    print(f"  Season: {season}, Window: {window_mode}")


def normalize_all_feature_vectors(all_team_features: List[Dict]) -> List[Dict]:
    """
    Normalize all team feature vectors to 0-1 range using min-max scaling.

    Args:
        all_team_features: List of raw feature dicts from compute_team_feature_vector()

    Returns:
        List of normalized feature vectors with 'features' key
    """
    feature_names = list(FEATURE_WEIGHTS.keys())

    # Find min/max for each feature across all teams
    feature_mins = {name: float('inf') for name in feature_names}
    feature_maxs = {name: float('-inf') for name in feature_names}

    for team_data in all_team_features:
        for name in feature_names:
            val = team_data['raw_features'][name]
            feature_mins[name] = min(feature_mins[name], val)
            feature_maxs[name] = max(feature_maxs[name], val)

    # Normalize each team
    normalized_teams = []
    for team_data in all_team_features:
        normalized_features = []
        for name in feature_names:
            raw_val = team_data['raw_features'][name]
            norm_val = normalize_value(raw_val, feature_mins[name], feature_maxs[name])
            normalized_features.append(norm_val)

        normalized_teams.append({
            'team_id': team_data['team_id'],
            'features': normalized_features,
            'feature_names': feature_names,
            'season': team_data['season']
        })

    return normalized_teams


def compute_weighted_distance(features_a: List[float], features_b: List[float]) -> float:
    """
    Compute weighted Euclidean distance between two feature vectors.

    Args:
        features_a, features_b: Lists of 20 normalized values (0-1)

    Returns:
        Distance value (0 = identical, higher = more different)
    """
    feature_names = list(FEATURE_WEIGHTS.keys())

    distance_sq = 0.0
    for i, name in enumerate(feature_names):
        weight = FEATURE_WEIGHTS[name]
        diff = features_a[i] - features_b[i]
        distance_sq += weight * (diff ** 2)

    return math.sqrt(distance_sq)


def distance_to_similarity(distance: float, max_distance: float) -> float:
    """
    Convert distance to similarity score (0-100%).

    Args:
        distance: Computed distance value
        max_distance: Maximum possible distance (for normalization)

    Returns:
        Similarity score 0-100
    """
    normalized_distance = distance / max_distance if max_distance > 0 else 0
    similarity = 100 * (1 - normalized_distance)
    return max(0.0, min(100.0, similarity))  # Clamp to 0-100


def compute_all_similarity_scores(season: str = '2025-26') -> Dict[int, List[Tuple[int, float]]]:
    """
    Compute pairwise similarity for all teams and store top 5 for each.

    Returns:
        {team_id: [(similar_team_id, similarity_score), ...], ...}
    """
    print(f"[Similarity] Computing feature vectors for all teams...")

    # Get all teams
    teams = get_all_teams()

    # Compute raw features for all teams
    all_raw_features = []
    for team in teams:
        features = compute_team_feature_vector(team['id'], season)
        if features:
            all_raw_features.append(features)

    print(f"[Similarity] Computed features for {len(all_raw_features)} teams")

    # Normalize all vectors
    normalized_teams = normalize_all_feature_vectors(all_raw_features)

    # Compute max possible distance (for normalization)
    max_distance = math.sqrt(sum(FEATURE_WEIGHTS.values()))  # All features maximally different

    # Compute pairwise similarities
    similarity_matrix = {}

    for i, team_a in enumerate(normalized_teams):
        similarities = []

        for j, team_b in enumerate(normalized_teams):
            if i == j:
                continue  # Skip self-comparison

            distance = compute_weighted_distance(team_a['features'], team_b['features'])
            similarity = distance_to_similarity(distance, max_distance)
            similarities.append((team_b['team_id'], similarity))

        # Sort by similarity (descending) and take top 5
        similarities.sort(key=lambda x: x[1], reverse=True)
        similarity_matrix[team_a['team_id']] = similarities[:5]

    # Store in database
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM team_similarity_scores WHERE season = ?", (season,))

    for team_id, top_similar in similarity_matrix.items():
        for rank, (similar_team_id, score) in enumerate(top_similar, start=1):
            cursor.execute("""
                INSERT INTO team_similarity_scores
                (team_id, similar_team_id, similarity_score, rank, season)
                VALUES (?, ?, ?, ?, ?)
            """, (team_id, similar_team_id, score, rank, season))

    conn.commit()

    # Also store feature vectors
    for team_data in normalized_teams:
        feature_json = json.dumps(team_data['features'])
        cursor.execute("""
            INSERT OR REPLACE INTO team_feature_vectors
            (team_id, feature_vector, pace_norm, three_pt_rate, paint_scoring_rate,
             ast_ratio, def_rating_norm, season)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            team_data['team_id'],
            feature_json,
            team_data['features'][0],  # pace_norm
            team_data['features'][2],  # three_pt_rate
            team_data['features'][4],  # paint_scoring_rate
            team_data['features'][6],  # ast_ratio
            team_data['features'][14],  # def_rating_norm
            season
        ))

    conn.commit()
    conn.close()

    print(f"[Similarity] Stored similarity scores for {len(similarity_matrix)} teams")

    return similarity_matrix


def get_team_similarity_ranking(
    team_id: int,
    season: str = '2025-26',
    limit: int = 5,
    opponent_cluster_id: Optional[int] = None,
    window_mode: str = 'season'
) -> List[Dict]:
    """
    Get top N most similar teams for a given team.

    Args:
        team_id: Team ID to get similar teams for
        season: NBA season (e.g., '2025-26')
        limit: Number of similar teams to return
        opponent_cluster_id: If provided, returns conditional similarity vs this opponent cluster
        window_mode: 'season', 'last20', or 'last10' (only used with opponent_cluster_id)

    Returns:
        [{'team_id': int, 'team_name': str, 'similarity_score': float, 'rank': int}, ...]

    IMPORTANT:
    - If opponent_cluster_id is None: Returns global similarity (all season matchups)
    - If opponent_cluster_id is set: Returns conditional similarity (vs that opponent type)
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Build query based on whether we want conditional or global similarity
    if opponent_cluster_id is not None:
        # Conditional similarity: filter by opponent_cluster_id and window_mode
        cursor.execute("""
            SELECT similar_team_id, similarity_score, rank
            FROM team_similarity_scores
            WHERE team_id = ? AND season = ?
              AND opponent_cluster_id = ? AND window_mode = ?
            ORDER BY rank
            LIMIT ?
        """, (team_id, season, opponent_cluster_id, window_mode, limit))
    else:
        # Global similarity: use rows where opponent_cluster_id is NULL
        cursor.execute("""
            SELECT similar_team_id, similarity_score, rank
            FROM team_similarity_scores
            WHERE team_id = ? AND season = ?
              AND opponent_cluster_id IS NULL
            ORDER BY rank
            LIMIT ?
        """, (team_id, season, limit))

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        similar_team = get_team_by_id(row[0])
        results.append({
            'team_id': row[0],
            'team_name': similar_team['full_name'] if similar_team else f"Team {row[0]}",
            'team_abbreviation': similar_team['abbreviation'] if similar_team else "",
            'similarity_score': round(row[1], 1),
            'rank': row[2]
        })

    return results


def get_team_cluster_assignment(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get cluster assignment for a given team (with primary, secondary, and confidence).

    Returns:
        {
            'primary_cluster': {
                'id': int,
                'name': str,
                'description': str,
                'fit_score': float,
                'distance_to_centroid': float,
                'confidence_label': str,
                'confidence_score': float
            },
            'secondary_cluster': {
                'id': int,
                'name': str,
                'description': str,
                'fit_score': float
            },
            'cluster_id': int,  # Backward compatibility
            'cluster_name': str,  # Backward compatibility
            'cluster_description': str,  # Backward compatibility
            'distance_to_centroid': float  # Backward compatibility
        }
        or None if no assignment found
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tca.cluster_id, tca.distance_to_centroid,
               tca.secondary_cluster_id, tca.primary_fit_score, tca.secondary_fit_score,
               tca.confidence_label, tca.confidence_score,
               tsc_primary.cluster_name, tsc_primary.cluster_description,
               tsc_secondary.cluster_name, tsc_secondary.cluster_description
        FROM team_cluster_assignments tca
        JOIN team_similarity_clusters tsc_primary
            ON tca.cluster_id = tsc_primary.cluster_id AND tca.season = tsc_primary.season
        LEFT JOIN team_similarity_clusters tsc_secondary
            ON tca.secondary_cluster_id = tsc_secondary.cluster_id AND tca.season = tsc_secondary.season
        WHERE tca.team_id = ? AND tca.season = ?
    """, (team_id, season))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    result = {
        # New structured format
        'primary_cluster': {
            'id': row[0],
            'name': row[7],
            'description': row[8],
            'fit_score': row[3] if row[3] is not None else 0.0,
            'distance_to_centroid': row[1] if row[1] is not None else 0.0,
            'confidence_label': row[5] if row[5] else 'Medium',
            'confidence_score': row[6] if row[6] is not None else 50.0
        },
        'secondary_cluster': {
            'id': row[2],
            'name': row[9],
            'description': row[10],
            'fit_score': row[4] if row[4] is not None else 0.0
        } if row[2] is not None else None,
        # Backward compatibility fields
        'cluster_id': row[0],
        'cluster_name': row[7],
        'cluster_description': row[8],
        'distance_to_centroid': row[1] if row[1] is not None else 0.0
    }

    return result


def evaluate_cluster_fit(raw_features: Dict, feature_names: List[str]) -> Dict[int, float]:
    """
    Evaluate how well a team's features fit each of the 6 clusters.

    Returns:
        {cluster_id: fit_score, ...}  # Higher score = better fit
    """
    # Extract key metrics from raw features
    pace = raw_features.get('pace', 98.0)
    three_pt_rate = raw_features.get('three_pt_rate', 0.35)
    paint_scoring_rate = raw_features.get('paint_scoring_rate', 0.45)
    rim_attempt_rate = raw_features.get('rim_attempt_rate', 0.30)
    ast_ratio = raw_features.get('ast_ratio', 0.60)
    ast_to_ratio = raw_features.get('ast_to_ratio', 1.7)
    fastbreak_pts_rate = raw_features.get('fastbreak_pts_rate', 0.12)
    oreb_pct = raw_features.get('oreb_pct', 0.23)
    def_rating = raw_features.get('def_paint_pts_allowed', 5.0)  # Proxy for defense
    pace_variance = raw_features.get('pace_variance', 0.5)

    fit_scores = {}

    # Cluster 1: Elite Pace Pushers (pace > 99, fastbreak pts > avg, 3PA > 35%)
    fit_scores[1] = 0.0
    if pace > 99:
        fit_scores[1] += 40.0
    elif pace > 97:
        fit_scores[1] += 20.0

    if fastbreak_pts_rate > 0.14:
        fit_scores[1] += 30.0
    elif fastbreak_pts_rate > 0.12:
        fit_scores[1] += 15.0

    if three_pt_rate > 0.38:
        fit_scores[1] += 30.0
    elif three_pt_rate > 0.35:
        fit_scores[1] += 15.0

    # Cluster 2: Paint Dominators (paint pts % > 50%, rim attempts > 30%, OREB% > avg)
    fit_scores[2] = 0.0
    if paint_scoring_rate > 0.50:
        fit_scores[2] += 40.0
    elif paint_scoring_rate > 0.47:
        fit_scores[2] += 20.0

    if rim_attempt_rate > 0.32:
        fit_scores[2] += 30.0
    elif rim_attempt_rate > 0.28:
        fit_scores[2] += 15.0

    if oreb_pct > 0.25:
        fit_scores[2] += 30.0
    elif oreb_pct > 0.23:
        fit_scores[2] += 15.0

    # Cluster 3: Three-Point Hunters (3PA rate > 40%, perimeter pts > 45%)
    fit_scores[3] = 0.0
    if three_pt_rate > 0.42:
        fit_scores[3] += 50.0
    elif three_pt_rate > 0.38:
        fit_scores[3] += 25.0

    perimeter_rate = 1.0 - paint_scoring_rate
    if perimeter_rate > 0.55:
        fit_scores[3] += 30.0
    elif perimeter_rate > 0.50:
        fit_scores[3] += 15.0

    if pace > 97:
        fit_scores[3] += 20.0

    # Cluster 4: Defensive Grinders (pace < 97, elite defense)
    fit_scores[4] = 0.0
    if pace < 97:
        fit_scores[4] += 40.0
    elif pace < 99:
        fit_scores[4] += 15.0

    if def_rating > 7.0:  # Good defense (proxy inverted from DRTG)
        fit_scores[4] += 40.0
    elif def_rating > 5.0:
        fit_scores[4] += 20.0

    if paint_scoring_rate > 0.48:  # Grind it out in the paint
        fit_scores[4] += 20.0

    # Cluster 5: Balanced High-Assist (AST ratio > 65%, AST/TO > 1.8)
    fit_scores[5] = 0.0
    if ast_ratio > 0.65:
        fit_scores[5] += 40.0
    elif ast_ratio > 0.60:
        fit_scores[5] += 20.0

    if ast_to_ratio > 1.9:
        fit_scores[5] += 30.0
    elif ast_to_ratio > 1.7:
        fit_scores[5] += 15.0

    # Balanced shot distribution (not too extreme in any direction)
    if 0.35 < three_pt_rate < 0.42 and 0.45 < paint_scoring_rate < 0.52:
        fit_scores[5] += 30.0

    # Cluster 6: ISO-Heavy (low assist rate < 60%)
    fit_scores[6] = 0.0
    if ast_ratio < 0.58:
        fit_scores[6] += 50.0
    elif ast_ratio < 0.62:
        fit_scores[6] += 25.0

    if ast_to_ratio < 1.6:
        fit_scores[6] += 30.0
    elif ast_to_ratio < 1.8:
        fit_scores[6] += 15.0

    # ISO teams tend to have variance in pace
    if pace_variance > 0.6:
        fit_scores[6] += 20.0

    return fit_scores


def compute_cluster_centroid(cluster_id: int, season: str = '2025-26') -> Optional[List[float]]:
    """
    Compute the centroid (average feature vector) for a cluster.

    Args:
        cluster_id: The cluster to compute centroid for
        season: NBA season

    Returns:
        List of 20 feature values representing cluster centroid, or None if no teams
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get all teams in this cluster
    cursor.execute("""
        SELECT team_id FROM team_cluster_assignments
        WHERE cluster_id = ? AND season = ?
    """, (cluster_id, season))

    team_ids = [row[0] for row in cursor.fetchall()]

    if not team_ids:
        conn.close()
        return None

    # Get feature vectors for all teams in cluster
    placeholders = ','.join('?' * len(team_ids))
    cursor.execute(f"""
        SELECT feature_vector FROM team_feature_vectors
        WHERE team_id IN ({placeholders}) AND season = ?
    """, (*team_ids, season))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    # Parse feature vectors and compute average
    all_vectors = [json.loads(row[0]) for row in rows]
    num_features = len(all_vectors[0])

    centroid = []
    for i in range(num_features):
        avg_val = sum(vec[i] for vec in all_vectors) / len(all_vectors)
        centroid.append(avg_val)

    return centroid


def assign_team_clusters(season: str = '2025-26') -> Dict[int, int]:
    """
    Assign all teams to their best-fit cluster based on playstyle features.

    Returns:
        {team_id: cluster_id, ...}
    """
    print(f"[Similarity] Assigning teams to clusters...")

    teams = get_all_teams()

    # Compute raw features for all teams
    all_raw_features = []
    for team in teams:
        features = compute_team_feature_vector(team['id'], season)
        if features:
            all_raw_features.append(features)

    # Normalize all vectors (we need normalized for distance calculation)
    normalized_teams = normalize_all_feature_vectors(all_raw_features)

    # Build lookup for raw features by team_id
    raw_features_by_team = {f['team_id']: f['raw_features'] for f in all_raw_features}
    normalized_by_team = {f['team_id']: f['features'] for f in normalized_teams}

    # Assign each team to best-fit cluster
    cluster_assignments = {}

    conn = get_connection()
    cursor = conn.cursor()

    # Clear old assignments
    cursor.execute("DELETE FROM team_cluster_assignments WHERE season = ?", (season,))

    feature_names = list(FEATURE_WEIGHTS.keys())

    for team in all_raw_features:
        team_id = team['team_id']
        raw_features = raw_features_by_team[team_id]

        # Evaluate fit for all 6 clusters
        fit_scores = evaluate_cluster_fit(raw_features, feature_names)

        # Sort clusters by fit score (descending), break ties by cluster_id (ascending)
        sorted_clusters = sorted(fit_scores.items(), key=lambda x: (-x[1], x[0]))

        # Primary = top 1, Secondary = top 2
        primary_cluster_id = sorted_clusters[0][0]
        primary_fit_score = sorted_clusters[0][1]
        secondary_cluster_id = sorted_clusters[1][0] if len(sorted_clusters) > 1 else None
        secondary_fit_score = sorted_clusters[1][1] if len(sorted_clusters) > 1 else None

        cluster_assignments[team_id] = primary_cluster_id

        # Store assignment (distance_to_centroid and confidence will be computed later)
        cursor.execute("""
            INSERT INTO team_cluster_assignments
            (team_id, cluster_id, secondary_cluster_id, primary_fit_score,
             secondary_fit_score, distance_to_centroid, confidence_label, confidence_score, season)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (team_id, primary_cluster_id, secondary_cluster_id, primary_fit_score,
              secondary_fit_score, None, None, None, season))

        team_info = get_team_by_id(team_id)
        team_name = team_info['full_name'] if team_info else f"Team {team_id}"

        print(f"[Similarity]   {team_name} → Primary: Cluster {primary_cluster_id} ({primary_fit_score:.1f}), Secondary: Cluster {secondary_cluster_id} ({secondary_fit_score:.1f})")

    conn.commit()

    # Now compute and update distance to centroid for each team
    print(f"[Similarity] Computing distances to cluster centroids...")

    for cluster_id in range(1, 7):
        centroid = compute_cluster_centroid(cluster_id, season)

        if not centroid:
            continue

        # Get all teams in this cluster
        cursor.execute("""
            SELECT team_id FROM team_cluster_assignments
            WHERE cluster_id = ? AND season = ?
        """, (cluster_id, season))

        team_ids_in_cluster = [row[0] for row in cursor.fetchall()]

        for team_id in team_ids_in_cluster:
            team_features = normalized_by_team.get(team_id)

            if not team_features:
                continue

            # Compute distance from team to cluster centroid
            distance = compute_weighted_distance(team_features, centroid)

            # Update database
            cursor.execute("""
                UPDATE team_cluster_assignments
                SET distance_to_centroid = ?
                WHERE team_id = ? AND season = ?
            """, (distance, team_id, season))

    conn.commit()

    # Compute confidence labels based on distance_to_centroid percentiles
    print(f"[Similarity] Computing confidence labels...")

    # Get all distance_to_centroid values for this season
    cursor.execute("""
        SELECT distance_to_centroid
        FROM team_cluster_assignments
        WHERE season = ? AND distance_to_centroid IS NOT NULL
        ORDER BY distance_to_centroid
    """, (season,))

    distances = [row[0] for row in cursor.fetchall()]

    if len(distances) >= 5:  # Need sufficient data for percentiles
        # Calculate percentiles
        n = len(distances)
        p30_idx = int(n * 0.30)
        p70_idx = int(n * 0.70)
        p30_threshold = distances[p30_idx]
        p70_threshold = distances[p70_idx]

        min_dist = min(distances)
        max_dist = max(distances)
        dist_range = max_dist - min_dist if max_dist > min_dist else 1.0

        # Update each team with confidence label and score
        cursor.execute("""
            SELECT team_id, distance_to_centroid
            FROM team_cluster_assignments
            WHERE season = ? AND distance_to_centroid IS NOT NULL
        """, (season,))

        for row in cursor.fetchall():
            team_id = row[0]
            distance = row[1]

            # Assign confidence label based on percentile bands
            if distance <= p30_threshold:
                confidence_label = "High"
            elif distance <= p70_threshold:
                confidence_label = "Medium"
            else:
                confidence_label = "Low"

            # Compute confidence score (0-100, where 100 = closest to centroid)
            confidence_score = 100.0 * (1.0 - (distance - min_dist) / dist_range)
            confidence_score = max(0.0, min(100.0, confidence_score))

            cursor.execute("""
                UPDATE team_cluster_assignments
                SET confidence_label = ?, confidence_score = ?
                WHERE team_id = ? AND season = ?
            """, (confidence_label, confidence_score, team_id, season))

        conn.commit()
    else:
        # Insufficient data, default all to Medium
        cursor.execute("""
            UPDATE team_cluster_assignments
            SET confidence_label = 'Medium', confidence_score = 50.0
            WHERE season = ? AND confidence_label IS NULL
        """, (season,))
        conn.commit()

    conn.close()

    print(f"[Similarity] Assigned {len(cluster_assignments)} teams to clusters")

    return cluster_assignments


def update_cluster_performance_after_game(
    team_id: int,
    opponent_id: int,
    team_pts: int,
    opponent_pts: int,
    total_pts: int,
    pace: float,
    sportsbook_line: Optional[float] = None,
    team_paint_pts: Optional[int] = None,
    opponent_paint_pts: Optional[int] = None,
    team_three_pt_made: Optional[int] = None,
    opponent_three_pt_made: Optional[int] = None,
    team_turnovers: Optional[int] = None,
    opponent_turnovers: Optional[int] = None,
    season: str = '2025-26'
) -> bool:
    """
    Update performance stats for a team after playing against a specific cluster.
    Uses incremental averaging to maintain running stats.

    Args:
        team_id: Team that played
        opponent_id: Opponent team ID
        team_pts: Points scored by team
        opponent_pts: Points scored by opponent
        total_pts: Total points in game
        pace: Game pace
        sportsbook_line: O/U line (optional, for over/under tracking)
        team_paint_pts: Paint points by team (optional)
        opponent_paint_pts: Paint points by opponent (optional)
        team_three_pt_made: 3PM by team (optional)
        opponent_three_pt_made: 3PM by opponent (optional)
        team_turnovers: Turnovers by team (optional)
        opponent_turnovers: Turnovers by opponent (optional)
        season: NBA season

    Returns:
        True if successful, False otherwise
    """
    # Get opponent's cluster
    opponent_cluster_info = get_team_cluster_assignment(opponent_id, season)

    if not opponent_cluster_info:
        print(f"[Performance] No cluster assignment for opponent {opponent_id}")
        return False

    opponent_cluster_id = opponent_cluster_info['cluster_id']

    conn = get_connection()
    cursor = conn.cursor()

    # Check if record exists
    cursor.execute("""
        SELECT games_played, avg_pts_scored, avg_pts_allowed, avg_total_points,
               avg_pace, avg_paint_pts_diff, avg_three_pt_diff, avg_turnover_diff,
               over_percentage, under_percentage
        FROM team_vs_cluster_performance
        WHERE team_id = ? AND opponent_cluster_id = ? AND season = ?
    """, (team_id, opponent_cluster_id, season))

    existing = cursor.fetchone()

    if existing:
        # Incremental update using running averages
        games_played = existing[0]
        new_games_played = games_played + 1

        # Update averages: new_avg = (old_avg * n + new_value) / (n + 1)
        new_avg_pts_scored = (existing[1] * games_played + team_pts) / new_games_played if existing[1] else team_pts
        new_avg_pts_allowed = (existing[2] * games_played + opponent_pts) / new_games_played if existing[2] else opponent_pts
        new_avg_total_points = (existing[3] * games_played + total_pts) / new_games_played if existing[3] else total_pts
        new_avg_pace = (existing[4] * games_played + pace) / new_games_played if existing[4] else pace

        # Paint points differential
        if team_paint_pts is not None and opponent_paint_pts is not None:
            paint_diff = team_paint_pts - opponent_paint_pts
            new_avg_paint_diff = (existing[5] * games_played + paint_diff) / new_games_played if existing[5] is not None else paint_diff
        else:
            new_avg_paint_diff = existing[5]

        # Three-point differential
        if team_three_pt_made is not None and opponent_three_pt_made is not None:
            three_diff = team_three_pt_made - opponent_three_pt_made
            new_avg_three_diff = (existing[6] * games_played + three_diff) / new_games_played if existing[6] is not None else three_diff
        else:
            new_avg_three_diff = existing[6]

        # Turnover differential
        if team_turnovers is not None and opponent_turnovers is not None:
            tov_diff = opponent_turnovers - team_turnovers  # Positive is good (opponent has more)
            new_avg_tov_diff = (existing[7] * games_played + tov_diff) / new_games_played if existing[7] is not None else tov_diff
        else:
            new_avg_tov_diff = existing[7]

        # Over/under tracking
        if sportsbook_line is not None:
            went_over = 1 if total_pts > sportsbook_line else 0
            overs = (existing[8] * games_played + went_over * 100) / new_games_played if existing[8] is not None else (went_over * 100)
            unders = 100 - overs
        else:
            overs = existing[8]
            unders = existing[9]

        # Update existing record
        cursor.execute("""
            UPDATE team_vs_cluster_performance
            SET games_played = ?,
                avg_pts_scored = ?,
                avg_pts_allowed = ?,
                avg_total_points = ?,
                avg_pace = ?,
                avg_paint_pts_diff = ?,
                avg_three_pt_diff = ?,
                avg_turnover_diff = ?,
                over_percentage = ?,
                under_percentage = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE team_id = ? AND opponent_cluster_id = ? AND season = ?
        """, (
            new_games_played, new_avg_pts_scored, new_avg_pts_allowed, new_avg_total_points,
            new_avg_pace, new_avg_paint_diff, new_avg_three_diff, new_avg_tov_diff,
            overs, unders,
            team_id, opponent_cluster_id, season
        ))

    else:
        # Create new record
        paint_diff = (team_paint_pts - opponent_paint_pts) if team_paint_pts is not None and opponent_paint_pts is not None else None
        three_diff = (team_three_pt_made - opponent_three_pt_made) if team_three_pt_made is not None and opponent_three_pt_made is not None else None
        tov_diff = (opponent_turnovers - team_turnovers) if team_turnovers is not None and opponent_turnovers is not None else None

        if sportsbook_line is not None:
            went_over = 1 if total_pts > sportsbook_line else 0
            overs = went_over * 100
            unders = 100 - overs
        else:
            overs = None
            unders = None

        cursor.execute("""
            INSERT INTO team_vs_cluster_performance
            (team_id, opponent_cluster_id, games_played, avg_pts_scored, avg_pts_allowed,
             avg_total_points, avg_pace, avg_paint_pts_diff, avg_three_pt_diff, avg_turnover_diff,
             over_percentage, under_percentage, season)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            team_id, opponent_cluster_id, 1, team_pts, opponent_pts,
            total_pts, pace, paint_diff, three_diff, tov_diff,
            overs, unders, season
        ))

    conn.commit()
    conn.close()

    return True


def get_team_cluster_performance(team_id: int, opponent_cluster_id: Optional[int] = None, season: str = '2025-26') -> List[Dict]:
    """
    Get performance stats for a team vs a specific cluster or all clusters.

    Args:
        team_id: Team to get stats for
        opponent_cluster_id: Specific cluster (None = all clusters)
        season: NBA season

    Returns:
        List of performance records
    """
    conn = get_connection()
    cursor = conn.cursor()

    if opponent_cluster_id is not None:
        cursor.execute("""
            SELECT tvcp.*, tsc.cluster_name, tsc.cluster_description
            FROM team_vs_cluster_performance tvcp
            LEFT JOIN team_similarity_clusters tsc
                ON tvcp.opponent_cluster_id = tsc.cluster_id AND tvcp.season = tsc.season
            WHERE tvcp.team_id = ? AND tvcp.opponent_cluster_id = ? AND tvcp.season = ?
        """, (team_id, opponent_cluster_id, season))
    else:
        cursor.execute("""
            SELECT tvcp.*, tsc.cluster_name, tsc.cluster_description
            FROM team_vs_cluster_performance tvcp
            LEFT JOIN team_similarity_clusters tsc
                ON tvcp.opponent_cluster_id = tsc.cluster_id AND tvcp.season = tsc.season
            WHERE tvcp.team_id = ? AND tvcp.season = ?
            ORDER BY tvcp.opponent_cluster_id
        """, (team_id, season))

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append({
            'team_id': row[1],
            'opponent_cluster_id': row[2],
            'cluster_name': row[13] if len(row) > 13 else None,
            'cluster_description': row[14] if len(row) > 14 else None,
            'games_played': row[3],
            'avg_pts_scored': round(row[4], 1) if row[4] else None,
            'avg_pts_allowed': round(row[5], 1) if row[5] else None,
            'avg_total_points': round(row[6], 1) if row[6] else None,
            'avg_pace': round(row[7], 1) if row[7] else None,
            'avg_paint_pts_diff': round(row[8], 1) if row[8] is not None else None,
            'avg_three_pt_diff': round(row[9], 1) if row[9] is not None else None,
            'avg_turnover_diff': round(row[10], 1) if row[10] is not None else None,
            'over_percentage': round(row[11], 1) if row[11] is not None else None,
            'under_percentage': round(row[12], 1) if row[12] is not None else None
        })

    return results


def refresh_similarity_engine(season: str = '2025-26'):
    """
    Master function to rebuild all similarity data.
    Runs: compute vectors → compute scores → assign clusters
    """
    print(f"[Similarity] Starting full refresh for season {season}")

    start_time = datetime.now()

    # Step 1: Compute all similarity scores
    similarity_matrix = compute_all_similarity_scores(season)

    # Step 2: Assign clusters
    cluster_assignments = assign_team_clusters(season)

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"[Similarity] Refresh complete in {elapsed:.2f}s")

    return {
        'success': True,
        'teams_processed': len(similarity_matrix),
        'clusters_assigned': len(cluster_assignments),
        'time_seconds': elapsed
    }


def validate_cluster_assignments(season: str = '2025-26'):
    """
    Validation helper to verify primary/secondary cluster assignments and confidence labels.
    Prints summary for all teams with sanity checks.
    """
    print(f"\n{'='*70}")
    print(f"VALIDATING CLUSTER ASSIGNMENTS (Season: {season})")
    print(f"{'='*70}\n")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tca.team_id, tca.cluster_id, tca.secondary_cluster_id,
               tca.primary_fit_score, tca.secondary_fit_score,
               tca.distance_to_centroid, tca.confidence_label, tca.confidence_score,
               tsc_primary.cluster_name, tsc_secondary.cluster_name
        FROM team_cluster_assignments tca
        LEFT JOIN team_similarity_clusters tsc_primary
            ON tca.cluster_id = tsc_primary.cluster_id AND tca.season = tsc_primary.season
        LEFT JOIN team_similarity_clusters tsc_secondary
            ON tca.secondary_cluster_id = tsc_secondary.cluster_id AND tca.season = tsc_secondary.season
        WHERE tca.season = ?
        ORDER BY tca.team_id
    """, (season,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("ERROR: No cluster assignments found!")
        return

    print(f"Found {len(rows)} team assignments\n")
    print(f"{'Team ID':<10} {'Primary':<25} {'Fit':<6} {'Secondary':<25} {'Fit':<6} {'Dist':<8} {'Conf':<8} {'Score':<6}")
    print("-" * 120)

    errors = []
    for row in rows:
        team_id = row[0]
        primary_id = row[1]
        secondary_id = row[2]
        primary_fit = row[3]
        secondary_fit = row[4]
        distance = row[5]
        conf_label = row[6]
        conf_score = row[7]
        primary_name = row[8] if row[8] else f"Cluster {primary_id}"
        secondary_name = row[9] if row[9] else f"Cluster {secondary_id}"

        # Sanity checks
        if secondary_id is not None and secondary_id == primary_id:
            errors.append(f"Team {team_id}: Secondary same as primary!")

        if primary_fit is not None and (primary_fit < 0 or primary_fit > 100):
            errors.append(f"Team {team_id}: Primary fit score out of range: {primary_fit}")

        if secondary_fit is not None and (secondary_fit < 0 or secondary_fit > 100):
            errors.append(f"Team {team_id}: Secondary fit score out of range: {secondary_fit}")

        if conf_label not in ['High', 'Medium', 'Low', None]:
            errors.append(f"Team {team_id}: Invalid confidence label: {conf_label}")

        # Print row
        team_info = get_team_by_id(team_id)
        team_abbr = team_info['abbreviation'] if team_info else f"Team{team_id}"

        primary_str = f"{primary_name[:23]}" if primary_name else "N/A"
        secondary_str = f"{secondary_name[:23]}" if secondary_name else "N/A"
        primary_fit_str = f"{primary_fit:.1f}" if primary_fit is not None else "N/A"
        secondary_fit_str = f"{secondary_fit:.1f}" if secondary_fit is not None else "N/A"
        distance_str = f"{distance:.4f}" if distance is not None else "N/A"
        conf_label_str = conf_label if conf_label else "N/A"
        conf_score_str = f"{conf_score:.1f}" if conf_score is not None else "N/A"

        print(f"{team_abbr:<10} {primary_str:<25} {primary_fit_str:<6} {secondary_str:<25} {secondary_fit_str:<6} {distance_str:<8} {conf_label_str:<8} {conf_score_str:<6}")

    print("\n" + "="*70)

    if errors:
        print("VALIDATION ERRORS:")
        for error in errors:
            print(f"  ✗ {error}")
    else:
        print("✓ All sanity checks passed!")

    # Confidence distribution
    high_count = sum(1 for row in rows if row[6] == 'High')
    med_count = sum(1 for row in rows if row[6] == 'Medium')
    low_count = sum(1 for row in rows if row[6] == 'Low')

    print(f"\nConfidence Distribution:")
    print(f"  High: {high_count} teams (~{high_count/len(rows)*100:.0f}%)")
    print(f"  Medium: {med_count} teams (~{med_count/len(rows)*100:.0f}%)")
    print(f"  Low: {low_count} teams (~{low_count/len(rows)*100:.0f}%)")

    print(f"\n{'='*70}\n")


def validate_feature_vectors(season: str = '2025-26'):
    """
    Validation helper to verify all 7 replaced features are computed correctly.
    Prints min/max ranges and sample outputs for verification.
    """
    print(f"\n{'='*70}")
    print(f"VALIDATING FEATURE VECTOR COMPUTATIONS (Season: {season})")
    print(f"{'='*70}\n")

    teams = get_all_teams()
    all_features = []

    print(f"Computing feature vectors for {len(teams)} teams...")
    for team in teams:
        features = compute_team_feature_vector(team['id'], season)
        if features:
            all_features.append(features)

    if len(all_features) == 0:
        print("ERROR: No feature vectors computed!")
        return

    print(f"✓ Successfully computed {len(all_features)} feature vectors\n")

    # Focus on the 7 replaced features
    replaced_features = [
        'pace_variance',
        'oreb_pct',
        'dreb_pct',
        'def_three_pct_allowed',
        'rim_attempt_rate',
        'midrange_rate',
        'fouls_committed_rate'
    ]

    print("MIN/MAX RANGES FOR REPLACED FEATURES:")
    print("-" * 70)

    for feature_name in replaced_features:
        values = [f['raw_features'][feature_name] for f in all_features]
        min_val = min(values)
        max_val = max(values)
        mean_val = sum(values) / len(values)

        # Check for NaN or invalid values
        has_nan = any(v != v for v in values)  # NaN != NaN
        has_negative = any(v < 0 for v in values)

        status = "✓"
        warnings = []
        if has_nan:
            status = "✗"
            warnings.append("HAS NaN VALUES")
        if has_negative and feature_name != 'def_three_pct_allowed':
            warnings.append("has negative values")

        print(f"{status} {feature_name:25s} | min: {min_val:6.3f} | max: {max_val:6.3f} | mean: {mean_val:6.3f}")
        if warnings:
            print(f"  WARNING: {', '.join(warnings)}")

    # Sample output for 2 teams
    print(f"\n{'='*70}")
    print("SAMPLE FEATURE VECTORS (2 teams):")
    print("-" * 70)

    # Boston Celtics and Oklahoma City Thunder
    sample_teams = [
        (1610612738, "Boston Celtics"),
        (1610612760, "Oklahoma City Thunder")
    ]

    for team_id, team_name in sample_teams:
        features = compute_team_feature_vector(team_id, season)
        if features:
            print(f"\n{team_name} (ID: {team_id}):")
            raw = features['raw_features']
            for feature_name in replaced_features:
                print(f"  {feature_name:25s}: {raw[feature_name]:.4f}")
        else:
            print(f"\n{team_name} (ID: {team_id}): NO DATA")

    print(f"\n{'='*70}")
    print("VALIDATION COMPLETE")
    print(f"{'='*70}\n")


def validate_conditional_similarity(season: str = '2025-26', window_mode: str = 'season'):
    """
    Validation helper to verify conditional similarity system is working correctly.
    Checks vectors, scores, and retrieval for all opponent clusters.
    """
    print(f"\n{'='*80}")
    print(f"VALIDATING CONDITIONAL SIMILARITY SYSTEM")
    print(f"Season: {season}, Window: {window_mode}")
    print(f"{'='*80}\n")

    conn = get_connection()
    cursor = conn.cursor()

    # Check 1: Validate conditional vectors
    print("📊 Check 1: Conditional Feature Vectors")
    print("-" * 80)

    cursor.execute("""
        SELECT
            opponent_cluster_id,
            COUNT(*) as vector_count,
            AVG(games_used) as avg_games,
            MIN(games_used) as min_games,
            MAX(games_used) as max_games
        FROM team_feature_vectors
        WHERE season = ? AND window_mode = ? AND opponent_cluster_id IS NOT NULL
        GROUP BY opponent_cluster_id
        ORDER BY opponent_cluster_id
    """, (season, window_mode))

    vector_rows = cursor.fetchall()

    if not vector_rows:
        print("❌ FAIL: No conditional vectors found!")
        conn.close()
        return False

    print(f"{'Cluster':<10} {'Teams':<10} {'Avg Games':<15} {'Games Range':<15}")
    print("-" * 80)

    for row in vector_rows:
        cluster_id = row[0]
        vector_count = row[1]
        avg_games = row[2]
        min_games = row[3]
        max_games = row[4]

        # Get cluster name
        cursor.execute("""
            SELECT cluster_name FROM team_similarity_clusters
            WHERE cluster_id = ? AND season = ?
        """, (cluster_id, season))
        cluster_row = cursor.fetchone()
        cluster_name = cluster_row[0] if cluster_row else f"Cluster {cluster_id}"

        print(f"{cluster_id:<10} {vector_count:<10} {avg_games:<15.1f} {min_games}-{max_games}")

        # Sanity check: all teams should have at least 5 games
        if min_games < 5:
            print(f"  ⚠️  WARNING: Some teams have < 5 games (min: {min_games})")

    # Check 2: Validate conditional similarity scores
    print(f"\n📊 Check 2: Conditional Similarity Scores")
    print("-" * 80)

    cursor.execute("""
        SELECT
            opponent_cluster_id,
            COUNT(*) as score_count,
            COUNT(DISTINCT team_id) as team_count,
            AVG(similarity_score) as avg_similarity,
            MIN(similarity_score) as min_similarity,
            MAX(similarity_score) as max_similarity
        FROM team_similarity_scores
        WHERE season = ? AND window_mode = ? AND opponent_cluster_id IS NOT NULL
        GROUP BY opponent_cluster_id
        ORDER BY opponent_cluster_id
    """, (season, window_mode))

    score_rows = cursor.fetchall()

    if not score_rows:
        print("❌ FAIL: No conditional similarity scores found!")
        conn.close()
        return False

    print(f"{'Cluster':<10} {'Teams':<10} {'Scores':<10} {'Avg Sim':<15} {'Range':<15}")
    print("-" * 80)

    for row in score_rows:
        cluster_id = row[0]
        score_count = row[1]
        team_count = row[2]
        avg_sim = row[3]
        min_sim = row[4]
        max_sim = row[5]

        print(f"{cluster_id:<10} {team_count:<10} {score_count:<10} {avg_sim:<15.1f} {min_sim:.1f}-{max_sim:.1f}")

        # Sanity check: similarity should be 0-100
        if min_sim < 0 or max_sim > 100:
            print(f"  ⚠️  WARNING: Similarity scores out of range [0, 100]")

    # Check 3: Test retrieval for sample teams
    print(f"\n📊 Check 3: Sample Retrieval Tests")
    print("-" * 80)

    # Get a few sample teams with conditional vectors
    cursor.execute("""
        SELECT DISTINCT team_id
        FROM team_feature_vectors
        WHERE season = ? AND window_mode = ? AND opponent_cluster_id = 3
        LIMIT 3
    """, (season, window_mode))

    sample_team_ids = [row[0] for row in cursor.fetchall()]

    for team_id in sample_team_ids:
        team_info = get_team_by_id(team_id)
        team_abbr = team_info['abbreviation'] if team_info else f"Team {team_id}"

        # Get conditional similarity vs cluster 3
        similar_teams = get_team_similarity_ranking(
            team_id=team_id,
            season=season,
            limit=3,
            opponent_cluster_id=3,
            window_mode=window_mode
        )

        if similar_teams:
            similar_abbrs = [f"{t['team_abbreviation']} ({t['similarity_score']}%)" for t in similar_teams]
            print(f"✓ {team_abbr} vs 3PT Hunters → Similar to: {', '.join(similar_abbrs)}")
        else:
            print(f"❌ {team_abbr} → No similar teams found")

    # Check 4: Verify JSON structure
    print(f"\n📊 Check 4: Feature Vector JSON Structure")
    print("-" * 80)

    cursor.execute("""
        SELECT feature_vector
        FROM team_feature_vectors
        WHERE season = ? AND window_mode = ? AND opponent_cluster_id IS NOT NULL
        LIMIT 1
    """, (season, window_mode))

    row = cursor.fetchone()
    if row:
        try:
            feature_vector = json.loads(row[0])
            if len(feature_vector) == 20:
                print(f"✓ Feature vectors have correct length (20 features)")
                all_in_range = all(0 <= val <= 1 for val in feature_vector)
                if all_in_range:
                    print(f"✓ All feature values normalized to [0, 1] range")
                else:
                    print(f"❌ FAIL: Some feature values outside [0, 1] range")
            else:
                print(f"❌ FAIL: Feature vectors have wrong length ({len(feature_vector)} instead of 20)")
        except json.JSONDecodeError:
            print(f"❌ FAIL: Feature vector JSON is malformed")
    else:
        print(f"❌ FAIL: No feature vectors found to validate")

    conn.close()

    print(f"\n{'='*80}")
    print(f"✅ VALIDATION COMPLETE")
    print(f"{'='*80}\n")

    return True


if __name__ == '__main__':
    # Test the system
    from api.utils.db_schema_similarity import initialize_schema, seed_cluster_definitions

    initialize_schema()
    seed_cluster_definitions()

    # Run validation first
    validate_feature_vectors('2025-26')

    result = refresh_similarity_engine('2025-26')
    print(f"\nRefresh result: {result}")

    # Validate cluster assignments
    validate_cluster_assignments('2025-26')

    # Test similarity lookup for a team
    magic_similar = get_team_similarity_ranking(1610612753, '2025-26')  # Orlando Magic
    print(f"\nOrlando Magic similar teams:")
    for team in magic_similar:
        print(f"  {team['rank']}. {team['team_name']}: {team['similarity_score']}%")
