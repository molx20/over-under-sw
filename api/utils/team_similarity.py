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
        return None

    # Fetch box score aggregates from game logs
    cursor.execute("""
        SELECT
            AVG(points_in_paint) as avg_paint_pts,
            AVG(fast_break_points) as avg_fastbreak_pts,
            AVG(second_chance_points) as avg_second_chance_pts
        FROM team_game_logs
        WHERE team_id = ? AND season = ?
        GROUP BY team_id
    """, (team_id, season))

    box_stats = cursor.fetchone()
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

    # Compute raw features
    three_pt_rate = fg3a / fga if fga > 0 else 0.35
    paint_scoring_rate = paint_pts / pts_pg if pts_pg > 0 else 0.45
    ast_ratio = ast / fgm if fgm > 0 else 0.6
    ast_to_ratio = ast / tov if tov > 0 else 1.7
    turnover_rate = tov / pace if pace > 0 else 0.13
    fta_rate = fta / fga if fga > 0 else 0.23
    fouls_drawn_rate = fta / pace if pace > 0 else 0.20
    # Note: we don't have personal fouls in the current query, using default
    fouls_committed_rate = 0.20
    fastbreak_pts_rate = fastbreak_pts / pts_pg if pts_pg > 0 else 0.12
    second_chance_pts_rate = second_chance_pts / pts_pg if pts_pg > 0 else 0.12

    # Rebounding percentages (estimate - we don't have OREB/DREB split, using defaults)
    oreb_pct = 0.23  # Default, would need more granular data
    dreb_pct = 0.77  # Default, would need more granular data

    # Build feature vector (will normalize later across all teams)
    raw_features = {
        'pace': pace,
        'pace_variance': 0.5,  # Placeholder, would need game-by-game data
        'three_pt_rate': three_pt_rate,
        'midrange_rate': 0.15,  # Placeholder, need shot zone data
        'paint_scoring_rate': paint_scoring_rate,
        'rim_attempt_rate': 0.30,  # Placeholder, need shot zone data
        'ast_ratio': ast_ratio,
        'ast_to_ratio': ast_to_ratio,
        'turnover_rate': turnover_rate,
        'fta_rate': fta_rate,
        'fouls_drawn_rate': fouls_drawn_rate,
        'fouls_committed_rate': fouls_committed_rate,
        'oreb_pct': oreb_pct,
        'dreb_pct': dreb_pct,
        'def_paint_pts_allowed': 115 - drtg,  # Proxy, inverted
        'def_three_pct_allowed': 0.36,  # Placeholder
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


def get_team_similarity_ranking(team_id: int, season: str = '2025-26', limit: int = 5) -> List[Dict]:
    """
    Get top N most similar teams for a given team.

    Returns:
        [{'team_id': int, 'team_name': str, 'similarity_score': float, 'rank': int}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT similar_team_id, similarity_score, rank
        FROM team_similarity_scores
        WHERE team_id = ? AND season = ?
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
    Get cluster assignment for a given team.

    Returns:
        {
            'cluster_id': int,
            'cluster_name': str,
            'cluster_description': str,
            'distance_to_centroid': float
        }
        or None if no assignment found
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tca.cluster_id, tca.distance_to_centroid,
               tsc.cluster_name, tsc.cluster_description
        FROM team_cluster_assignments tca
        JOIN team_similarity_clusters tsc
            ON tca.cluster_id = tsc.cluster_id AND tca.season = tsc.season
        WHERE tca.team_id = ? AND tca.season = ?
    """, (team_id, season))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'cluster_id': row[0],
        'distance_to_centroid': row[1],
        'cluster_name': row[2],
        'cluster_description': row[3]
    }


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

        # Assign to cluster with highest fit score
        best_cluster = max(fit_scores.items(), key=lambda x: x[1])
        cluster_id = best_cluster[0]
        fit_score = best_cluster[1]

        cluster_assignments[team_id] = cluster_id

        # Store assignment (distance_to_centroid will be computed later)
        cursor.execute("""
            INSERT INTO team_cluster_assignments
            (team_id, cluster_id, distance_to_centroid, season)
            VALUES (?, ?, ?, ?)
        """, (team_id, cluster_id, None, season))

        team_info = get_team_by_id(team_id)
        team_name = team_info['full_name'] if team_info else f"Team {team_id}"

        print(f"[Similarity]   {team_name} → Cluster {cluster_id} (fit: {fit_score:.1f})")

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


if __name__ == '__main__':
    # Test the system
    from api.utils.db_schema_similarity import initialize_schema, seed_cluster_definitions

    initialize_schema()
    seed_cluster_definitions()

    result = refresh_similarity_engine('2025-26')
    print(f"\nRefresh result: {result}")

    # Test similarity lookup for a team
    magic_similar = get_team_similarity_ranking(1610612753, '2025-26')  # Orlando Magic
    print(f"\nOrlando Magic similar teams:")
    for team in magic_similar:
        print(f"  {team['rank']}. {team['team_name']}: {team['similarity_score']}%")
