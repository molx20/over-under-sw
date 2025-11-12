"""
Simple team ratings prediction model with online learning

Uses a lightweight rating system:
- Base points per team (default: 100)
- Home court advantage (default: +2)
- Per-team offensive and defensive ratings

Formula:
  PTS_home_hat = base + HCA + Off[home] - Def[away]
  PTS_away_hat = base - HCA + Off[away] - Def[home]

Learning updates (gradient descent with η = 0.02):
  err_h = pts_home_final - PTS_home_hat
  err_a = pts_away_final - PTS_away_hat

  Off[home] += η * err_h
  Def[away] -= η * err_h
  Off[away] += η * err_a
  Def[home] -= η * err_a

All ratings clamped to [-20, +20] to prevent runaway values.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Tuple

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'model.json')

def _load_model() -> Dict:
    """
    Load the team ratings model from GitHub (source of truth) with local fallback

    On Vercel serverless, always fetch from GitHub to get latest ratings.
    Fall back to local file if GitHub is unavailable (e.g., no credentials).
    """
    # Try to fetch from GitHub first (source of truth for updated ratings)
    from utils.github_persistence import fetch_model_from_github
    model = fetch_model_from_github()
    if model:
        return model

    # Fall back to local file if GitHub fetch failed
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, 'r') as f:
            return json.load(f)

    raise FileNotFoundError(f"Model file not found at {MODEL_PATH} and GitHub fetch failed")

def _save_model(model_data: Dict) -> None:
    """
    Save the team ratings model (skip local save on read-only serverless filesystem)

    On Vercel, we can't write to the filesystem, so we only update the timestamp
    and rely on GitHub persistence. Local saves work in development.
    """
    model_data['last_updated'] = datetime.now(timezone.utc).isoformat()

    # Try to save locally (works in development, fails silently on Vercel)
    try:
        with open(MODEL_PATH, 'w') as f:
            json.dump(model_data, f, indent=2)
    except (OSError, IOError) as e:
        # Read-only filesystem on serverless (expected on Vercel)
        print(f"Local save skipped (read-only filesystem): {e}")
        pass

def _clamp(value: float, min_val: float = -20, max_val: float = 20) -> float:
    """Clamp a value to the range [min_val, max_val]"""
    return max(min_val, min(max_val, value))

def get_model_data() -> Dict:
    """Public method to get current model data (for API responses)"""
    return _load_model()

def predict(home_tricode: str, away_tricode: str) -> Dict:
    """
    Predict game score using team ratings model

    Args:
        home_tricode: Home team tricode (e.g., 'BOS')
        away_tricode: Away team tricode (e.g., 'LAL')

    Returns:
        Dict with predictions:
        {
            'home_pts': float,
            'home_pts_rounded': int,
            'away_pts': float,
            'away_pts_rounded': int,
            'predicted_total': float,
            'model_version': str
        }

    Raises:
        ValueError: If team tricode not found in model
    """
    model = _load_model()

    # Validate teams exist
    teams = model['teams']
    if home_tricode not in teams:
        raise ValueError(f"Home team '{home_tricode}' not found in model")
    if away_tricode not in teams:
        raise ValueError(f"Away team '{away_tricode}' not found in model")

    # Get parameters
    base = model['parameters']['base']
    hca = model['parameters']['hca']

    # Get team ratings
    home_off = teams[home_tricode]['off']
    home_def = teams[home_tricode]['def']
    away_off = teams[away_tricode]['off']
    away_def = teams[away_tricode]['def']

    # Calculate predictions
    # PTS_home_hat = base + HCA + Off[home] - Def[away]
    # PTS_away_hat = base - HCA + Off[away] - Def[home]
    home_pts = base + hca + home_off - away_def
    away_pts = base - hca + away_off - home_def

    return {
        'home_pts': round(home_pts, 2),
        'home_pts_rounded': round(home_pts),
        'away_pts': round(away_pts, 2),
        'away_pts_rounded': round(away_pts),
        'predicted_total': round(home_pts + away_pts, 2),
        'model_version': model['version']
    }

def update_ratings(
    home_tricode: str,
    away_tricode: str,
    home_pts_final: float,
    away_pts_final: float
) -> Dict:
    """
    Update team ratings based on actual game result using online learning

    Args:
        home_tricode: Home team tricode
        away_tricode: Away team tricode
        home_pts_final: Actual home team points scored
        away_pts_final: Actual away team points scored

    Returns:
        Dict with updated ratings and metadata:
        {
            'old_ratings': {...},
            'new_ratings': {...},
            'errors': {'home': float, 'away': float},
            'learning_rate': float
        }

    Raises:
        ValueError: If team tricode not found in model
    """
    model = _load_model()

    # Validate teams exist
    teams = model['teams']
    if home_tricode not in teams:
        raise ValueError(f"Home team '{home_tricode}' not found in model")
    if away_tricode not in teams:
        raise ValueError(f"Away team '{away_tricode}' not found in model")

    # Get parameters
    base = model['parameters']['base']
    hca = model['parameters']['hca']
    eta = model['parameters']['learning_rate']

    # Get current ratings (before update)
    home_off_old = teams[home_tricode]['off']
    home_def_old = teams[home_tricode]['def']
    away_off_old = teams[away_tricode]['off']
    away_def_old = teams[away_tricode]['def']

    # Calculate predictions (what model predicted)
    pts_home_hat = base + hca + home_off_old - away_def_old
    pts_away_hat = base - hca + away_off_old - home_def_old

    # Calculate errors
    err_h = home_pts_final - pts_home_hat
    err_a = away_pts_final - pts_away_hat

    # Apply gradient-style updates
    # Off[home] += η * err_h
    # Def[away] -= η * err_h
    # Off[away] += η * err_a
    # Def[home] -= η * err_a
    home_off_new = _clamp(home_off_old + eta * err_h)
    away_def_new = _clamp(away_def_old - eta * err_h)
    away_off_new = _clamp(away_off_old + eta * err_a)
    home_def_new = _clamp(home_def_old - eta * err_a)

    # Update model
    teams[home_tricode]['off'] = home_off_new
    teams[home_tricode]['def'] = home_def_new
    teams[away_tricode]['off'] = away_off_new
    teams[away_tricode]['def'] = away_def_new

    # Save updated model
    _save_model(model)

    # Return update summary including the full updated model
    return {
        'old_ratings': {
            home_tricode: {'off': home_off_old, 'def': home_def_old},
            away_tricode: {'off': away_off_old, 'def': away_def_old}
        },
        'new_ratings': {
            home_tricode: {'off': home_off_new, 'def': home_def_new},
            away_tricode: {'off': away_off_new, 'def': away_def_new}
        },
        'errors': {
            'home': round(err_h, 2),
            'away': round(err_a, 2)
        },
        'predictions': {
            'home_predicted': round(pts_home_hat, 2),
            'away_predicted': round(pts_away_hat, 2),
            'home_actual': home_pts_final,
            'away_actual': away_pts_final
        },
        'learning_rate': eta,
        'updated_model': model  # Include full updated model for GitHub commit
    }
