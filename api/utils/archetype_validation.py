"""
Archetype Validation Module

Validates archetype assignments to ensure:
1. Reasonable distribution across archetypes
2. Archetypes correlate with expected statistical patterns
3. Style shifts are meaningful

Outputs diagnostic reports for tuning archetype rules if needed.
"""

from typing import Dict, List
from collections import Counter
import logging

logger = logging.getLogger(__name__)

try:
    from api.utils.archetype_classifier import OFFENSIVE_ARCHETYPES, DEFENSIVE_ARCHETYPES
    from api.utils.archetype_features import calculate_all_team_features
    from api.utils.db_queries import get_team_by_id
except ImportError:
    from archetype_classifier import OFFENSIVE_ARCHETYPES, DEFENSIVE_ARCHETYPES
    from archetype_features import calculate_all_team_features
    from db_queries import get_team_by_id


def validate_archetypes(assignments: Dict, season: str = '2025-26') -> Dict:
    """
    Validate archetype assignments.

    Checks:
    1. Distribution: Are teams reasonably distributed across archetypes?
    2. Correlation: Do offensive archetypes correlate with expected stats?
    3. Defensive correlation: Do defensive archetypes match opponent stats?
    4. Style shift frequency: How many teams show shifts?

    Args:
        assignments: Output from assign_all_team_archetypes()
        season: Season string

    Returns:
        {
            'offensive_distribution': {archetype_id: count, ...},
            'defensive_distribution': {archetype_id: count, ...},
            'total_teams': int,
            'offensive_style_shifts': int,
            'defensive_style_shifts': int,
            'correlations': {
                'offensive': {...},  # Feature correlations per archetype
                'defensive': {...}
            },
            'warnings': [str, ...],  # Low-sample or imbalanced clusters
            'sample_assignments': [...]  # 5 example teams with archetypes
        }
    """
    logger.info(f"Starting archetype validation for {len(assignments)} teams")

    # Distribution analysis
    season_offensive_counts = Counter()
    season_defensive_counts = Counter()
    last10_offensive_counts = Counter()
    last10_defensive_counts = Counter()

    offensive_shifts = 0
    defensive_shifts = 0

    for team_id, data in assignments.items():
        season_offensive_counts[data['season_offensive']] += 1
        season_defensive_counts[data['season_defensive']] += 1
        last10_offensive_counts[data['last10_offensive']] += 1
        last10_defensive_counts[data['last10_defensive']] += 1

        if data['offensive_style_shift']:
            offensive_shifts += 1
        if data['defensive_style_shift']:
            defensive_shifts += 1

    # Check for warnings
    warnings = []
    recommended_min = 2  # At least 2 teams per archetype recommended
    recommended_max = 15  # Max 15 teams per archetype for meaningful distinction

    for archetype_id, count in season_offensive_counts.items():
        archetype_name = OFFENSIVE_ARCHETYPES[archetype_id]['name']
        if count < recommended_min:
            warnings.append(f"Offensive archetype '{archetype_name}' only has {count} team(s) (below recommended {recommended_min})")
        elif count > recommended_max:
            warnings.append(f"Offensive archetype '{archetype_name}' has {count} teams (above recommended {recommended_max}, may be too broad)")

    for archetype_id, count in season_defensive_counts.items():
        archetype_name = DEFENSIVE_ARCHETYPES[archetype_id]['name']
        if count < recommended_min:
            warnings.append(f"Defensive archetype '{archetype_name}' only has {count} team(s) (below recommended {recommended_min})")
        elif count > recommended_max:
            warnings.append(f"Defensive archetype '{archetype_name}' has {count} teams (above recommended {recommended_max}, may be too broad)")

    # Correlation check
    all_features = calculate_all_team_features(season)

    offensive_correlations = {}
    for archetype_id in OFFENSIVE_ARCHETYPES.keys():
        teams_in_archetype = [
            tid for tid, data in assignments.items()
            if data['season_offensive'] == archetype_id
        ]
        if teams_in_archetype:
            offensive_correlations[archetype_id] = correlation_check(
                archetype_id, teams_in_archetype, 'offensive', all_features
            )

    defensive_correlations = {}
    for archetype_id in DEFENSIVE_ARCHETYPES.keys():
        teams_in_archetype = [
            tid for tid, data in assignments.items()
            if data['season_defensive'] == archetype_id
        ]
        if teams_in_archetype:
            defensive_correlations[archetype_id] = correlation_check(
                archetype_id, teams_in_archetype, 'defensive', all_features
            )

    # Sample assignments (first 5 teams)
    sample_assignments = []
    for i, (team_id, data) in enumerate(assignments.items()):
        if i >= 5:
            break
        team_info = get_team_by_id(team_id)
        abbr = team_info['abbreviation'] if team_info else str(team_id)
        sample_assignments.append({
            'team': abbr,
            'off_season': OFFENSIVE_ARCHETYPES[data['season_offensive']]['name'],
            'def_season': DEFENSIVE_ARCHETYPES[data['season_defensive']]['name'],
            'off_last10': OFFENSIVE_ARCHETYPES[data['last10_offensive']]['name'],
            'def_last10': DEFENSIVE_ARCHETYPES[data['last10_defensive']]['name'],
            'off_shift': data['offensive_style_shift'],
            'def_shift': data['defensive_style_shift']
        })

    result = {
        'offensive_distribution': dict(season_offensive_counts),
        'defensive_distribution': dict(season_defensive_counts),
        'last10_offensive_distribution': dict(last10_offensive_counts),
        'last10_defensive_distribution': dict(last10_defensive_counts),
        'total_teams': len(assignments),
        'offensive_style_shifts': offensive_shifts,
        'defensive_style_shifts': defensive_shifts,
        'correlations': {
            'offensive': offensive_correlations,
            'defensive': defensive_correlations
        },
        'warnings': warnings,
        'sample_assignments': sample_assignments
    }

    logger.info(f"Validation complete: {len(warnings)} warnings, {offensive_shifts} offensive shifts, {defensive_shifts} defensive shifts")
    return result


def correlation_check(archetype_id: str, teams_in_archetype: List[int],
                     archetype_type: str, all_features: Dict) -> Dict:
    """
    Check if teams in archetype actually exhibit defining features.

    For example, 'foul_pressure_paint_attack' should have:
    - High ft_rate on average
    - High pitp_share
    - Low three_pa_rate

    Args:
        archetype_id: Archetype ID
        teams_in_archetype: List of team IDs in this archetype
        archetype_type: 'offensive' or 'defensive'
        all_features: Output from calculate_all_team_features()

    Returns:
        Dict with average feature values for teams in this archetype
    """
    if archetype_type == 'offensive':
        archetype_def = OFFENSIVE_ARCHETYPES[archetype_id]
        feature_data = all_features['offensive']
    else:
        archetype_def = DEFENSIVE_ARCHETYPES[archetype_id]
        feature_data = all_features['defensive']

    # Get defining features from rules
    defining_features = list(archetype_def['rules'].keys())

    # Calculate average values for defining features
    feature_sums = {feature: 0.0 for feature in defining_features}
    count = len(teams_in_archetype)

    for team_id in teams_in_archetype:
        if team_id in feature_data:
            season_features = feature_data[team_id]['season']
            for feature in defining_features:
                feature_sums[feature] += season_features.get(feature, 0.0)

    averages = {feature: feature_sums[feature] / count if count > 0 else 0.0
                for feature in defining_features}

    logger.debug(f"Correlation check for {archetype_id}: {averages}")

    return {
        'archetype_name': archetype_def['name'],
        'team_count': count,
        'average_features': averages,
        'defining_features': defining_features
    }


def print_validation_report(validation_result: Dict):
    """
    Print human-readable validation report.

    Args:
        validation_result: Output from validate_archetypes()
    """
    print("\n" + "=" * 80)
    print("ARCHETYPE VALIDATION REPORT")
    print("=" * 80)

    print(f"\nTotal Teams: {validation_result['total_teams']}")
    print(f"Offensive Style Shifts: {validation_result['offensive_style_shifts']}")
    print(f"Defensive Style Shifts: {validation_result['defensive_style_shifts']}")

    print("\n" + "-" * 80)
    print("OFFENSIVE ARCHETYPE DISTRIBUTION (SEASON)")
    print("-" * 80)
    for archetype_id, count in sorted(
        validation_result['offensive_distribution'].items(),
        key=lambda x: x[1],
        reverse=True
    ):
        name = OFFENSIVE_ARCHETYPES[archetype_id]['name']
        pct = (count / validation_result['total_teams']) * 100
        print(f"  {name:40} {count:2} teams ({pct:5.1f}%)")

    print("\n" + "-" * 80)
    print("DEFENSIVE ARCHETYPE DISTRIBUTION (SEASON)")
    print("-" * 80)
    for archetype_id, count in sorted(
        validation_result['defensive_distribution'].items(),
        key=lambda x: x[1],
        reverse=True
    ):
        name = DEFENSIVE_ARCHETYPES[archetype_id]['name']
        pct = (count / validation_result['total_teams']) * 100
        print(f"  {name:40} {count:2} teams ({pct:5.1f}%)")

    if validation_result['warnings']:
        print("\n" + "-" * 80)
        print("WARNINGS")
        print("-" * 80)
        for warning in validation_result['warnings']:
            print(f"  ⚠️  {warning}")

    print("\n" + "-" * 80)
    print("SAMPLE TEAM ASSIGNMENTS")
    print("-" * 80)
    for sample in validation_result['sample_assignments']:
        print(f"\n  {sample['team']}:")
        print(f"    Offensive: {sample['off_season']}")
        if sample['off_shift']:
            print(f"      → Last 10: {sample['off_last10']} (SHIFTED)")
        print(f"    Defensive: {sample['def_season']}")
        if sample['def_shift']:
            print(f"      → Last 10: {sample['def_last10']} (SHIFTED)")

    print("\n" + "=" * 80 + "\n")
