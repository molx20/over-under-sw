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
import math

logger = logging.getLogger(__name__)

# ============================================================================
# SCIPY REQUIRED DEPENDENCY - Percentile calculation
# ============================================================================

try:
    from scipy.stats import norm
    logger.info("[ARCHETYPE_CLASSIFIER] scipy.stats successfully imported")
except ImportError as e:
    error_msg = (
        "CRITICAL: scipy is required for archetype percentile calculations. "
        "Install scipy with: pip install scipy>=1.13.1"
    )
    logger.error(f"[ARCHETYPE_CLASSIFIER] {error_msg}")
    raise RuntimeError(error_msg) from e


def _safe_zscore(x: float, mean: float, std: float) -> float:
    """
    Calculate z-score safely, handling edge cases.

    Args:
        x: Value to standardize
        mean: Mean of distribution
        std: Standard deviation

    Returns:
        Z-score (0 if std is 0)
    """
    if std == 0 or std is None or math.isnan(std):
        return 0.0
    return (x - mean) / std

try:
    from api.utils.archetype_features import (
        calculate_all_team_features,
        OFFENSIVE_FEATURE_NAMES,
        DEFENSIVE_FEATURE_NAMES,
        ASSISTS_FEATURE_NAMES,
        ASSISTS_DEFENSIVE_FEATURE_NAMES,
        REBOUNDS_FEATURE_NAMES,
        REBOUNDS_DEFENSIVE_FEATURE_NAMES,
        THREES_FEATURE_NAMES,
        THREES_DEFENSIVE_FEATURE_NAMES,
        TURNOVERS_FEATURE_NAMES,
        TURNOVERS_DEFENSIVE_FEATURE_NAMES
    )
except ImportError:
    from archetype_features import (
        calculate_all_team_features,
        OFFENSIVE_FEATURE_NAMES,
        DEFENSIVE_FEATURE_NAMES,
        ASSISTS_FEATURE_NAMES,
        ASSISTS_DEFENSIVE_FEATURE_NAMES,
        REBOUNDS_FEATURE_NAMES,
        REBOUNDS_DEFENSIVE_FEATURE_NAMES,
        THREES_FEATURE_NAMES,
        THREES_DEFENSIVE_FEATURE_NAMES,
        TURNOVERS_FEATURE_NAMES,
        TURNOVERS_DEFENSIVE_FEATURE_NAMES
    )

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
# NEW ARCHETYPE FAMILIES - ASSISTS
# ============================================================================

ASSISTS_OFFENSIVE_ARCHETYPES = {
    'ball_movement_maestro': {
        'name': 'Ball Movement Maestro',
        'rules': {
            'assist_rate': ('>', 0.5),
            'assists_per_100': ('>', 0.3)
        },
        'description': 'Elite ball movement with exceptional passing frequency. Team-oriented offense with high assist rate.',
        'profile': 'High assist rate, ball-sharing, team-first offense'
    },

    'high_volume_playmaking': {
        'name': 'High Volume Playmaking',
        'rules': {
            'assists': ('>', 0.3),
            'assist_rate': ('between', -0.3, 0.5),
        },
        'description': 'High volume of assists with solid rate. Generates plenty of scoring opportunities through passing.',
        'profile': 'High assist volume, good playmaking'
    },

    'iso_driven_low_assist': {
        'name': 'ISO Driven Low-Assist',
        'rules': {
            'assist_rate': ('<', -0.5),
            'assists': ('<', -0.3),
        },
        'description': 'Isolation-heavy offense with minimal passing. Relies on individual creation over ball movement.',
        'profile': 'Low assists, ISO-heavy, individual creation'
    },

    'balanced_sharing': {
        'name': 'Balanced Sharing',
        'rules': {
            'assist_rate': ('between', -0.5, 0.5),
        },
        'description': 'Balanced approach to ball movement. Neither high nor low assist tendencies.',
        'profile': 'Moderate assists, balanced playmaking'
    }
}

ASSISTS_DEFENSIVE_ARCHETYPES = {
    'assist_denial_elite': {
        'name': 'Assist Denial Elite',
        'rules': {
            'opp_assist_rate': ('<', -0.5),
            'opp_assists': ('<', -0.3),
        },
        'description': 'Forces opponents into isolation. Excellent at denying ball movement and disrupting passing lanes.',
        'allows': 'ISO plays',
        'suppresses': 'Ball movement, assist opportunities'
    },

    'rotation_scrambler': {
        'name': 'Rotation Scrambler',
        'rules': {
            'opp_assist_rate': ('between', -0.5, 0.0),
            'opp_assists': ('between', -0.5, 0.3),
        },
        'description': 'Solid rotations that disrupt passing angles. Makes opponents work harder for assists.',
        'allows': 'Some ball movement',
        'suppresses': 'Easy passing lanes'
    },

    'ball_movement_vulnerable': {
        'name': 'Ball Movement Vulnerable',
        'rules': {
            'opp_assist_rate': ('>', 0.3),
            'opp_assists': ('>', 0.2),
        },
        'description': 'Vulnerable to ball movement. Allows opponents to find open shooters and cutters easily.',
        'allows': 'High assist opportunities',
        'suppresses': 'Nothing specific'
    },

    'average_assist_defense': {
        'name': 'Average Assist Defense',
        'rules': {
            'opp_assist_rate': ('between', -0.3, 0.3),
        },
        'description': 'Standard defense against ball movement. No extreme tendencies in assist prevention.',
        'allows': 'Average ball movement',
        'suppresses': 'Nothing specific'
    }
}

ASSISTS_OFFENSIVE_ORDER = ['ball_movement_maestro', 'high_volume_playmaking', 'iso_driven_low_assist', 'balanced_sharing']
ASSISTS_DEFENSIVE_ORDER = ['assist_denial_elite', 'rotation_scrambler', 'ball_movement_vulnerable', 'average_assist_defense']


# ============================================================================
# NEW ARCHETYPE FAMILIES - REBOUNDS
# ============================================================================

REBOUNDS_OFFENSIVE_ARCHETYPES = {
    'crash_the_glass_elite': {
        'name': 'Crash the Glass Elite',
        'rules': {
            'offensive_rebounds': ('>', 0.6),
            'second_chance_points': ('>', 0.3),
        },
        'description': 'Dominant offensive rebounding creates extra possessions. Elite at second-chance opportunities.',
        'profile': 'High OREB, second-chance scoring, possession extension'
    },

    'selective_crasher': {
        'name': 'Selective Crasher',
        'rules': {
            'offensive_rebounds': ('between', 0.0, 0.6),
            'second_chance_points': ('between', -0.2, 0.3),
        },
        'description': 'Good offensive rebounding with selective crashing. Creates some extra possessions.',
        'profile': 'Above average OREB, balanced approach'
    },

    'transition_focused': {
        'name': 'Transition Focused',
        'rules': {
            'offensive_rebounds': ('<', -0.5),
        },
        'description': 'Prioritizes transition over offensive rebounding. Gets back on defense quickly.',
        'profile': 'Low OREB, transition first'
    },

    'balanced_rebounding': {
        'name': 'Balanced Rebounding',
        'rules': {
            'offensive_rebounds': ('between', -0.5, 0.0),
        },
        'description': 'Balanced approach to offensive rebounding. Neither aggressive nor passive.',
        'profile': 'Moderate OREB, balanced strategy'
    }
}

REBOUNDS_DEFENSIVE_ARCHETYPES = {
    'glass_protector_elite': {
        'name': 'Glass Protector Elite',
        'rules': {
            'defensive_rebounds': ('>', 0.6),  # Team gets many DREBs
            'opp_offensive_rebounds': ('<', -0.5),  # Opponent gets few OREBs
        },
        'description': 'Dominant defensive rebounding prevents second chances. Elite box-out fundamentals.',
        'allows': 'Minimal second chances',
        'suppresses': 'Opponent offensive rebounds, putbacks'
    },

    'solid_boxing_out': {
        'name': 'Solid Boxing Out',
        'rules': {
            'defensive_rebounds': ('between', 0.0, 0.6),
            'opp_offensive_rebounds': ('between', -0.5, 0.2),
        },
        'description': 'Good defensive rebounding with solid fundamentals. Limits second-chance opportunities.',
        'allows': 'Some second chances',
        'suppresses': 'Excessive offensive rebounds'
    },

    'vulnerable_to_crashes': {
        'name': 'Vulnerable to Crashes',
        'rules': {
            'defensive_rebounds': ('<', -0.4),
            'opp_offensive_rebounds': ('>', 0.3),
        },
        'description': 'Vulnerable to offensive rebounds. Allows too many second-chance opportunities.',
        'allows': 'High opponent OREB',
        'suppresses': 'Nothing specific'
    },

    'average_rebounding': {
        'name': 'Average Rebounding',
        'rules': {
            'defensive_rebounds': ('between', -0.4, 0.0),
        },
        'description': 'Average defensive rebounding. No extreme tendencies.',
        'allows': 'Average second chances',
        'suppresses': 'Nothing specific'
    }
}

REBOUNDS_OFFENSIVE_ORDER = ['crash_the_glass_elite', 'selective_crasher', 'transition_focused', 'balanced_rebounding']
REBOUNDS_DEFENSIVE_ORDER = ['glass_protector_elite', 'solid_boxing_out', 'vulnerable_to_crashes', 'average_rebounding']


# ============================================================================
# NEW ARCHETYPE FAMILIES - THREES
# ============================================================================

THREES_OFFENSIVE_ARCHETYPES = {
    'volume_three_bomber': {
        'name': 'Volume Three Bomber',
        'rules': {
            'three_pa_rate': ('>', 0.5),
            'fg3a': ('>', 0.4),
        },
        'description': 'Elite three-point shooting volume. Lives beyond the arc with high attempt rate.',
        'profile': 'High 3PA volume, perimeter-heavy, spacing offense'
    },

    'efficient_selective_shooter': {
        'name': 'Efficient Selective Shooter',
        'rules': {
            'fg3_pct': ('>', 0.5),
            'three_pa_rate': ('between', -0.2, 0.5),
        },
        'description': 'Selective but efficient three-point shooting. Quality over quantity approach.',
        'profile': 'High 3P%, selective shooting, efficient'
    },

    'three_avoidant': {
        'name': 'Three Avoidant',
        'rules': {
            'three_pa_rate': ('<', -0.5),
            'fg3a': ('<', -0.4),
        },
        'description': 'Avoids three-point shooting. Prefers midrange and paint scoring.',
        'profile': 'Low 3PA, inside-focused, traditional scoring'
    },

    'balanced_shooting': {
        'name': 'Balanced Shooting',
        'rules': {
            'three_pa_rate': ('between', -0.5, 0.5),
        },
        'description': 'Balanced three-point approach. Moderate volume and efficiency.',
        'profile': 'Average 3PT shooting, balanced offense'
    }
}

THREES_DEFENSIVE_ARCHETYPES = {
    'three_point_shutdown': {
        'name': 'Three-Point Shutdown',
        'rules': {
            'opp_fg3_pct': ('<', -0.5),
            'opp_three_pa_rate': ('<', -0.2),
        },
        'description': 'Elite three-point defense. Limits both volume and efficiency from deep.',
        'allows': 'Inside scoring',
        'suppresses': 'Three-point volume and efficiency'
    },

    'perimeter_contest_strong': {
        'name': 'Perimeter Contest Strong',
        'rules': {
            'opp_fg3_pct': ('<', -0.3),
            'opp_three_pa_rate': ('between', -0.3, 0.3),
        },
        'description': 'Strong perimeter contests make threes difficult. Limits efficiency more than volume.',
        'allows': 'Three-point attempts',
        'suppresses': 'Three-point efficiency'
    },

    'three_point_vulnerable': {
        'name': 'Three-Point Vulnerable',
        'rules': {
            'opp_fg3_pct': ('>', 0.3),
            'opp_three_pa_rate': ('>', 0.2),
        },
        'description': 'Vulnerable to three-point shooting. Allows both high volume and efficiency.',
        'allows': 'High 3PA volume and efficiency',
        'suppresses': 'Nothing specific'
    },

    'average_perimeter_defense': {
        'name': 'Average Perimeter Defense',
        'rules': {
            'opp_fg3_pct': ('between', -0.3, 0.3),
        },
        'description': 'Average three-point defense. No extreme tendencies.',
        'allows': 'Average three-point shooting',
        'suppresses': 'Nothing specific'
    }
}

THREES_OFFENSIVE_ORDER = ['volume_three_bomber', 'efficient_selective_shooter', 'three_avoidant', 'balanced_shooting']
THREES_DEFENSIVE_ORDER = ['three_point_shutdown', 'perimeter_contest_strong', 'three_point_vulnerable', 'average_perimeter_defense']


# ============================================================================
# NEW ARCHETYPE FAMILIES - TURNOVERS
# ============================================================================

TURNOVERS_OFFENSIVE_ARCHETYPES = {
    'ball_security_elite': {
        'name': 'Ball Security Elite',
        'rules': {
            'turnover_rate': ('<', -0.6),
            'turnovers': ('<', -0.5),
        },
        'description': 'Elite ball security with minimal turnovers. Takes care of the ball exceptionally well.',
        'profile': 'Low turnovers, ball security, careful play'
    },

    'solid_ball_handler': {
        'name': 'Solid Ball Handler',
        'rules': {
            'turnover_rate': ('between', -0.6, 0.0),
            'turnovers': ('between', -0.5, 0.2),
        },
        'description': 'Good ball security with below-average turnover rate. Solid fundamental ball handling.',
        'profile': 'Below average turnovers, solid handling'
    },

    'turnover_prone_aggressive': {
        'name': 'Turnover Prone Aggressive',
        'rules': {
            'turnover_rate': ('>', 0.3),
            'turnovers': ('>', 0.3),
        },
        'description': 'Aggressive style leads to turnovers. High-risk, high-reward approach.',
        'profile': 'High turnovers, aggressive play, risky'
    },

    'average_ball_security': {
        'name': 'Average Ball Security',
        'rules': {
            'turnover_rate': ('between', -0.3, 0.3),
        },
        'description': 'Average ball security. Moderate turnover tendencies.',
        'profile': 'Average turnovers, balanced approach'
    }
}

TURNOVERS_DEFENSIVE_ARCHETYPES = {
    'turnover_forcing_havoc': {
        'name': 'Turnover Forcing Havoc',
        'rules': {
            'opp_turnovers': ('>', 0.6),
            'opp_steals': ('>', 0.5),
        },
        'description': 'Creates chaos and forces turnovers. Aggressive, disruptive defensive pressure.',
        'allows': 'High pace, possessions',
        'suppresses': 'Clean possessions, ball security'
    },

    'pressure_defense': {
        'name': 'Pressure Defense',
        'rules': {
            'opp_turnovers': ('between', 0.0, 0.6),
            'opp_steals': ('between', 0.0, 0.5),
        },
        'description': 'Applies solid pressure that creates some turnovers. Active hands and good positioning.',
        'allows': 'Some possessions',
        'suppresses': 'Easy ball movement'
    },

    'passive_turnover_defense': {
        'name': 'Passive Turnover Defense',
        'rules': {
            'opp_turnovers': ('<', -0.5),
            'opp_steals': ('<', -0.4),
        },
        'description': 'Passive approach that doesn\'t force turnovers. Allows opponents to execute cleanly.',
        'allows': 'Clean possessions',
        'suppresses': 'Nothing specific'
    },

    'average_pressure': {
        'name': 'Average Pressure',
        'rules': {
            'opp_turnovers': ('between', -0.5, 0.0),
        },
        'description': 'Average defensive pressure. Moderate turnover forcing.',
        'allows': 'Average ball security',
        'suppresses': 'Nothing specific'
    }
}

TURNOVERS_OFFENSIVE_ORDER = ['ball_security_elite', 'solid_ball_handler', 'turnover_prone_aggressive', 'average_ball_security']
TURNOVERS_DEFENSIVE_ORDER = ['turnover_forcing_havoc', 'pressure_defense', 'passive_turnover_defense', 'average_pressure']

# ============================================================================
# FEATURE STANDARDIZATION
# ============================================================================

def standardize_features(all_team_features: Dict, feature_type: str) -> Dict:
    """
    Calculate z-scores for all features across all teams.

    Z-score = (value - mean) / std_dev

    Args:
        all_team_features: Dict of team_id -> features
        feature_type: 'offensive', 'defensive', 'assists_offensive', 'assists_defensive',
                     'rebounds_offensive', 'rebounds_defensive', 'threes_offensive',
                     'threes_defensive', 'turnovers_offensive', 'turnovers_defensive'

    Returns:
        Dict of team_id -> standardized_features
    """
    # Map feature type to feature names
    feature_name_map = {
        'offensive': OFFENSIVE_FEATURE_NAMES,
        'defensive': DEFENSIVE_FEATURE_NAMES,
        'assists_offensive': ASSISTS_FEATURE_NAMES,
        'assists_defensive': ASSISTS_DEFENSIVE_FEATURE_NAMES,
        'rebounds_offensive': REBOUNDS_FEATURE_NAMES,
        'rebounds_defensive': REBOUNDS_DEFENSIVE_FEATURE_NAMES,
        'threes_offensive': THREES_FEATURE_NAMES,
        'threes_defensive': THREES_DEFENSIVE_FEATURE_NAMES,
        'turnovers_offensive': TURNOVERS_FEATURE_NAMES,
        'turnovers_defensive': TURNOVERS_DEFENSIVE_FEATURE_NAMES
    }

    feature_names = feature_name_map.get(feature_type, OFFENSIVE_FEATURE_NAMES)

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
# NEW ARCHETYPE FAMILIES - CLASSIFICATION FUNCTIONS
# ============================================================================

def assign_assists_offensive_archetype(standardized_features: Dict) -> str:
    """Assign assists offensive archetype using rule matching."""
    for archetype_id in ASSISTS_OFFENSIVE_ORDER:
        archetype_def = ASSISTS_OFFENSIVE_ARCHETYPES[archetype_id]
        if _check_all_rules(standardized_features, archetype_def['rules']):
            logger.debug(f"Matched assists offensive archetype: {archetype_id}")
            return archetype_id
    return 'balanced_sharing'  # Fallback


def assign_assists_defensive_archetype(standardized_features: Dict) -> str:
    """Assign assists defensive archetype using rule matching."""
    for archetype_id in ASSISTS_DEFENSIVE_ORDER:
        archetype_def = ASSISTS_DEFENSIVE_ARCHETYPES[archetype_id]
        if _check_all_rules(standardized_features, archetype_def['rules']):
            logger.debug(f"Matched assists defensive archetype: {archetype_id}")
            return archetype_id
    return 'average_assist_defense'  # Fallback


def assign_rebounds_offensive_archetype(standardized_features: Dict) -> str:
    """Assign rebounds offensive archetype using rule matching."""
    for archetype_id in REBOUNDS_OFFENSIVE_ORDER:
        archetype_def = REBOUNDS_OFFENSIVE_ARCHETYPES[archetype_id]
        if _check_all_rules(standardized_features, archetype_def['rules']):
            logger.debug(f"Matched rebounds offensive archetype: {archetype_id}")
            return archetype_id
    return 'balanced_rebounding'  # Fallback


def assign_rebounds_defensive_archetype(standardized_features: Dict) -> str:
    """Assign rebounds defensive archetype using rule matching."""
    for archetype_id in REBOUNDS_DEFENSIVE_ORDER:
        archetype_def = REBOUNDS_DEFENSIVE_ARCHETYPES[archetype_id]
        if _check_all_rules(standardized_features, archetype_def['rules']):
            logger.debug(f"Matched rebounds defensive archetype: {archetype_id}")
            return archetype_id
    return 'average_rebounding'  # Fallback


def assign_threes_offensive_archetype(standardized_features: Dict) -> str:
    """Assign threes offensive archetype using rule matching."""
    for archetype_id in THREES_OFFENSIVE_ORDER:
        archetype_def = THREES_OFFENSIVE_ARCHETYPES[archetype_id]
        if _check_all_rules(standardized_features, archetype_def['rules']):
            logger.debug(f"Matched threes offensive archetype: {archetype_id}")
            return archetype_id
    return 'balanced_shooting'  # Fallback


def assign_threes_defensive_archetype(standardized_features: Dict) -> str:
    """Assign threes defensive archetype using rule matching."""
    for archetype_id in THREES_DEFENSIVE_ORDER:
        archetype_def = THREES_DEFENSIVE_ARCHETYPES[archetype_id]
        if _check_all_rules(standardized_features, archetype_def['rules']):
            logger.debug(f"Matched threes defensive archetype: {archetype_id}")
            return archetype_id
    return 'average_perimeter_defense'  # Fallback


def assign_turnovers_offensive_archetype(standardized_features: Dict) -> str:
    """Assign turnovers offensive archetype using rule matching."""
    for archetype_id in TURNOVERS_OFFENSIVE_ORDER:
        archetype_def = TURNOVERS_OFFENSIVE_ARCHETYPES[archetype_id]
        if _check_all_rules(standardized_features, archetype_def['rules']):
            logger.debug(f"Matched turnovers offensive archetype: {archetype_id}")
            return archetype_id
    return 'average_ball_security'  # Fallback


def assign_turnovers_defensive_archetype(standardized_features: Dict) -> str:
    """Assign turnovers defensive archetype using rule matching."""
    for archetype_id in TURNOVERS_DEFENSIVE_ORDER:
        archetype_def = TURNOVERS_DEFENSIVE_ARCHETYPES[archetype_id]
        if _check_all_rules(standardized_features, archetype_def['rules']):
            logger.debug(f"Matched turnovers defensive archetype: {archetype_id}")
            return archetype_id
    return 'average_pressure'  # Fallback


# ============================================================================
# PERCENTILE CALCULATION
# ============================================================================

def calculate_percentile(z_score: float) -> float:
    """
    Convert z-score to percentile (0-100) using scipy.

    Args:
        z_score: Standardized feature value

    Returns:
        Percentile value between 0 and 100

    Raises:
        RuntimeError: If scipy is not available (should never happen after startup check)
    """
    return round(norm.cdf(z_score) * 100, 1)


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
    Includes all 5 archetype families: scoring, assists, rebounds, threes, turnovers.

    Process:
    1. Calculate features for all teams (season + last 10)
    2. Standardize features separately for each window
    3. Assign archetypes using rules
    4. Calculate percentiles
    5. Detect style shifts

    Returns:
        {
            team_id: {
                # EXISTING scoring archetypes (backward compatible)
                'season_offensive': archetype_id,
                'season_defensive': archetype_id,
                'last10_offensive': archetype_id,
                'last10_defensive': archetype_id,
                'offensive_style_shift': bool,
                'defensive_style_shift': bool,
                'offensive_shift_details': str,
                'defensive_shift_details': str,

                # NEW archetype families
                'assists': {
                    'offensive': {
                        'season': {'id', 'name', 'description', 'profile', 'percentile', 'z_score'},
                        'last10': {...}
                    },
                    'defensive': {...},
                    'style_shifts': {...}
                },
                'rebounds': {...},
                'threes': {...},
                'turnovers': {...}
            }
        }
    """
    logger.info(f"Starting archetype assignment for season {season}")

    # Step 1: Calculate features for all teams
    all_features = calculate_all_team_features(season)

    # Step 2: Standardize features for SCORING archetypes (existing)
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

    # Step 2b: Standardize features for NEW archetype families
    # Assists
    season_assists_off_std = standardize_features(
        {tid: data['season'] for tid, data in all_features['assists_offensive'].items()},
        'assists_offensive'
    ) if 'assists_offensive' in all_features else {}
    last10_assists_off_std = standardize_features(
        {tid: data['last_10'] for tid, data in all_features['assists_offensive'].items()},
        'assists_offensive'
    ) if 'assists_offensive' in all_features else {}
    season_assists_def_std = standardize_features(
        {tid: data['season'] for tid, data in all_features['assists_defensive'].items()},
        'assists_defensive'
    ) if 'assists_defensive' in all_features else {}
    last10_assists_def_std = standardize_features(
        {tid: data['last_10'] for tid, data in all_features['assists_defensive'].items()},
        'assists_defensive'
    ) if 'assists_defensive' in all_features else {}

    # Rebounds
    season_rebounds_off_std = standardize_features(
        {tid: data['season'] for tid, data in all_features['rebounds_offensive'].items()},
        'rebounds_offensive'
    ) if 'rebounds_offensive' in all_features else {}
    last10_rebounds_off_std = standardize_features(
        {tid: data['last_10'] for tid, data in all_features['rebounds_offensive'].items()},
        'rebounds_offensive'
    ) if 'rebounds_offensive' in all_features else {}
    season_rebounds_def_std = standardize_features(
        {tid: data['season'] for tid, data in all_features['rebounds_defensive'].items()},
        'rebounds_defensive'
    ) if 'rebounds_defensive' in all_features else {}
    last10_rebounds_def_std = standardize_features(
        {tid: data['last_10'] for tid, data in all_features['rebounds_defensive'].items()},
        'rebounds_defensive'
    ) if 'rebounds_defensive' in all_features else {}

    # Threes
    season_threes_off_std = standardize_features(
        {tid: data['season'] for tid, data in all_features['threes_offensive'].items()},
        'threes_offensive'
    ) if 'threes_offensive' in all_features else {}
    last10_threes_off_std = standardize_features(
        {tid: data['last_10'] for tid, data in all_features['threes_offensive'].items()},
        'threes_offensive'
    ) if 'threes_offensive' in all_features else {}
    season_threes_def_std = standardize_features(
        {tid: data['season'] for tid, data in all_features['threes_defensive'].items()},
        'threes_defensive'
    ) if 'threes_defensive' in all_features else {}
    last10_threes_def_std = standardize_features(
        {tid: data['last_10'] for tid, data in all_features['threes_defensive'].items()},
        'threes_defensive'
    ) if 'threes_defensive' in all_features else {}

    # Turnovers
    season_turnovers_off_std = standardize_features(
        {tid: data['season'] for tid, data in all_features['turnovers_offensive'].items()},
        'turnovers_offensive'
    ) if 'turnovers_offensive' in all_features else {}
    last10_turnovers_off_std = standardize_features(
        {tid: data['last_10'] for tid, data in all_features['turnovers_offensive'].items()},
        'turnovers_offensive'
    ) if 'turnovers_offensive' in all_features else {}
    season_turnovers_def_std = standardize_features(
        {tid: data['season'] for tid, data in all_features['turnovers_defensive'].items()},
        'turnovers_defensive'
    ) if 'turnovers_defensive' in all_features else {}
    last10_turnovers_def_std = standardize_features(
        {tid: data['last_10'] for tid, data in all_features['turnovers_defensive'].items()},
        'turnovers_defensive'
    ) if 'turnovers_defensive' in all_features else {}

    # Step 3 & 4: Assign archetypes and calculate percentiles
    assignments = {}

    team_ids = set(all_features['offensive'].keys()) & set(all_features['defensive'].keys())

    for team_id in team_ids:
        # ===== SCORING ARCHETYPES (existing, backward compatible) =====
        season_off = assign_offensive_archetype(season_offensive_std[team_id])
        last10_off = assign_offensive_archetype(last10_offensive_std[team_id])
        off_shift, off_shift_details = detect_style_shift(season_off, last10_off, 'offensive')

        season_def = assign_defensive_archetype(season_defensive_std[team_id])
        last10_def = assign_defensive_archetype(last10_defensive_std[team_id])
        def_shift, def_shift_details = detect_style_shift(season_def, last10_def, 'defensive')

        # Calculate percentiles for scoring archetypes (use max z-score)
        season_off_percentile = calculate_percentile(max([abs(v) for v in season_offensive_std[team_id].values() if isinstance(v, (int, float))], default=0))
        last10_off_percentile = calculate_percentile(max([abs(v) for v in last10_offensive_std[team_id].values() if isinstance(v, (int, float))], default=0))
        season_def_percentile = calculate_percentile(max([abs(v) for v in season_defensive_std[team_id].values() if isinstance(v, (int, float))], default=0))
        last10_def_percentile = calculate_percentile(max([abs(v) for v in last10_defensive_std[team_id].values() if isinstance(v, (int, float))], default=0))

        assignments[team_id] = {
            # Backward compatible scoring archetype fields
            'season_offensive': season_off,
            'season_defensive': season_def,
            'last10_offensive': last10_off,
            'last10_defensive': last10_def,
            'offensive_style_shift': off_shift,
            'defensive_style_shift': def_shift,
            'offensive_shift_details': off_shift_details,
            'defensive_shift_details': def_shift_details,
            'season_offensive_percentile': season_off_percentile,
            'last10_offensive_percentile': last10_off_percentile,
            'season_defensive_percentile': season_def_percentile,
            'last10_defensive_percentile': last10_def_percentile,
        }

        # ===== ASSISTS ARCHETYPES =====
        if team_id in season_assists_off_std and team_id in last10_assists_off_std:
            season_assists_off_id = assign_assists_offensive_archetype(season_assists_off_std[team_id])
            last10_assists_off_id = assign_assists_offensive_archetype(last10_assists_off_std[team_id])
            season_assists_def_id = assign_assists_defensive_archetype(season_assists_def_std[team_id])
            last10_assists_def_id = assign_assists_defensive_archetype(last10_assists_def_std[team_id])

            assists_off_shift = season_assists_off_id != last10_assists_off_id
            assists_def_shift = season_assists_def_id != last10_assists_def_id

            assignments[team_id]['assists'] = {
                'offensive': {
                    'season': {
                        'id': season_assists_off_id,
                        'name': ASSISTS_OFFENSIVE_ARCHETYPES[season_assists_off_id]['name'],
                        'description': ASSISTS_OFFENSIVE_ARCHETYPES[season_assists_off_id]['description'],
                        'profile': ASSISTS_OFFENSIVE_ARCHETYPES[season_assists_off_id]['profile'],
                        'percentile': calculate_percentile(max([abs(v) for v in season_assists_off_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    },
                    'last10': {
                        'id': last10_assists_off_id,
                        'name': ASSISTS_OFFENSIVE_ARCHETYPES[last10_assists_off_id]['name'],
                        'description': ASSISTS_OFFENSIVE_ARCHETYPES[last10_assists_off_id]['description'],
                        'profile': ASSISTS_OFFENSIVE_ARCHETYPES[last10_assists_off_id]['profile'],
                        'percentile': calculate_percentile(max([abs(v) for v in last10_assists_off_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    }
                },
                'defensive': {
                    'season': {
                        'id': season_assists_def_id,
                        'name': ASSISTS_DEFENSIVE_ARCHETYPES[season_assists_def_id]['name'],
                        'description': ASSISTS_DEFENSIVE_ARCHETYPES[season_assists_def_id]['description'],
                        'allows': ASSISTS_DEFENSIVE_ARCHETYPES[season_assists_def_id].get('allows', ''),
                        'suppresses': ASSISTS_DEFENSIVE_ARCHETYPES[season_assists_def_id].get('suppresses', ''),
                        'percentile': calculate_percentile(max([abs(v) for v in season_assists_def_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    },
                    'last10': {
                        'id': last10_assists_def_id,
                        'name': ASSISTS_DEFENSIVE_ARCHETYPES[last10_assists_def_id]['name'],
                        'description': ASSISTS_DEFENSIVE_ARCHETYPES[last10_assists_def_id]['description'],
                        'allows': ASSISTS_DEFENSIVE_ARCHETYPES[last10_assists_def_id].get('allows', ''),
                        'suppresses': ASSISTS_DEFENSIVE_ARCHETYPES[last10_assists_def_id].get('suppresses', ''),
                        'percentile': calculate_percentile(max([abs(v) for v in last10_assists_def_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    }
                },
                'style_shifts': {
                    'offensive': assists_off_shift,
                    'defensive': assists_def_shift,
                    'offensive_details': f"STYLE SHIFT: {ASSISTS_OFFENSIVE_ARCHETYPES[season_assists_off_id]['name']} → {ASSISTS_OFFENSIVE_ARCHETYPES[last10_assists_off_id]['name']}" if assists_off_shift else '',
                    'defensive_details': f"STYLE SHIFT: {ASSISTS_DEFENSIVE_ARCHETYPES[season_assists_def_id]['name']} → {ASSISTS_DEFENSIVE_ARCHETYPES[last10_assists_def_id]['name']}" if assists_def_shift else ''
                }
            }

        # ===== REBOUNDS ARCHETYPES =====
        if team_id in season_rebounds_off_std and team_id in last10_rebounds_off_std:
            season_rebounds_off_id = assign_rebounds_offensive_archetype(season_rebounds_off_std[team_id])
            last10_rebounds_off_id = assign_rebounds_offensive_archetype(last10_rebounds_off_std[team_id])
            season_rebounds_def_id = assign_rebounds_defensive_archetype(season_rebounds_def_std[team_id])
            last10_rebounds_def_id = assign_rebounds_defensive_archetype(last10_rebounds_def_std[team_id])

            rebounds_off_shift = season_rebounds_off_id != last10_rebounds_off_id
            rebounds_def_shift = season_rebounds_def_id != last10_rebounds_def_id

            assignments[team_id]['rebounds'] = {
                'offensive': {
                    'season': {
                        'id': season_rebounds_off_id,
                        'name': REBOUNDS_OFFENSIVE_ARCHETYPES[season_rebounds_off_id]['name'],
                        'description': REBOUNDS_OFFENSIVE_ARCHETYPES[season_rebounds_off_id]['description'],
                        'profile': REBOUNDS_OFFENSIVE_ARCHETYPES[season_rebounds_off_id]['profile'],
                        'percentile': calculate_percentile(max([abs(v) for v in season_rebounds_off_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    },
                    'last10': {
                        'id': last10_rebounds_off_id,
                        'name': REBOUNDS_OFFENSIVE_ARCHETYPES[last10_rebounds_off_id]['name'],
                        'description': REBOUNDS_OFFENSIVE_ARCHETYPES[last10_rebounds_off_id]['description'],
                        'profile': REBOUNDS_OFFENSIVE_ARCHETYPES[last10_rebounds_off_id]['profile'],
                        'percentile': calculate_percentile(max([abs(v) for v in last10_rebounds_off_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    }
                },
                'defensive': {
                    'season': {
                        'id': season_rebounds_def_id,
                        'name': REBOUNDS_DEFENSIVE_ARCHETYPES[season_rebounds_def_id]['name'],
                        'description': REBOUNDS_DEFENSIVE_ARCHETYPES[season_rebounds_def_id]['description'],
                        'allows': REBOUNDS_DEFENSIVE_ARCHETYPES[season_rebounds_def_id].get('allows', ''),
                        'suppresses': REBOUNDS_DEFENSIVE_ARCHETYPES[season_rebounds_def_id].get('suppresses', ''),
                        'percentile': calculate_percentile(max([abs(v) for v in season_rebounds_def_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    },
                    'last10': {
                        'id': last10_rebounds_def_id,
                        'name': REBOUNDS_DEFENSIVE_ARCHETYPES[last10_rebounds_def_id]['name'],
                        'description': REBOUNDS_DEFENSIVE_ARCHETYPES[last10_rebounds_def_id]['description'],
                        'allows': REBOUNDS_DEFENSIVE_ARCHETYPES[last10_rebounds_def_id].get('allows', ''),
                        'suppresses': REBOUNDS_DEFENSIVE_ARCHETYPES[last10_rebounds_def_id].get('suppresses', ''),
                        'percentile': calculate_percentile(max([abs(v) for v in last10_rebounds_def_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    }
                },
                'style_shifts': {
                    'offensive': rebounds_off_shift,
                    'defensive': rebounds_def_shift,
                    'offensive_details': f"STYLE SHIFT: {REBOUNDS_OFFENSIVE_ARCHETYPES[season_rebounds_off_id]['name']} → {REBOUNDS_OFFENSIVE_ARCHETYPES[last10_rebounds_off_id]['name']}" if rebounds_off_shift else '',
                    'defensive_details': f"STYLE SHIFT: {REBOUNDS_DEFENSIVE_ARCHETYPES[season_rebounds_def_id]['name']} → {REBOUNDS_DEFENSIVE_ARCHETYPES[last10_rebounds_def_id]['name']}" if rebounds_def_shift else ''
                }
            }

        # ===== THREES ARCHETYPES =====
        if team_id in season_threes_off_std and team_id in last10_threes_off_std:
            season_threes_off_id = assign_threes_offensive_archetype(season_threes_off_std[team_id])
            last10_threes_off_id = assign_threes_offensive_archetype(last10_threes_off_std[team_id])
            season_threes_def_id = assign_threes_defensive_archetype(season_threes_def_std[team_id])
            last10_threes_def_id = assign_threes_defensive_archetype(last10_threes_def_std[team_id])

            threes_off_shift = season_threes_off_id != last10_threes_off_id
            threes_def_shift = season_threes_def_id != last10_threes_def_id

            assignments[team_id]['threes'] = {
                'offensive': {
                    'season': {
                        'id': season_threes_off_id,
                        'name': THREES_OFFENSIVE_ARCHETYPES[season_threes_off_id]['name'],
                        'description': THREES_OFFENSIVE_ARCHETYPES[season_threes_off_id]['description'],
                        'profile': THREES_OFFENSIVE_ARCHETYPES[season_threes_off_id]['profile'],
                        'percentile': calculate_percentile(max([abs(v) for v in season_threes_off_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    },
                    'last10': {
                        'id': last10_threes_off_id,
                        'name': THREES_OFFENSIVE_ARCHETYPES[last10_threes_off_id]['name'],
                        'description': THREES_OFFENSIVE_ARCHETYPES[last10_threes_off_id]['description'],
                        'profile': THREES_OFFENSIVE_ARCHETYPES[last10_threes_off_id]['profile'],
                        'percentile': calculate_percentile(max([abs(v) for v in last10_threes_off_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    }
                },
                'defensive': {
                    'season': {
                        'id': season_threes_def_id,
                        'name': THREES_DEFENSIVE_ARCHETYPES[season_threes_def_id]['name'],
                        'description': THREES_DEFENSIVE_ARCHETYPES[season_threes_def_id]['description'],
                        'allows': THREES_DEFENSIVE_ARCHETYPES[season_threes_def_id].get('allows', ''),
                        'suppresses': THREES_DEFENSIVE_ARCHETYPES[season_threes_def_id].get('suppresses', ''),
                        'percentile': calculate_percentile(max([abs(v) for v in season_threes_def_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    },
                    'last10': {
                        'id': last10_threes_def_id,
                        'name': THREES_DEFENSIVE_ARCHETYPES[last10_threes_def_id]['name'],
                        'description': THREES_DEFENSIVE_ARCHETYPES[last10_threes_def_id]['description'],
                        'allows': THREES_DEFENSIVE_ARCHETYPES[last10_threes_def_id].get('allows', ''),
                        'suppresses': THREES_DEFENSIVE_ARCHETYPES[last10_threes_def_id].get('suppresses', ''),
                        'percentile': calculate_percentile(max([abs(v) for v in last10_threes_def_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    }
                },
                'style_shifts': {
                    'offensive': threes_off_shift,
                    'defensive': threes_def_shift,
                    'offensive_details': f"STYLE SHIFT: {THREES_OFFENSIVE_ARCHETYPES[season_threes_off_id]['name']} → {THREES_OFFENSIVE_ARCHETYPES[last10_threes_off_id]['name']}" if threes_off_shift else '',
                    'defensive_details': f"STYLE SHIFT: {THREES_DEFENSIVE_ARCHETYPES[season_threes_def_id]['name']} → {THREES_DEFENSIVE_ARCHETYPES[last10_threes_def_id]['name']}" if threes_def_shift else ''
                }
            }

        # ===== TURNOVERS ARCHETYPES =====
        if team_id in season_turnovers_off_std and team_id in last10_turnovers_off_std:
            season_turnovers_off_id = assign_turnovers_offensive_archetype(season_turnovers_off_std[team_id])
            last10_turnovers_off_id = assign_turnovers_offensive_archetype(last10_turnovers_off_std[team_id])
            season_turnovers_def_id = assign_turnovers_defensive_archetype(season_turnovers_def_std[team_id])
            last10_turnovers_def_id = assign_turnovers_defensive_archetype(last10_turnovers_def_std[team_id])

            turnovers_off_shift = season_turnovers_off_id != last10_turnovers_off_id
            turnovers_def_shift = season_turnovers_def_id != last10_turnovers_def_id

            assignments[team_id]['turnovers'] = {
                'offensive': {
                    'season': {
                        'id': season_turnovers_off_id,
                        'name': TURNOVERS_OFFENSIVE_ARCHETYPES[season_turnovers_off_id]['name'],
                        'description': TURNOVERS_OFFENSIVE_ARCHETYPES[season_turnovers_off_id]['description'],
                        'profile': TURNOVERS_OFFENSIVE_ARCHETYPES[season_turnovers_off_id]['profile'],
                        'percentile': calculate_percentile(max([abs(v) for v in season_turnovers_off_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    },
                    'last10': {
                        'id': last10_turnovers_off_id,
                        'name': TURNOVERS_OFFENSIVE_ARCHETYPES[last10_turnovers_off_id]['name'],
                        'description': TURNOVERS_OFFENSIVE_ARCHETYPES[last10_turnovers_off_id]['description'],
                        'profile': TURNOVERS_OFFENSIVE_ARCHETYPES[last10_turnovers_off_id]['profile'],
                        'percentile': calculate_percentile(max([abs(v) for v in last10_turnovers_off_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    }
                },
                'defensive': {
                    'season': {
                        'id': season_turnovers_def_id,
                        'name': TURNOVERS_DEFENSIVE_ARCHETYPES[season_turnovers_def_id]['name'],
                        'description': TURNOVERS_DEFENSIVE_ARCHETYPES[season_turnovers_def_id]['description'],
                        'allows': TURNOVERS_DEFENSIVE_ARCHETYPES[season_turnovers_def_id].get('allows', ''),
                        'suppresses': TURNOVERS_DEFENSIVE_ARCHETYPES[season_turnovers_def_id].get('suppresses', ''),
                        'percentile': calculate_percentile(max([abs(v) for v in season_turnovers_def_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    },
                    'last10': {
                        'id': last10_turnovers_def_id,
                        'name': TURNOVERS_DEFENSIVE_ARCHETYPES[last10_turnovers_def_id]['name'],
                        'description': TURNOVERS_DEFENSIVE_ARCHETYPES[last10_turnovers_def_id]['description'],
                        'allows': TURNOVERS_DEFENSIVE_ARCHETYPES[last10_turnovers_def_id].get('allows', ''),
                        'suppresses': TURNOVERS_DEFENSIVE_ARCHETYPES[last10_turnovers_def_id].get('suppresses', ''),
                        'percentile': calculate_percentile(max([abs(v) for v in last10_turnovers_def_std[team_id].values() if isinstance(v, (int, float))], default=0))
                    }
                },
                'style_shifts': {
                    'offensive': turnovers_off_shift,
                    'defensive': turnovers_def_shift,
                    'offensive_details': f"STYLE SHIFT: {TURNOVERS_OFFENSIVE_ARCHETYPES[season_turnovers_off_id]['name']} → {TURNOVERS_OFFENSIVE_ARCHETYPES[last10_turnovers_off_id]['name']}" if turnovers_off_shift else '',
                    'defensive_details': f"STYLE SHIFT: {TURNOVERS_DEFENSIVE_ARCHETYPES[season_turnovers_def_id]['name']} → {TURNOVERS_DEFENSIVE_ARCHETYPES[last10_turnovers_def_id]['name']}" if turnovers_def_shift else ''
                }
            }

    logger.info(f"Archetype assignment complete for {len(assignments)} teams")
    return assignments
