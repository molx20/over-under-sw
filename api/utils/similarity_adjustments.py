"""
Similarity-Based Adjustments for Prediction Engine

This module provides cluster and similarity-based adjustments to predictions.
It uses the Team Similarity Engine to make more informed predictions based on:
- Team playstyle clusters (Elite Pace Pushers, Paint Dominators, etc.)
- Historical performance vs similar opponents
- Cluster-specific pace and scoring patterns
"""

from typing import Dict, Optional, Tuple
import sqlite3
import os

# Import similarity engine functions
from api.utils.team_similarity import (
    get_team_similarity_ranking,
    get_team_cluster_assignment
)
from api.utils.db_schema_similarity import get_connection as get_similarity_conn


def get_similarity_data(home_team_id: int, away_team_id: int, season: str = '2025-26') -> Dict:
    """
    Fetch similarity data for both teams in a matchup

    Args:
        home_team_id: Home team NBA ID
        away_team_id: Away team NBA ID
        season: Season string (default '2025-26')

    Returns:
        Dictionary containing:
        - home_cluster: Home team's cluster assignment
        - away_cluster: Away team's cluster assignment
        - home_similar_teams: Top 5 similar teams to home team
        - away_similar_teams: Top 5 similar teams to away team
        - matchup_cluster_type: String describing the cluster matchup
    """
    try:
        # Get cluster assignments
        home_cluster = get_team_cluster_assignment(home_team_id, season)
        away_cluster = get_team_cluster_assignment(away_team_id, season)

        # Get similar teams (top 3 for brevity)
        home_similar_teams = get_team_similarity_ranking(home_team_id, season, limit=3)
        away_similar_teams = get_team_similarity_ranking(away_team_id, season, limit=3)

        # Determine matchup type
        matchup_cluster_type = _get_matchup_cluster_type(home_cluster, away_cluster)

        return {
            'home_cluster': home_cluster,
            'away_cluster': away_cluster,
            'home_similar_teams': home_similar_teams,
            'away_similar_teams': away_similar_teams,
            'matchup_cluster_type': matchup_cluster_type,
            'has_data': True
        }
    except Exception as e:
        print(f"[similarity_adjustments] Warning: Could not fetch similarity data: {e}")
        return {
            'home_cluster': None,
            'away_cluster': None,
            'home_similar_teams': [],
            'away_similar_teams': [],
            'matchup_cluster_type': 'Unknown',
            'has_data': False
        }


def _get_matchup_cluster_type(home_cluster: Optional[Dict], away_cluster: Optional[Dict]) -> str:
    """
    Classify the matchup based on cluster assignments

    Returns strings like:
    - "Pace Pushers vs Defensive Grinders"
    - "Paint Dominators Clash"
    - "Perimeter Shootout"
    """
    if not home_cluster or not away_cluster:
        return "Unknown"

    home_name = home_cluster.get('cluster_name', 'Unknown')
    away_name = away_cluster.get('cluster_name', 'Unknown')

    # Same cluster matchups
    if home_cluster.get('cluster_id') == away_cluster.get('cluster_id'):
        if 'Pace' in home_name:
            return "High-Pace Shootout"
        elif 'Paint' in home_name:
            return "Paint Battle"
        elif 'Three-Point' in home_name:
            return "Perimeter Shootout"
        elif 'Defensive' in home_name:
            return "Defensive Grind"
        elif 'Balanced' in home_name:
            return "Balanced Matchup"
        else:
            return f"{home_name} Mirror Match"

    # Different clusters - show contrast
    return f"{home_name} vs {away_name}"


def calculate_cluster_pace_adjustment(
    home_cluster: Optional[Dict],
    away_cluster: Optional[Dict],
    baseline_pace: float
) -> Tuple[float, str]:
    """
    Adjust predicted pace based on cluster matchup

    Args:
        home_cluster: Home team cluster info
        away_cluster: Away team cluster info
        baseline_pace: Current predicted pace

    Returns:
        (adjustment, explanation) tuple
    """
    if not home_cluster or not away_cluster:
        return (0.0, "No cluster data available")

    home_cluster_id = home_cluster.get('cluster_id')
    away_cluster_id = away_cluster.get('cluster_id')

    adjustment = 0.0
    reasons = []

    # Cluster 1: Elite Pace Pushers (99+ pace)
    if home_cluster_id == 1 or away_cluster_id == 1:
        adjustment += 1.5
        reasons.append("Elite pace pusher influence")

    # Cluster 4: Defensive Grinders (slow pace <97)
    if home_cluster_id == 4 or away_cluster_id == 4:
        adjustment -= 1.5
        reasons.append("Defensive grinder slowdown")

    # Both teams same cluster - amplify tendency
    if home_cluster_id == away_cluster_id:
        if home_cluster_id == 1:  # Both pace pushers
            adjustment += 1.0
            reasons.append("Dual pace pushers")
        elif home_cluster_id == 4:  # Both grinders
            adjustment -= 1.0
            reasons.append("Dual defensive grinders")

    # Pace pushers vs grinders - moderate effect (conflicting styles)
    if (home_cluster_id == 1 and away_cluster_id == 4) or (home_cluster_id == 4 and away_cluster_id == 1):
        adjustment *= 0.5  # Reduce the adjustment
        reasons.append("Conflicting pace styles (moderated)")

    explanation = "; ".join(reasons) if reasons else "No pace adjustment"

    return (adjustment, explanation)


def calculate_cluster_scoring_adjustment(
    home_cluster: Optional[Dict],
    away_cluster: Optional[Dict],
    home_baseline: float,
    away_baseline: float
) -> Tuple[float, float, str]:
    """
    Adjust team scoring projections based on cluster matchup

    Args:
        home_cluster: Home team cluster info
        away_cluster: Away team cluster info
        home_baseline: Home team baseline projection
        away_baseline: Away team baseline projection

    Returns:
        (home_adjustment, away_adjustment, explanation) tuple
    """
    if not home_cluster or not away_cluster:
        return (0.0, 0.0, "No cluster data available")

    home_cluster_id = home_cluster.get('cluster_id')
    away_cluster_id = away_cluster.get('cluster_id')

    home_adj = 0.0
    away_adj = 0.0
    reasons = []

    # Cluster 2: Paint Dominators vs Cluster 3: Three-Point Hunters
    # Paint teams may struggle vs perimeter-heavy defenses
    if home_cluster_id == 2 and away_cluster_id == 3:
        home_adj -= 0.5
        reasons.append("Paint offense vs perimeter defense mismatch")

    if away_cluster_id == 2 and home_cluster_id == 3:
        away_adj -= 0.5
        reasons.append("Paint offense vs perimeter defense mismatch")

    # Cluster 3: Three-Point Hunters vs Cluster 4: Defensive Grinders
    # Grinders typically have strong perimeter defense
    if home_cluster_id == 3 and away_cluster_id == 4:
        home_adj -= 1.0
        reasons.append("Perimeter offense vs defensive grinder")

    if away_cluster_id == 3 and home_cluster_id == 4:
        away_adj -= 1.0
        reasons.append("Perimeter offense vs defensive grinder")

    # Cluster 1: Pace Pushers - score more in transition
    # But may struggle vs Cluster 4: Grinders who slow the game
    if home_cluster_id == 1 and away_cluster_id != 4:
        home_adj += 0.75
        reasons.append("Pace pusher advantage")

    if away_cluster_id == 1 and home_cluster_id != 4:
        away_adj += 0.75
        reasons.append("Pace pusher advantage")

    # Cluster 6: ISO-Heavy teams may struggle vs Cluster 5: Balanced High-Assist
    # High-assist teams typically have better team defense
    if home_cluster_id == 6 and away_cluster_id == 5:
        home_adj -= 0.5
        reasons.append("ISO-heavy vs team-oriented defense")

    if away_cluster_id == 6 and home_cluster_id == 5:
        away_adj -= 0.5
        reasons.append("ISO-heavy vs team-oriented defense")

    explanation = "; ".join(reasons) if reasons else "No scoring adjustment"

    return (home_adj, away_adj, explanation)


def calculate_paint_vs_perimeter_adjustment(
    home_cluster: Optional[Dict],
    away_cluster: Optional[Dict],
    home_stats: Dict,
    away_stats: Dict
) -> Tuple[float, float, str]:
    """
    Adjust scoring based on paint vs perimeter tendencies

    This looks at teams' offensive identities (paint-heavy vs perimeter-heavy)
    and adjusts based on opponent's defensive cluster profile

    Returns:
        (home_adjustment, away_adjustment, explanation) tuple
    """
    if not home_cluster or not away_cluster:
        return (0.0, 0.0, "No cluster data available")

    home_cluster_id = home_cluster.get('cluster_id')
    away_cluster_id = away_cluster.get('cluster_id')

    home_adj = 0.0
    away_adj = 0.0
    reasons = []

    # Get 3PT attempt rates if available
    home_overall = home_stats.get('overall', {})
    away_overall = away_stats.get('overall', {})

    home_3pa_rate = home_overall.get('FG3A', 0) / max(home_overall.get('FGA', 1), 1) if home_overall else 0.35
    away_3pa_rate = away_overall.get('FG3A', 0) / max(away_overall.get('FGA', 1), 1) if away_overall else 0.35

    # Paint Dominators (Cluster 2) vs teams with weak paint defense
    # Look for mismatches
    if home_cluster_id == 2 and away_cluster_id != 4:  # Paint vs non-grinder
        home_adj += 0.75
        reasons.append("Paint dominator advantage")

    if away_cluster_id == 2 and home_cluster_id != 4:
        away_adj += 0.75
        reasons.append("Paint dominator advantage")

    # Three-Point Hunters (Cluster 3) vs teams that allow high 3PT%
    if home_cluster_id == 3 and away_cluster_id not in [3, 4]:  # Perimeter vs non-perimeter/non-grinder
        home_adj += 0.5
        reasons.append("Perimeter advantage")

    if away_cluster_id == 3 and home_cluster_id not in [3, 4]:
        away_adj += 0.5
        reasons.append("Perimeter advantage")

    explanation = "; ".join(reasons) if reasons else "No paint/perimeter adjustment"

    return (home_adj, away_adj, explanation)


def get_similarity_insights_for_breakdown(
    similarity_data: Dict,
    pace_adj: Tuple[float, str],
    scoring_adj: Tuple[float, float, str],
    paint_perimeter_adj: Tuple[float, float, str]
) -> Dict:
    """
    Package similarity data for inclusion in prediction breakdown

    Args:
        similarity_data: Output from get_similarity_data()
        pace_adj: Output from calculate_cluster_pace_adjustment()
        scoring_adj: Output from calculate_cluster_scoring_adjustment()
        paint_perimeter_adj: Output from calculate_paint_vs_perimeter_adjustment()

    Returns:
        Dictionary formatted for prediction result['breakdown']['similarity']
    """
    if not similarity_data.get('has_data'):
        return None

    home_cluster = similarity_data.get('home_cluster')
    away_cluster = similarity_data.get('away_cluster')

    return {
        'matchup_type': similarity_data.get('matchup_cluster_type'),
        'home_cluster': {
            'id': home_cluster.get('cluster_id') if home_cluster else None,
            'name': home_cluster.get('cluster_name') if home_cluster else None,
            'description': home_cluster.get('cluster_description') if home_cluster else None,
            'distance_to_centroid': round(home_cluster.get('distance_to_centroid'), 3) if home_cluster and home_cluster.get('distance_to_centroid') else None
        },
        'away_cluster': {
            'id': away_cluster.get('cluster_id') if away_cluster else None,
            'name': away_cluster.get('cluster_name') if away_cluster else None,
            'description': away_cluster.get('cluster_description') if away_cluster else None,
            'distance_to_centroid': round(away_cluster.get('distance_to_centroid'), 3) if away_cluster and away_cluster.get('distance_to_centroid') else None
        },
        'home_similar_teams': similarity_data.get('home_similar_teams', []),
        'away_similar_teams': similarity_data.get('away_similar_teams', []),
        'adjustments': {
            'pace_adjustment': round(pace_adj[0], 2),
            'pace_explanation': pace_adj[1],
            'home_scoring_adjustment': round(scoring_adj[0], 2),
            'away_scoring_adjustment': round(scoring_adj[1], 2),
            'scoring_explanation': scoring_adj[2],
            'home_paint_perimeter_adjustment': round(paint_perimeter_adj[0], 2),
            'away_paint_perimeter_adjustment': round(paint_perimeter_adj[1], 2),
            'paint_perimeter_explanation': paint_perimeter_adj[2]
        }
    }


if __name__ == '__main__':
    # Test with a sample matchup
    print("Testing similarity adjustments...")
    print("="*60)

    # Test Orlando Magic (1610612753) vs Minnesota Timberwolves (1610612750)
    home_id = 1610612753  # Orlando Magic
    away_id = 1610612750  # Minnesota Timberwolves

    # Get similarity data
    sim_data = get_similarity_data(home_id, away_id)

    print(f"\nMatchup: Team {home_id} vs Team {away_id}")
    print(f"Matchup Type: {sim_data['matchup_cluster_type']}")
    print(f"\nHome Cluster: {sim_data['home_cluster']}")
    print(f"Away Cluster: {sim_data['away_cluster']}")

    # Test pace adjustment
    baseline_pace = 100.0
    pace_adj, pace_reason = calculate_cluster_pace_adjustment(
        sim_data['home_cluster'],
        sim_data['away_cluster'],
        baseline_pace
    )
    print(f"\nPace Adjustment: {pace_adj:+.1f}")
    print(f"Reason: {pace_reason}")

    # Test scoring adjustment
    home_baseline = 115.0
    away_baseline = 112.0
    home_score_adj, away_score_adj, score_reason = calculate_cluster_scoring_adjustment(
        sim_data['home_cluster'],
        sim_data['away_cluster'],
        home_baseline,
        away_baseline
    )
    print(f"\nScoring Adjustments:")
    print(f"  Home: {home_score_adj:+.1f}")
    print(f"  Away: {away_score_adj:+.1f}")
    print(f"  Reason: {score_reason}")

    # Test paint/perimeter adjustment
    home_stats = {'overall': {'FG3A': 35, 'FGA': 90}}
    away_stats = {'overall': {'FG3A': 40, 'FGA': 88}}
    home_pp_adj, away_pp_adj, pp_reason = calculate_paint_vs_perimeter_adjustment(
        sim_data['home_cluster'],
        sim_data['away_cluster'],
        home_stats,
        away_stats
    )
    print(f"\nPaint/Perimeter Adjustments:")
    print(f"  Home: {home_pp_adj:+.1f}")
    print(f"  Away: {away_pp_adj:+.1f}")
    print(f"  Reason: {pp_reason}")

    # Test insights packaging
    insights = get_similarity_insights_for_breakdown(
        sim_data,
        (pace_adj, pace_reason),
        (home_score_adj, away_score_adj, score_reason),
        (home_pp_adj, away_pp_adj, pp_reason)
    )
    print(f"\nFull Insights Package:")
    import json
    print(json.dumps(insights, indent=2))
