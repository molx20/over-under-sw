"""
Pace Analysis Constants

Centralized configuration for pace-based scoring analysis.
All thresholds are tunable in one place.
"""

# ============================================================================
# PACE BUCKET THRESHOLDS
# ============================================================================

# Pace bucket classification (possessions per 48 minutes)
PACE_SLOW_THRESHOLD = 96.0    # Below this = slow pace game
PACE_FAST_THRESHOLD = 101.0   # Above this = fast pace game
# Between thresholds = normal pace game

# ============================================================================
# DATA QUALITY THRESHOLDS
# ============================================================================

# Minimum games required to trust a pace bucket's statistics
MIN_GAMES_PER_BUCKET = 3

# ============================================================================
# PREDICTION ADJUSTMENT SETTINGS
# ============================================================================

# Pace effect moderation factor
# How much to trust the pace bucket adjustment vs season average
# 0.5 = Use 50% of the observed difference between bucket and season avg
PACE_EFFECT_WEIGHT = 0.5

# Maximum allowed adjustment from pace effect (points)
# Prevents wild swings from small sample outliers
MAX_PACE_ADJUSTMENT = 4.0
