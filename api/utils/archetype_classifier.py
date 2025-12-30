"""
Archetype Classifier Module

Defines 5 offensive and 5 defensive archetypes using rule-based thresholds.
Assigns teams to archetypes based on standardized feature vectors (z-scores).
Detects style shifts between season and last-10-games windows.

Design Principles:
- Interpretable: Every archetype defined by clear, human-readable rules
- Stable: Rule-based clustering ensures consistent assignments
- Actionable: Archetypes directly inform matchup analysis
- Data-Driven: Rules derived from league distributions, not narratives
"""

from typing import Dict, Tuple, List, Optional
import logging
import statistics

logger = logging.getLogger(__name__)

try:
    from api.utils.archetype_features import calculate_all_team_features, OFFENSIVE_FEATURE_NAMES, DEFENSIVE_FEATURE_NAMES
except ImportError:
    from archetype_features import calculate_all_team_features, OFFENSIVE_FEATURE_NAMES, DEFENSIVE_FEATURE_NAMES

# ============================================================================
# ARCHETYPE DEFINITIONS
# ============================================================================

OFFENSIVE_ARCHETYPES = {
    'foul_pressure_paint_attack': {
        'name': 'Foul-Pressure Paint Attack',
        'rules': {
            'ft_rate': ('>', 0.5),           # Z-score > 0.5 (high FT rate)
            'pitp_share': ('>', 0.3),        # High paint share
            'three_pa_rate': ('<', -0.3),    # Low 3PA rate
        },
        'description': 'Drives to the rim, draws fouls, and scores heavily in the paint. Low reliance on three-pointers.',
        'scoring_profile': 'FT-heavy, paint-heavy, low perimeter volume'
    },

    'perimeter_spacing_offense': {
        'name': 'Perimeter Spacing Offense',
        'rules': {
            'three_pa_rate': ('>', 0.5),     # High 3PA rate
            'efg_pct': ('>', 0.3),           # High efficiency
            'pitp_share': ('<', -0.3),       # Low paint share
        },
        'description': 'Relies on three-point shooting and floor spacing. Minimizes paint scoring in favor of perimeter volume.',
        'scoring_profile': 'Perimeter-heavy, 3PT volume, spacing-dependent'
    },

    'balanced_high_assist': {
        'name': 'Balanced High-Assist',
        'rules': {
            'assist_rate': ('>', 0.5),       # High assist rate
            'turnover_rate': ('<', -0.2),    # Low turnovers
            'pitp_share': ('between', -0.3, 0.3),  # Balanced paint/perimeter
            'three_pa_rate': ('between', -0.3, 0.3),
        },
        'description': 'Ball-movement focused offense with balanced scoring sources. High assists, low turnovers.',
        'scoring_profile': 'Balanced 2PT/3PT, ball-sharing, efficient'
    },

    'second_chance_rebounders': {
        'name': 'Second-Chance Rebounders',
        'rules': {
            'second_chance_ppg': ('>', 0.5), # High 2nd chance points
            'pitp_ppg': ('>', 0.3),          # Paint presence
            'turnover_rate': ('<', 0.0),     # Average or low TOs
        },
        'description': 'Offensive rebounding-driven offense. Creates additional possessions and scores on putbacks.',
        'scoring_profile': 'OREB-dependent, paint-heavy, possession extension'
    },

    'iso_low_assist': {
        'name': 'ISO Low-Assist',
        'rules': {
            'assist_rate': ('<', -0.5),      # Low assist rate
            'turnover_rate': ('>', 0.2),     # Higher turnovers
            'efg_pct': ('>', -0.5),          # Not terrible efficiency
        },
        'description': 'Isolation-heavy offense with less ball movement. Individual creation over team sharing.',
        'scoring_profile': 'ISO-heavy, lower assists, individual creation'
    }
}

DEFENSIVE_ARCHETYPES = {
    'foul_baiting_suppressor': {
        'name': 'Foul-Baiting Suppressor',
        'rules': {
            'opp_ft_rate': ('<', -0.5),      # Suppress opponent FT rate
            'opp_ft_ppg': ('<', -0.4),       # Low FT points allowed
            'opp_pitp_ppg': ('<', -0.2),     # Protect paint
        },
        'description': 'Prevents opponents from drawing fouls and getting to the line. Strong paint protection.',
        'allows': 'Minimal FT attempts',
        'suppresses': 'FT rate, paint penetration'
    },

    'perimeter_lockdown': {
        'name': 'Perimeter Lockdown',
        'rules': {
            'opp_three_pa_rate': ('<', -0.3), # Suppress 3PA rate
            'opp_efg_pct': ('<', -0.4),       # Low eFG% allowed
            'opp_pitp_ppg': ('>', 0.2),       # Allow more paint
        },
        'description': 'Elite perimeter defense that forces opponents inside. Limits three-point volume and efficiency.',
        'allows': 'Paint scoring',
        'suppresses': '3PT volume and efficiency'
    },

    'paint_protection_elite': {
        'name': 'Paint Protection Elite',
        'rules': {
            'opp_pitp_ppg': ('<', -0.5),      # Very low paint points allowed
            'opp_three_pa_rate': ('>', 0.3),  # Force perimeter attempts
            'opp_efg_pct': ('<', -0.2),       # Solid overall efficiency
        },
        'description': 'Rim protection and paint defense forces opponents to the perimeter. Strong interior defense.',
        'allows': 'Perimeter attempts',
        'suppresses': 'Paint scoring, rim attempts'
    },

    'turnover_forcing_pressure': {
        'name': 'Turnover-Forcing Pressure',
        'rules': {
            'opp_turnovers_forced': ('>', 0.5), # Force high turnovers
            'opp_pace': ('>', 0.3),              # High pace allowed
        },
        'description': 'Aggressive, pressure defense that creates turnovers. High-pace, high-variance style.',
        'allows': 'Fast pace, higher possessions',
        'suppresses': 'Clean possessions, ball security'
    },

    'balanced_disciplined': {
        'name': 'Balanced Disciplined',
        'rules': {
            'opp_efg_pct': ('<', -0.3),         # Low eFG% allowed
            'opp_ft_rate': ('between', -0.3, 0.3), # Average FT rate
            'opp_three_pa_rate': ('between', -0.3, 0.3), # Balanced
            'opp_pitp_ppg': ('between', -0.3, 0.3),
        },
        'description': 'Fundamentally sound defense without extreme tendencies. Solid across all areas.',
        'allows': 'Nothing specific',
        'suppresses': 'Overall efficiency'
    }
}

# Archetype priority order (checked in order, first match wins)
OFFENSIVE_ARCHETYPE_ORDER = [
    'perimeter_spacing_offense',
    'foul_pressure_paint_attack',
    'second_chance_rebounders',
    'balanced_high_assist',
    'iso_low_assist'
]

DEFENSIVE_ARCHETYPE_ORDER = [
    'paint_protection_elite',
    'perimeter_lockdown',
    'foul_baiting_suppressor',
    'turnover_forcing_pressure',
    'balanced_disciplined'
]

# ============================================================================
# FEATURE STANDARDIZATION
# ============================================================================

def standardize_features(all_team_features: Dict, feature_type: str) -> Dict:
    """
    Calculate z-scores for all features across all teams.

    Z-score = (value - mean) / std_dev

    Args:
        all_team_features: Dict of team_id -> features
        feature_type: 'offensive' or 'defensive'

    Returns:
        Dict of team_id -> standardized_features
    """
    feature_names = OFFENSIVE_FEATURE_NAMES if feature_type == 'offensive' else DEFENSIVE_FEATURE_NAMES

    # Collect all values for each feature across all teams
    feature_values = {name: [] for name in feature_names}

    for team_id, features in all_team_features.items():
        for feature_name in feature_names:
            value = features.get(feature_name)
            if value is not None:
                feature_values[feature_name].append(value)

    # Calculate mean and stdev for each feature
    feature_stats = {}
    for feature_name, values in feature_values.items():
        if len(values) > 1:
            mean = statistics.mean(values)
            stdev = statistics.stdev(values) if len(values) > 2 else 1.0
            feature_stats[feature_name] = {'mean': mean, 'stdev': stdev}
        else:
            feature_stats[feature_name] = {'mean': 0.0, 'stdev': 1.0}

    logger.debug(f"{feature_type.capitalize()} feature statistics: {feature_stats}")

    # Standardize features for each team
    standardized = {}
    for team_id, features in all_team_features.items():
        standardized[team_id] = {}
        for feature_name in feature_names:
            value = features.get(feature_name, 0.0)
            stats = feature_stats[feature_name]
            if stats['stdev'] > 0:
                z_score = (value - stats['mean']) / stats['stdev']
            else:
                z_score = 0.0
            standardized[team_id][feature_name] = z_score

        # Preserve metadata
        standardized[team_id]['games_count'] = features.get('games_count', 0)
        standardized[team_id]['window'] = features.get('window', 'unknown')

    return standardized


# ============================================================================
# RULE MATCHING
# ============================================================================

def _check_rule(z_score: float, operator: str, threshold: float, threshold2: Optional[float] = None) -> bool:
    """
    Check if a z-score matches a rule.

    Args:
        z_score: Standardized feature value
        operator: '>', '<', or 'between'
        threshold: Primary threshold value
        threshold2: Secondary threshold (for 'between' operator)

    Returns:
        True if rule matches
    """
    if operator == '>':
        return z_score > threshold
    elif operator == '<':
        return z_score < threshold
    elif operator == 'between':
        if threshold2 is None:
            logger.error("'between' operator requires threshold2")
            return False
        return threshold <= z_score <= threshold2
    else:
        logger.error(f"Unknown operator: {operator}")
        return False


def _check_all_rules(standardized_features: Dict, archetype_rules: Dict) -> bool:
    """
    Check if all rules for an archetype are satisfied.

    Args:
        standardized_features: Z-scores for all features
        archetype_rules: Dict of feature_name -> (operator, threshold, [threshold2])

    Returns:
        True if ALL rules match
    """
    for feature_name, rule_spec in archetype_rules.items():
        z_score = standardized_features.get(feature_name, 0.0)

        if len(rule_spec) == 2:
            operator, threshold = rule_spec
            if not _check_rule(z_score, operator, threshold):
                return False
        elif len(rule_spec) == 3:
            operator, threshold, threshold2 = rule_spec
            if not _check_rule(z_score, operator, threshold, threshold2):
                return False
        else:
            logger.error(f"Invalid rule spec for {feature_name}: {rule_spec}")
            return False

    return True


# ============================================================================
# ARCHETYPE ASSIGNMENT
# ============================================================================

def assign_offensive_archetype(standardized_features: Dict) -> str:
    """
    Assign team to offensive archetype using rule matching.

    Process:
    1. Check each archetype's rules in priority order
    2. Return first match
    3. Default to 'balanced_high_assist' if no match

    Args:
        standardized_features: Dict with 9 standardized offensive features

    Returns:
        Archetype ID string
    """
    for archetype_id in OFFENSIVE_ARCHETYPE_ORDER:
        archetype_def = OFFENSIVE_ARCHETYPES[archetype_id]
        if _check_all_rules(standardized_features, archetype_def['rules']):
            logger.debug(f"Matched offensive archetype: {archetype_id}")
            return archetype_id

    # Default fallback
    logger.debug("No offensive archetype matched, defaulting to balanced_high_assist")
    return 'balanced_high_assist'


def assign_defensive_archetype(standardized_features: Dict) -> str:
    """
    Assign team to defensive archetype using rule matching.

    Process:
    1. Check each archetype's rules in priority order
    2. Return first match
    3. Default to 'balanced_disciplined' if no match

    Args:
        standardized_features: Dict with 7 standardized defensive features

    Returns:
        Archetype ID string
    """
    for archetype_id in DEFENSIVE_ARCHETYPE_ORDER:
        archetype_def = DEFENSIVE_ARCHETYPES[archetype_id]
        if _check_all_rules(standardized_features, archetype_def['rules']):
            logger.debug(f"Matched defensive archetype: {archetype_id}")
            return archetype_id

    # Default fallback
    logger.debug("No defensive archetype matched, defaulting to balanced_disciplined")
    return 'balanced_disciplined'


# ============================================================================
# STYLE SHIFT DETECTION
# ============================================================================

def detect_style_shift(season_archetype: str, last10_archetype: str,
                      archetype_type: str) -> Tuple[bool, str]:
    """
    Detect if team has shifted style in last 10 games.

    Args:
        season_archetype: Season archetype ID
        last10_archetype: Last 10 archetype ID
        archetype_type: 'offensive' or 'defensive'

    Returns:
        (has_shifted: bool, shift_description: str)
    """
    if season_archetype != last10_archetype:
        archetype_map = OFFENSIVE_ARCHETYPES if archetype_type == 'offensive' else DEFENSIVE_ARCHETYPES
        from_name = archetype_map[season_archetype]['name']
        to_name = archetype_map[last10_archetype]['name']
        shift_desc = f"STYLE SHIFT: {from_name} → {to_name}"
        logger.info(f"{archetype_type.capitalize()} {shift_desc}")
        return (True, shift_desc)
    return (False, "")


# ============================================================================
# FULL TEAM ASSIGNMENT
# ============================================================================

def assign_all_team_archetypes(season: str = '2025-26') -> Dict:
    """
    Assign archetypes to all teams for both season and last 10 games.

    Process:
    1. Calculate features for all teams (season + last 10)
    2. Standardize features separately for each window
    3. Assign archetypes using rules
    4. Detect style shifts

    Returns:
        {
            team_id: {
                'season_offensive': archetype_id,
                'season_defensive': archetype_id,
                'last10_offensive': archetype_id,
                'last10_defensive': archetype_id,
                'offensive_style_shift': bool,
                'defensive_style_shift': bool,
                'offensive_shift_details': str (if shifted),
                'defensive_shift_details': str (if shifted)
            }
        }
    """
    logger.info(f"Starting archetype assignment for season {season}")

    # Step 1: Calculate features for all teams
    all_features = calculate_all_team_features(season)

    # Step 2: Standardize features for each window
    season_offensive_std = standardize_features(
        {tid: data['season'] for tid, data in all_features['offensive'].items()},
        'offensive'
    )
    last10_offensive_std = standardize_features(
        {tid: data['last_10'] for tid, data in all_features['offensive'].items()},
        'offensive'
    )

    season_defensive_std = standardize_features(
        {tid: data['season'] for tid, data in all_features['defensive'].items()},
        'defensive'
    )
    last10_defensive_std = standardize_features(
        {tid: data['last_10'] for tid, data in all_features['defensive'].items()},
        'defensive'
    )

    # Step 3 & 4: Assign archetypes and detect shifts
    assignments = {}

    team_ids = set(all_features['offensive'].keys()) & set(all_features['defensive'].keys())

    for team_id in team_ids:
        # Assign offensive archetypes
        season_off = assign_offensive_archetype(season_offensive_std[team_id])
        last10_off = assign_offensive_archetype(last10_offensive_std[team_id])
        off_shift, off_shift_details = detect_style_shift(season_off, last10_off, 'offensive')

        # Assign defensive archetypes
        season_def = assign_defensive_archetype(season_defensive_std[team_id])
        last10_def = assign_defensive_archetype(last10_defensive_std[team_id])
        def_shift, def_shift_details = detect_style_shift(season_def, last10_def, 'defensive')

        assignments[team_id] = {
            'season_offensive': season_off,
            'season_defensive': season_def,
            'last10_offensive': last10_off,
            'last10_defensive': last10_def,
            'offensive_style_shift': off_shift,
            'defensive_style_shift': def_shift,
            'offensive_shift_details': off_shift_details,
            'defensive_shift_details': def_shift_details
        }

    logger.info(f"Archetype assignment complete for {len(assignments)} teams")
    return assignments
