"""
Feature Vector Builder

Combines recent form + matchup profile features into a single vector for prediction.
This vector is used to compute correction to base prediction via w·x dot product.

Feature Vector (9 features total):
1. bias (always 1.0) - intercept term
2. home_recent_off_delta - home team's recent OFF RTG vs season average
3. home_recent_def_delta - home team's recent DEF RTG vs season average
4. away_recent_off_delta - away team's recent OFF RTG vs season average
5. away_recent_def_delta - away team's recent DEF RTG vs season average
6. home_vs_off_bucket_total - home's avg total vs opponent's offensive bucket
7. away_vs_off_bucket_total - away's avg total vs opponent's offensive bucket
8. home_vs_def_bucket_total - home's avg total vs opponent's defensive bucket
9. away_vs_def_bucket_total - away's avg total vs opponent's defensive bucket
"""

from typing import Dict, List
from datetime import datetime

try:
    from api.utils.recent_form import compute_recent_form_features
    from api.utils.matchup_profile import (
        classify_team_bucket,
        get_matchup_profile
    )
    from api.utils import team_rankings
    from api.utils.nba_data import get_all_teams
except ImportError:
    from recent_form import compute_recent_form_features
    from matchup_profile import (
        classify_team_bucket,
        get_matchup_profile
    )
    import team_rankings
    from nba_data import get_all_teams


# Feature names in order (for reference)
FEATURE_NAMES = [
    'bias',
    'home_recent_off_delta',
    'home_recent_def_delta',
    'away_recent_off_delta',
    'away_recent_def_delta',
    'home_vs_off_bucket_total',
    'away_vs_off_bucket_total',
    'home_vs_def_bucket_total',
    'away_vs_def_bucket_total'
]


def build_feature_vector(
    home_team: str,
    away_team: str,
    game_id: str,
    as_of_date: str,
    home_team_id: int = None,
    away_team_id: int = None,
    n_recent_games: int = 10,
    season: str = '2025-26'
) -> Dict:
    """
    Build complete feature vector for a matchup

    Args:
        home_team: Home team abbreviation (e.g., 'BOS')
        away_team: Away team abbreviation (e.g., 'LAL')
        game_id: NBA game ID
        as_of_date: Date to compute features as of (YYYY-MM-DD)
        home_team_id: NBA team ID for home (optional, will lookup if needed)
        away_team_id: NBA team ID for away (optional, will lookup if needed)
        n_recent_games: Number of recent games to analyze (default 10)
        season: Season string (default '2025-26')

    Returns:
        Dict with:
        - features: Dict mapping feature names to values
        - feature_array: List of values in order (for dot product)
        - metadata: Dict with diagnostic info about feature quality

    Example:
        >>> features = build_feature_vector('BOS', 'LAL', 'game123', '2025-11-20')
        >>> features['features']['home_recent_off_delta']
        -2.9  # BOS offense cooled off recently
        >>> features['feature_array']
        [1.0, -2.9, -1.9, 1.5, 0.8, 225.3, 218.1, 208.2, 220.4]
    """
    print(f'[feature_builder] Building features for {home_team} vs {away_team} (game {game_id})')

    # Get team IDs if not provided
    if not home_team_id or not away_team_id:
        all_teams = get_all_teams()
        home_data = next((t for t in all_teams if t['abbreviation'] == home_team), None)
        away_data = next((t for t in all_teams if t['abbreviation'] == away_team), None)

        if not home_data or not away_data:
            raise ValueError(f'Could not find team data for {home_team} or {away_team}')

        home_team_id = home_data['id']
        away_team_id = away_data['id']

    # Step 1: Get recent form for both teams
    print(f'[feature_builder] Computing recent form features...')
    home_form = compute_recent_form_features(
        home_team, as_of_date,
        n=n_recent_games,
        team_id=home_team_id,
        season=season
    )
    away_form = compute_recent_form_features(
        away_team, as_of_date,
        n=n_recent_games,
        team_id=away_team_id,
        season=season
    )

    # Step 2: Get opponent classifications (what bucket is each team in?)
    print(f'[feature_builder] Classifying teams into strength buckets...')

    # Trigger background refresh if needed (non-blocking)
    team_rankings.refresh_rankings_if_needed(season, background=True)

    home_stats = team_rankings.get_team_stats_with_ranks(home_team_id, season)
    away_stats = team_rankings.get_team_stats_with_ranks(away_team_id, season)

    home_off_bucket = classify_team_bucket(home_stats, 'off_rtg') if home_stats else 'mid'
    home_def_bucket = classify_team_bucket(home_stats, 'def_rtg') if home_stats else 'mid'
    away_off_bucket = classify_team_bucket(away_stats, 'off_rtg') if away_stats else 'mid'
    away_def_bucket = classify_team_bucket(away_stats, 'def_rtg') if away_stats else 'mid'

    print(f'[feature_builder] {home_team}: {home_off_bucket} offense, {home_def_bucket} defense')
    print(f'[feature_builder] {away_team}: {away_off_bucket} offense, {away_def_bucket} defense')

    # Step 3: Get matchup profiles (how has each team performed vs these buckets?)
    print(f'[feature_builder] Getting matchup profiles...')
    home_profile = get_matchup_profile(home_team, away_off_bucket, away_def_bucket, season)
    away_profile = get_matchup_profile(away_team, home_off_bucket, home_def_bucket, season)

    # Step 4: Build feature vector
    features = {
        'bias': 1.0,  # Always 1 for intercept

        # Recent form deltas
        'home_recent_off_delta': home_form['recent_off_delta'],
        'home_recent_def_delta': home_form['recent_def_delta'],
        'away_recent_off_delta': away_form['recent_off_delta'],
        'away_recent_def_delta': away_form['recent_def_delta'],

        # Matchup-specific features
        # Home team's performance vs away's offensive strength
        'home_vs_off_bucket_total': home_profile.get(f'vs_off_{away_off_bucket}_avg_total', 0.0),

        # Away team's performance vs home's offensive strength
        'away_vs_off_bucket_total': away_profile.get(f'vs_off_{home_off_bucket}_avg_total', 0.0),

        # Home team's performance vs away's defensive strength
        'home_vs_def_bucket_total': home_profile.get(f'vs_def_{away_def_bucket}_avg_total', 0.0),

        # Away team's performance vs home's defensive strength
        'away_vs_def_bucket_total': away_profile.get(f'vs_def_{home_def_bucket}_avg_total', 0.0)
    }

    # Create feature array (list) for dot product computation
    feature_array = [features[name] for name in FEATURE_NAMES]

    # Build metadata for diagnostics
    metadata = {
        'feature_version': 'v1',
        'recent_games_n': n_recent_games,
        'home_recent_games_found': home_form['games_found'],
        'away_recent_games_found': away_form['games_found'],
        'home_recent_data_quality': home_form['data_quality'],
        'away_recent_data_quality': away_form['data_quality'],
        'home_off_bucket': home_off_bucket,
        'home_def_bucket': home_def_bucket,
        'away_off_bucket': away_off_bucket,
        'away_def_bucket': away_def_bucket,
        'home_vs_off_games': home_profile.get(f'games_vs_off_{away_off_bucket}', 0),
        'away_vs_off_games': away_profile.get(f'games_vs_off_{home_off_bucket}', 0),
        'home_vs_def_games': home_profile.get(f'games_vs_def_{away_def_bucket}', 0),
        'away_vs_def_games': away_profile.get(f'games_vs_def_{home_def_bucket}', 0),
        'computed_at': datetime.now().isoformat()
    }

    print(f'[feature_builder] Feature vector built successfully')
    print(f'[feature_builder] Recent form quality: home={home_form["data_quality"]}, away={away_form["data_quality"]}')

    return {
        'features': features,
        'feature_array': feature_array,
        'metadata': metadata
    }


def compute_feature_correction(feature_vector: Dict, feature_weights: Dict) -> float:
    """
    Compute total correction from feature vector and weights

    total_correction = w·x = Σ(w_i * x_i)

    Args:
        feature_vector: Dict from build_feature_vector()['features']
        feature_weights: Dict from model.json['feature_weights']

    Returns:
        float: Total correction to add to base prediction

    Example:
        >>> w = {'bias': 0.5, 'home_recent_off_delta': 0.3, ...}
        >>> x = {'bias': 1.0, 'home_recent_off_delta': -2.9, ...}
        >>> compute_feature_correction(x, w)
        1.23  # Add 1.23 points to base prediction
    """
    total_corr = 0.0

    for feature_name in FEATURE_NAMES:
        weight = feature_weights.get(feature_name, 0.0)
        value = feature_vector.get(feature_name, 0.0)
        total_corr += weight * value

    return round(total_corr, 2)


def get_empty_feature_vector() -> Dict:
    """
    Return empty/zero feature vector when data is unavailable

    Useful for backward compatibility or when features can't be computed
    """
    features = {name: 0.0 for name in FEATURE_NAMES}
    features['bias'] = 1.0  # Bias always 1

    return {
        'features': features,
        'feature_array': [features[name] for name in FEATURE_NAMES],
        'metadata': {
            'feature_version': 'v1',
            'error': 'Could not compute features',
            'computed_at': datetime.now().isoformat()
        }
    }
