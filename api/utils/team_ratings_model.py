"""
Simple team ratings prediction model with online learning

Uses a lightweight rating system:
- Base points per team (default: 100)
- Home court advantage (default: +2)
- Per-team offensive and defensive ratings
- Total bias (learned from sportsbook lines)

Formula:
  PTS_home_hat = base + HCA + Off[home] - Def[away]
  PTS_away_hat = base - HCA + Off[away] - Def[home]
  total_hat = PTS_home_hat + PTS_away_hat + total_bias

Learning updates (gradient descent with η = 0.02):
  err_h = pts_home_final - PTS_home_hat
  err_a = pts_away_final - PTS_away_hat

  Off[home] += η * err_h
  Def[away] -= η * err_h
  Off[away] += η * err_a
  Def[home] -= η * err_a

Line-aware learning (η_line = 0.005):
  If |line_error| < |model_error|:
    total_bias += η_line * (sportsbook_line - pred_total)

All ratings clamped to [-20, +20] to prevent runaway values.
Total bias clamped to [-5, +5] to prevent over-correction.
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
    try:
        from api.utils.github_persistence import fetch_model_from_github
        model = fetch_model_from_github()
        if model:
            return model
    except ImportError:
        # Fallback for when running from within api/utils directory
        try:
            from github_persistence import fetch_model_from_github
            model = fetch_model_from_github()
            if model:
                return model
        except ImportError:
            pass

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


def predict_with_bias(home_tricode: str, away_tricode: str) -> Dict:
    """
    Predict game score using team ratings model WITH total bias applied

    This is the enhanced prediction that incorporates learning from sportsbook lines.
    Use this for generating pre-game predictions that will be stored and compared.

    Args:
        home_tricode: Home team tricode (e.g., 'BOS')
        away_tricode: Away team tricode (e.g., 'LAL')

    Returns:
        Dict with predictions:
        {
            'home_pts': float,
            'away_pts': float,
            'total_raw': float,      # Total before bias
            'total_bias': float,     # Current bias value
            'predicted_total': float, # Total with bias applied
            'home_pts_rounded': int,
            'away_pts_rounded': int,
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
    total_bias = model['parameters'].get('total_bias', 0)  # Default to 0 if not present

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

    # Calculate total with bias
    total_raw = home_pts + away_pts
    predicted_total = total_raw + total_bias

    return {
        'home_pts': round(home_pts, 2),
        'away_pts': round(away_pts, 2),
        'total_raw': round(total_raw, 2),
        'total_bias': round(total_bias, 2),
        'predicted_total': round(predicted_total, 2),
        'home_pts_rounded': round(home_pts),
        'away_pts_rounded': round(away_pts),
        'model_version': model.get('version', '1.0')
    }


def update_from_sportsbook_line(
    pred_total: float,
    sportsbook_line: float,
    actual_total: float
) -> Dict:
    """
    Update model based on comparison between model prediction, sportsbook line, and actual result

    This implements line-aware learning:
    1. Computes how far off the model was vs how far off the line was
    2. If the line beat the model, nudges total_bias toward the line
    3. Returns error metrics for database storage

    Args:
        pred_total: Model's predicted total (before this learning step)
        sportsbook_line: Sportsbook over/under closing line
        actual_total: Actual final total points scored

    Returns:
        Dict with error metrics and updated bias:
        {
            'model_error': float,        # actual - predicted
            'line_error': float,         # actual - line
            'model_abs_error': float,
            'line_abs_error': float,
            'model_beat_line': bool,
            'line_gap': float,           # line - predicted
            'old_total_bias': float,
            'new_total_bias': float,
            'bias_adjustment': float,
            'updated_model': Dict        # Full model for GitHub commit
        }
    """
    model = _load_model()

    # Get current total_bias
    old_total_bias = model['parameters'].get('total_bias', 0)

    # Get line learning rate (default 0.005 if not present)
    eta_line = model['parameters'].get('line_learning_rate', 0.005)

    # 1. Calculate errors
    model_error = actual_total - pred_total
    line_error = actual_total - sportsbook_line
    model_abs_error = abs(model_error)
    line_abs_error = abs(line_error)
    model_beat_line = model_abs_error < line_abs_error

    # 2. Calculate gap between line and prediction
    line_gap = sportsbook_line - pred_total

    # 3. Update total_bias toward the line IF the line was more accurate
    # This gradually teaches the model to respect the market wisdom
    new_total_bias = old_total_bias
    bias_adjustment = 0

    if not model_beat_line:
        # Line was more accurate, so nudge our bias toward it
        bias_adjustment = eta_line * line_gap
        new_total_bias = old_total_bias + bias_adjustment

        # Clamp to [-5, +5] to prevent over-correction
        new_total_bias = max(-5.0, min(5.0, new_total_bias))

        # Update model
        model['parameters']['total_bias'] = new_total_bias
        _save_model(model)

    return {
        'model_error': round(model_error, 2),
        'line_error': round(line_error, 2),
        'model_abs_error': round(model_abs_error, 2),
        'line_abs_error': round(line_abs_error, 2),
        'model_beat_line': model_beat_line,
        'line_gap': round(line_gap, 2),
        'old_total_bias': round(old_total_bias, 2),
        'new_total_bias': round(new_total_bias, 2),
        'bias_adjustment': round(bias_adjustment, 4),
        'updated_model': model  # Include full updated model for GitHub commit
    }


def get_total_bias() -> float:
    """Get the current total_bias parameter"""
    model = _load_model()
    return model['parameters'].get('total_bias', 0)


def set_total_bias(value: float) -> Dict:
    """
    Manually set the total_bias parameter (for debugging/testing)

    Args:
        value: New total_bias value (will be clamped to [-5, +5])

    Returns:
        Dict with old and new values
    """
    model = _load_model()
    old_value = model['parameters'].get('total_bias', 0)
    new_value = max(-5.0, min(5.0, value))

    model['parameters']['total_bias'] = new_value
    _save_model(model)

    return {
        'old_total_bias': round(old_value, 2),
        'new_total_bias': round(new_value, 2)
    }
