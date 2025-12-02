"""
Profile Explanation Module

Generates 5th-grade reading level explanations of team prediction profiles.
All explanations are deterministic based on profile data.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def explain_team_prediction(team_id: int, season: str = '2025-26') -> str:
    """
    Generate 5th-grade reading level explanation of team's prediction profile.

    Args:
        team_id: Team's NBA ID
        season: Season string

    Returns:
        1-3 sentence explanation like:
        "They play fast and their scores swing a lot from game to game,
         so we lean more on how they played in their last few games."
    """
    try:
        from api.utils.db_queries import get_team_profile

        profile = get_team_profile(team_id, season)
        if not profile:
            return "We're using standard predictions for this team."

        parts = []

        # Pace + Variance context
        pace_label = profile['pace_label']
        variance_label = profile['variance_label']

        if pace_label == 'fast' and variance_label == 'high':
            parts.append("They play fast and their scores swing a lot from game to game")
        elif pace_label == 'slow' and variance_label == 'low':
            parts.append("They play at a slow pace and their scoring is pretty steady each night")
        elif pace_label == 'fast':
            parts.append("They play at a fast pace")
        elif pace_label == 'slow':
            parts.append("They play at a slow pace")
        elif variance_label == 'high':
            parts.append("Their scores change a lot from game to game")
        elif variance_label == 'low':
            parts.append("They score about the same amount most nights")

        # Season vs Recent weights (even though not actively used in hybrid, still informative)
        season_weight = profile['season_weight']
        recent_weight = profile['recent_weight']

        if recent_weight > season_weight + 0.05:
            if parts:
                # Connect with previous part using lowercase
                parts[-1] = parts[-1] + ", so we lean more on how they played in their last few games"
            else:
                parts.append("We lean more on how they played in their last few games")
        elif season_weight > recent_weight + 0.05:
            if parts:
                # Connect with previous part using lowercase
                parts[-1] = parts[-1] + ", so we trust their full season numbers more than just their last few games"
            else:
                parts.append("We trust their full season numbers more")

        # Pace weight (actively used in hybrid)
        pace_weight = profile['pace_weight']
        if pace_weight > 1.05:
            parts.append("We also give extra weight to the pace of this game")
        elif pace_weight < 0.95:
            parts.append("The pace of this game matters less for them")

        # Defense weight (actively used in hybrid)
        def_weight = profile['def_weight']
        if def_weight > 1.05:
            parts.append("The other team's defense matters more than usual for this matchup")
        elif def_weight < 0.95:
            parts.append("The other team's defense matters less for them")

        # Home/away weight
        home_away_label = profile['home_away_label']
        if home_away_label == 'home_strong':
            parts.append("They're especially strong at home")
        elif home_away_label == 'road_strong':
            parts.append("They actually play better on the road")

        # Combine parts into sentences
        if not parts:
            return "We're using standard predictions for this team."

        return '. '.join(parts) + '.'

    except Exception as e:
        logger.error(f"Error generating explanation for team {team_id}: {e}")
        return "We're using standard predictions for this team."
