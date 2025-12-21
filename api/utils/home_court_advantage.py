"""
Dynamic Home Court Advantage Calculator

Calculates home court advantage points (0-6 range) based on:
- Home team's home win percentage
- Away team's road win percentage
- Home team's recent home performance (last 3 games)
"""


def calculate_home_court_advantage(home_win_pct, road_win_pct, last3_home_wins):
    """
    Calculate dynamic home court advantage in points.

    Args:
        home_win_pct (float): Home team's win percentage at home (0.0 to 1.0)
        road_win_pct (float): Away team's win percentage on road (0.0 to 1.0)
        last3_home_wins (int): Number of wins in home team's last 3 home games (0-3)

    Returns:
        float: Home court advantage in points (clamped to 0-6 range)

    Formula:
        Base = 2.5
        Home_Record_Multiplier = (home_win_pct - 0.500) * 3
        Road_Weakness_Multiplier = (0.500 - road_win_pct) * 2
        Home_Momentum = 1.0 if last3_home_wins >= 2, -1.0 if == 0, else 0
        HCA = Base * (1 + Home_Record_Multiplier + Road_Weakness_Multiplier) + Home_Momentum
        Result clamped to [0, 6]
    """
    # Base home advantage
    base_home_advantage = 2.5

    # Factor 1: Home record strength
    home_record_multiplier = (home_win_pct - 0.500) * 3

    # Factor 2: Opponent road weakness
    road_weakness_multiplier = (0.500 - road_win_pct) * 2

    # Factor 3: Recent home performance momentum
    if last3_home_wins >= 2:
        home_momentum = 1.0
    elif last3_home_wins == 0:
        home_momentum = -1.0
    else:
        home_momentum = 0.0

    # Final calculation
    home_court_advantage = (
        base_home_advantage * (1 + home_record_multiplier + road_weakness_multiplier)
        + home_momentum
    )

    # Clamp result between 0 and 6
    home_court_advantage = max(0, min(6, home_court_advantage))

    return home_court_advantage
