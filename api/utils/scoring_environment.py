"""
Scoring Environment Classifier

Deterministic business rules to classify games as HIGH, GRAY ZONE, or LOW
scoring environments based on pace and offensive ratings.

NOT AI-driven. Uses fixed thresholds only.
"""


def calculate_scoring_environment(home_pace: float, away_pace: float,
                                   home_ortg: float, away_ortg: float,
                                   home_3p_pct: float = None, away_3p_pct: float = None) -> str:
    """
    Classify the scoring environment for a matchup.

    Args:
        home_pace: Home team pace (possessions per 48 min)
        away_pace: Away team pace
        home_ortg: Home team offensive rating (points per 100 possessions)
        away_ortg: Away team offensive rating
        home_3p_pct: Home team 3-point percentage (optional, 0-100 scale or 0-1 scale)
        away_3p_pct: Away team 3-point percentage (optional, 0-100 scale or 0-1 scale)

    Returns:
        One of: "HIGH", "GRAY ZONE", "LOW"

    Business Rules (ORDER MATTERS):
        1. HIGH: combined_pace >= 108 AND combined_ortg >= 110
        2. LOW: combined_pace <= 100 AND (combined_ortg <= 106 OR combined_3p_pct <= 33)
        3. GRAY ZONE: Everything else
    """
    # Step 1: Compute combined metrics
    combined_pace = (home_pace + away_pace) / 2
    combined_ortg = (home_ortg + away_ortg) / 2

    # Handle 3-point percentage (normalize to 0-100 scale if needed)
    combined_3p_pct = None
    if home_3p_pct is not None and away_3p_pct is not None:
        # Convert to percentage if given as decimal (0-1 range)
        h_pct = home_3p_pct * 100 if home_3p_pct <= 1 else home_3p_pct
        a_pct = away_3p_pct * 100 if away_3p_pct <= 1 else away_3p_pct
        combined_3p_pct = (h_pct + a_pct) / 2

    # Step 2: Apply classification rules (ORDER MATTERS)
    import logging
    logger = logging.getLogger(__name__)

    # Rule 1: HIGH
    if combined_pace >= 108 and combined_ortg >= 110:
        logger.info(f"[scoring_env] HIGH: pace={combined_pace:.1f}, ortg={combined_ortg:.1f}")
        return "HIGH"

    # Rule 2: LOW
    if combined_pace <= 100:
        if combined_ortg <= 106:
            logger.info(f"[scoring_env] LOW (slow+weak): pace={combined_pace:.1f}, ortg={combined_ortg:.1f}")
            return "LOW"
        if combined_3p_pct is not None and combined_3p_pct <= 33:
            logger.info(f"[scoring_env] LOW (slow+cold): pace={combined_pace:.1f}, 3p%={combined_3p_pct:.1f}")
            return "LOW"

    # Rule 3: GRAY ZONE (default)
    logger.info(f"[scoring_env] GRAY ZONE: pace={combined_pace:.1f}, ortg={combined_ortg:.1f}")
    return "GRAY ZONE"


def get_scoring_environment_details(scoring_environment: str) -> dict:
    """
    Get display properties for a scoring environment.

    Args:
        scoring_environment: One of "HIGH", "GRAY ZONE", "LOW"

    Returns:
        Dict with display properties (color, icon, etc.)
    """
    if scoring_environment == "HIGH":
        return {
            "label": "HIGH",
            "color": "green",
            "bg_color": "bg-green-50 dark:bg-green-900/20",
            "text_color": "text-green-700 dark:text-green-400",
            "border_color": "border-green-200 dark:border-green-800"
        }
    elif scoring_environment == "LOW":
        return {
            "label": "LOW",
            "color": "red",
            "bg_color": "bg-red-50 dark:bg-red-900/20",
            "text_color": "text-red-700 dark:text-red-400",
            "border_color": "border-red-200 dark:border-red-800"
        }
    else:  # GRAY ZONE
        return {
            "label": "GRAY ZONE",
            "color": "gray",
            "bg_color": "bg-gray-50 dark:bg-gray-800/50",
            "text_color": "text-gray-700 dark:text-gray-400",
            "border_color": "border-gray-200 dark:border-gray-700"
        }
