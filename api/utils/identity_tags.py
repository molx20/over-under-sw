"""
Identity Tags Module

Generates descriptive tags for teams based on defense-adjusted scoring splits.
Tags highlight interesting scoring patterns vs different defense tiers and locations.

Seven tag types are supported:
1. Home Giant Killers - Scores well at home vs elite defenses
2. Home Flat-Track Bullies - Scores much better at home vs bad defenses than elite
3. Road Warriors vs Good Defense - Scores well on road vs elite defenses
4. Road Shrinkers vs Good Defense - Struggles on road vs elite defenses
5. Home Scoring Suppressed vs Bad Defense - Counterintuitive pattern
6. Consistent Scorer - All splits stay within narrow band
7. High-Variance Scoring Identity - Large spread between splits

All thresholds are configurable.
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Default thresholds (user-confirmed preferences)
TAG_THRESHOLDS = {
    'significant_diff': 4.0,      # Points above/below season avg for significance
    'moderate_diff': 3.0,          # Points for tier-to-tier comparisons
    'consistency_band': 3.0,       # Max deviation for "Consistent Scorer"
    'high_variance_spread': 8.0,   # Spread for "High-Variance"
    'min_games_required': 3        # Minimum games per bucket for tag generation
}


def generate_identity_tags(
    splits_data: Dict,
    thresholds: Optional[Dict] = None
) -> List[str]:
    """
    Generate identity tags based on team's scoring splits.

    Tags describe distinctive scoring patterns vs different defense tiers
    and locations. Multiple tags can apply to the same team.

    Args:
        splits_data: Output from scoring_splits.get_team_scoring_splits()
        thresholds: Optional custom threshold configuration (uses defaults if None)

    Returns:
        List of tag strings (e.g., ["Home Giant Killers", "Road Warriors vs Good Defense"])
        Returns empty list if insufficient data or no patterns detected

    Example:
        >>> splits = get_team_scoring_splits(1610612738, '2025-26')
        >>> tags = generate_identity_tags(splits)
        >>> print(tags)
        ['Home Flat-Track Bullies', 'Road Shrinkers vs Good Defense']
    """
    if not splits_data or 'splits' not in splits_data or 'season_avg_ppg' not in splits_data:
        logger.warning("Invalid splits_data provided to generate_identity_tags")
        return []

    # Use default thresholds if not provided
    config = thresholds if thresholds else TAG_THRESHOLDS

    season_avg = splits_data['season_avg_ppg']
    if season_avg is None:
        logger.warning("No season average PPG available for tag generation")
        return []

    splits = splits_data['splits']
    tags = []

    # Extract values from splits for easier access
    elite = splits.get('elite', {})
    average = splits.get('average', {})
    bad = splits.get('bad', {})

    home_vs_elite_ppg = elite.get('home_ppg')
    home_vs_elite_games = elite.get('home_games', 0)
    away_vs_elite_ppg = elite.get('away_ppg')
    away_vs_elite_games = elite.get('away_games', 0)

    home_vs_avg_ppg = average.get('home_ppg')
    home_vs_avg_games = average.get('home_games', 0)
    away_vs_avg_ppg = average.get('away_ppg')
    away_vs_avg_games = average.get('away_games', 0)

    home_vs_bad_ppg = bad.get('home_ppg')
    home_vs_bad_games = bad.get('home_games', 0)
    away_vs_bad_ppg = bad.get('away_ppg')
    away_vs_bad_games = bad.get('away_games', 0)

    min_games = config['min_games_required']
    significant_diff = config['significant_diff']
    moderate_diff = config['moderate_diff']

    # Tag 1: Home Giant Killers
    # Scores significantly MORE at home vs elite defenses than season average
    if home_vs_elite_ppg is not None and home_vs_elite_games >= min_games:
        if home_vs_elite_ppg > season_avg + significant_diff:
            tags.append("Home Giant Killers")
            logger.debug(f"Tag: Home Giant Killers ({home_vs_elite_ppg} vs {season_avg} season avg)")

    # Tag 2: Home Flat-Track Bullies
    # Scores significantly MORE at home vs bad defenses than vs elite defenses
    if (home_vs_bad_ppg is not None and home_vs_elite_ppg is not None and
        home_vs_bad_games >= min_games and home_vs_elite_games >= min_games):
        if home_vs_bad_ppg > home_vs_elite_ppg + moderate_diff:
            tags.append("Home Flat-Track Bullies")
            logger.debug(f"Tag: Home Flat-Track Bullies ({home_vs_bad_ppg} vs bad, {home_vs_elite_ppg} vs elite)")

    # Tag 3: Road Warriors vs Good Defense
    # Scores significantly MORE on road vs elite defenses than season average
    if away_vs_elite_ppg is not None and away_vs_elite_games >= min_games:
        if away_vs_elite_ppg > season_avg + significant_diff:
            tags.append("Road Warriors vs Good Defense")
            logger.debug(f"Tag: Road Warriors ({away_vs_elite_ppg} on road vs {season_avg} season avg)")

    # Tag 4: Road Shrinkers vs Good Defense
    # Scores significantly LESS on road vs elite defenses than season average
    if away_vs_elite_ppg is not None and away_vs_elite_games >= min_games:
        if away_vs_elite_ppg < season_avg - significant_diff:
            tags.append("Road Shrinkers vs Good Defense")
            logger.debug(f"Tag: Road Shrinkers ({away_vs_elite_ppg} on road vs {season_avg} season avg)")

    # Tag 5: Home Scoring Suppressed vs Bad Defense
    # Counterintuitive: Scores LESS at home vs bad defenses than season average
    if home_vs_bad_ppg is not None and home_vs_bad_games >= min_games:
        if home_vs_bad_ppg < season_avg - significant_diff:
            tags.append("Home Scoring Suppressed vs Bad Defense")
            logger.debug(f"Tag: Suppressed vs Bad Defense ({home_vs_bad_ppg} vs {season_avg} season avg)")

    # Collect all valid PPG values for variance analysis
    all_valid_ppgs = []
    all_buckets = [
        (home_vs_elite_ppg, home_vs_elite_games),
        (home_vs_avg_ppg, home_vs_avg_games),
        (home_vs_bad_ppg, home_vs_bad_games),
        (away_vs_elite_ppg, away_vs_elite_games),
        (away_vs_avg_ppg, away_vs_avg_games),
        (away_vs_bad_ppg, away_vs_bad_games)
    ]

    for ppg, games in all_buckets:
        if ppg is not None and games >= min_games:
            all_valid_ppgs.append(ppg)

    # Tag 6: Consistent Scorer
    # All valid splits stay within narrow band (only if no other tags already applied)
    if len(all_valid_ppgs) >= 4:
        max_ppg = max(all_valid_ppgs)
        min_ppg = min(all_valid_ppgs)
        ppg_range = max_ppg - min_ppg

        if ppg_range <= config['consistency_band']:
            # Only add if no other specific tags already matched
            if len(tags) == 0:
                tags.append("Consistent Scorer")
                logger.debug(f"Tag: Consistent Scorer (range: {ppg_range:.1f})")

    # Tag 7: High-Variance Scoring Identity
    # Large spread between highest and lowest splits
    if len(all_valid_ppgs) >= 4:
        max_ppg = max(all_valid_ppgs)
        min_ppg = min(all_valid_ppgs)
        ppg_range = max_ppg - min_ppg

        if ppg_range >= config['high_variance_spread']:
            tags.append("High-Variance Scoring Identity")
            logger.debug(f"Tag: High-Variance ({ppg_range:.1f} pt spread)")

    logger.info(f"Generated {len(tags)} identity tags: {tags}")
    return tags


def get_tag_explanation(tag: str) -> str:
    """
    Get human-readable explanation for a tag.

    Args:
        tag: Tag name

    Returns:
        Explanation string describing what the tag means
    """
    explanations = {
        "Home Giant Killers": "This team scores significantly more at home against elite defenses (top 10) compared to their season average, showing they rise to the challenge of tough opponents at home.",

        "Home Flat-Track Bullies": "This team scores much better at home against weaker defenses (bottom 10) than against elite defenses, suggesting they capitalize on favorable matchups at home.",

        "Road Warriors vs Good Defense": "This team performs exceptionally well on the road against elite defenses, scoring above their season average even in hostile environments against top defenders.",

        "Road Shrinkers vs Good Defense": "This team struggles significantly on the road against elite defenses, scoring well below their season average when facing both a tough opponent and a hostile crowd.",

        "Home Scoring Suppressed vs Bad Defense": "Counterintuitively, this team scores less at home against bad defenses than their season average, which may indicate motivational issues or stylistic mismatches.",

        "Consistent Scorer": "This team shows very little variation in scoring across different defense tiers and locations, maintaining steady output regardless of opponent quality or venue.",

        "High-Variance Scoring Identity": "This team has large swings in scoring output depending on opponent defense quality and location, making their performance more unpredictable."
    }

    return explanations.get(tag, "No explanation available for this tag.")


def get_tag_color_suggestion(tag: str) -> str:
    """
    Get recommended color coding for UI display.

    Args:
        tag: Tag name

    Returns:
        Color category: 'positive', 'negative', 'neutral', 'informational'
    """
    color_map = {
        "Home Giant Killers": "positive",
        "Home Flat-Track Bullies": "neutral",
        "Road Warriors vs Good Defense": "positive",
        "Road Shrinkers vs Good Defense": "negative",
        "Home Scoring Suppressed vs Bad Defense": "negative",
        "Consistent Scorer": "neutral",
        "High-Variance Scoring Identity": "informational"
    }

    return color_map.get(tag, "neutral")
