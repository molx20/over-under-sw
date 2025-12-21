"""
True Pace and Volume-Based Scoring Adjustments

This module implements possession-based pace calculation and volume adjustments
to better predict game totals based on actual shot volume, free throws, rebounds, and turnovers.
"""

# League average possessions per 48 minutes
LEAGUE_AVG_PACE = 100.0

# Top offensive identity teams (high FGA + 3PA volume)
# Boston Celtics, Indiana Pacers, Houston Rockets
TOP_OFFENSIVE_IDENTITY_TEAMS = [
    1610612738,  # Boston Celtics
    1610612754,  # Indiana Pacers
    1610612745,  # Houston Rockets
]


def calculate_true_pace(team_stats):
    """
    Calculate true possessions for a team using the formula:
    possessions = FGA + (0.44 * FTA) + TO - ORB

    Args:
        team_stats: Dict with FGA, FTA, TOV, OREB keys

    Returns:
        float: Estimated possessions per game
    """
    fga = team_stats.get('FGA', 85.0)
    fta = team_stats.get('FTA', 20.0)
    tov = team_stats.get('TOV', 14.0)
    oreb = team_stats.get('OREB', 10.0)

    possessions = fga + (0.44 * fta) + tov - oreb

    return possessions


def calculate_pace_multiplier(home_possessions, away_possessions):
    """
    Calculate game pace multiplier based on combined team possessions.

    Args:
        home_possessions: Home team's possessions per game
        away_possessions: Away team's possessions per game

    Returns:
        float: Pace multiplier relative to league average
    """
    game_pace = (home_possessions + away_possessions) / 2.0
    pace_multiplier = game_pace / LEAGUE_AVG_PACE

    return pace_multiplier, game_pace


def apply_muted_pace_effect(base_offense, pace_multiplier):
    """
    Apply a VERY LIGHT pace effect to base offense.

    Formula: offense_after_pace = baseOffense * (0.92 + 0.08 * paceMultiplier)

    This caps realistic impact to about ±5% of scoring (was ±15% before tuning).
    Even slower adjustments reduce the tendency to over-predict fast-paced games.

    Args:
        base_offense: Base offensive points before pace adjustment
        pace_multiplier: Pace multiplier from calculate_pace_multiplier

    Returns:
        float: Adjusted offense after very light pace effect
    """
    adjusted = base_offense * (0.92 + 0.08 * pace_multiplier)
    return adjusted


def calculate_shot_volume_boost(team_stats):
    """
    Calculate bonus/penalty based on shot volume.

    shotVolume = FGA + (3PA * 0.5) + ORB

    TUNED Rules (smaller bonuses, higher thresholds):
    - If shotVolume > 100:  +4 points
    - Else if shotVolume > 95:  +2 points
    - Else if shotVolume < 75:  -4 points
    - Else if shotVolume < 80:  -2 points
    - Else: 0

    Args:
        team_stats: Dict with FGA, FG3A, OREB keys

    Returns:
        float: Shot volume adjustment
    """
    fga = team_stats.get('FGA', 85.0)
    fg3a = team_stats.get('FG3A', 30.0)
    oreb = team_stats.get('OREB', 10.0)

    shot_volume = fga + (fg3a * 0.5) + oreb

    if shot_volume > 100:
        return 4.0
    elif shot_volume > 95:
        return 2.0
    elif shot_volume < 75:
        return -4.0
    elif shot_volume < 80:
        return -2.0
    else:
        return 0.0


def calculate_free_throw_boost(team_stats):
    """
    Calculate bonus based on free throw attempts.

    TUNED Rules (smaller bonuses for whistle-heavy games):
    - If FTA > 40 → +3 points
    - Else if FTA > 30 → +1 point
    - Else: 0

    Note: Free throws add points but also slow the game. We only apply
    small positive bonuses in whistle-heavy games.

    Args:
        team_stats: Dict with FTA key

    Returns:
        float: Free throw bonus
    """
    fta = team_stats.get('FTA', 20.0)

    if fta > 40:
        return 3.0
    elif fta > 30:
        return 1.0
    else:
        return 0.0


def calculate_offensive_rebound_bonus(team_stats):
    """
    Calculate bonus based on offensive rebounds.

    TUNED Rules (smaller bonuses to avoid double-counting with possessions):
    - If ORB >= 16 → +2 points
    - Else if ORB >= 12 → +1 point
    - Else: 0

    Note: ORB is already counted in the possessions formula, so this bonus
    must be small to avoid inflating totals.

    Args:
        team_stats: Dict with OREB key

    Returns:
        float: Offensive rebound bonus
    """
    oreb = team_stats.get('OREB', 10.0)

    if oreb >= 16:
        return 2.0
    elif oreb >= 12:
        return 1.0
    else:
        return 0.0


def calculate_turnover_pace_bonus(home_stats, away_stats):
    """
    REMOVED: Turnover pace bonus.

    Turnovers are already accounted for in the possessions formula:
    possessions = FGA + (0.44 * FTA) + TO - ORB

    Adding a separate turnover bonus was double-counting the pace impact.
    This function now always returns 0.

    Args:
        home_stats: Dict with TOV key
        away_stats: Dict with TOV key

    Returns:
        float: Always 0.0 (turnovers handled in possessions/pace)
    """
    # Turnovers are already in the possessions formula - no additional bonus needed
    return 0.0


def calculate_offensive_identity_boost(team_id, team_stats):
    """
    Small boost for teams in top 5 for BOTH FGA and 3PA.

    TUNED: Reduced from +6 to +2 to avoid over-predicting high-volume teams.

    Args:
        team_id: NBA team ID
        team_stats: Dict with FGA and FG3A keys

    Returns:
        float: High-volume shooter identity bonus (+2 for top teams, 0 otherwise)
    """
    # Check if team is in our hard-coded list
    if team_id in TOP_OFFENSIVE_IDENTITY_TEAMS:
        # Verify they actually have high volume
        fga = team_stats.get('FGA', 85.0)
        fg3a = team_stats.get('FG3A', 30.0)

        # Top 5 in league is roughly FGA > 90 and 3PA > 38
        if fga > 88 and fg3a > 36:
            return 2.0

    return 0.0


def calculate_conditional_home_road_adjustment(home_stats, away_stats):
    """
    Calculate conditional home/road adjustment ONLY when meaningful.

    Remove baseline home/road boosts.

    Rules:
    - If (homePPG_at_home - homePPG_on_road >= 4): homeBoost = +2
    - If (awayPPG_on_road - awayPPG_at_home >= 4): roadPenalty = -2
    - Else: no change

    Args:
        home_stats: Dict with home/away split PTS
        away_stats: Dict with home/away split PTS

    Returns:
        tuple: (home_adjustment, away_adjustment, explanation)
    """
    # Get home/away splits
    home_pts_home = home_stats.get('home', {}).get('PTS', 0)
    home_pts_away = home_stats.get('away', {}).get('PTS', 0)

    away_pts_home = away_stats.get('home', {}).get('PTS', 0)
    away_pts_road = away_stats.get('away', {}).get('PTS', 0)

    home_adjustment = 0.0
    away_adjustment = 0.0
    explanation = "No significant home/road split pattern"

    # Check home team's home advantage
    if home_pts_home > 0 and home_pts_away > 0:
        if (home_pts_home - home_pts_away) >= 4:
            home_adjustment = 2.0
            explanation = f"Home team scores {home_pts_home - home_pts_away:.1f} more points at home"

    # Check away team's road penalty
    if away_pts_road > 0 and away_pts_home > 0:
        if (away_pts_home - away_pts_road) >= 4:
            away_adjustment = -2.0
            if explanation != "No significant home/road split pattern":
                explanation += f"; Away team scores {away_pts_home - away_pts_road:.1f} fewer on road"
            else:
                explanation = f"Away team scores {away_pts_home - away_pts_road:.1f} fewer on road"

    return home_adjustment, away_adjustment, explanation
