"""Simple test of B2B functionality"""
from api.utils.back_to_back_profiles import (
    get_back_to_back_profile,
    is_team_on_back_to_back,
    print_team_b2b_summary
)

# Test game 0022500338 where both teams are on B2B
game_id = '0022500338'
home_team_id = 1610612738  # BOS
away_team_id = 1610612747  # LAL

print("="*70)
print("Testing Back-to-Back Detection")
print("="*70)

print(f"\nGame ID: {game_id}")
print(f"Home Team: {home_team_id}")
print(f"Away Team: {away_team_id}")

# Check if teams are on B2B
home_is_b2b = is_team_on_back_to_back(home_team_id, game_id)
away_is_b2b = is_team_on_back_to_back(away_team_id, game_id)

print(f"\nHome Team on B2B: {home_is_b2b}")
print(f"Away Team on B2B: {away_is_b2b}")

# Get B2B profiles
if home_is_b2b:
    print_team_b2b_summary(home_team_id)

if away_is_b2b:
    print_team_b2b_summary(away_team_id)

# Test the adjustment calculation
if home_is_b2b:
    profile = get_back_to_back_profile(home_team_id)
    if not profile.small_sample:
        off_adj = profile.b2b_off_delta * 0.5
        def_adj = max(0, profile.b2b_def_delta * 0.5)
        print(f"\nHome Team B2B Adjustments (if applied):")
        print(f"  Offensive: {off_adj:+.1f} pts (to home score)")
        print(f"  Defensive: {def_adj:+.1f} pts (to away score)")
    else:
        print(f"\nHome Team: Small sample ({profile.b2b_games} games) - no adjustment")

if away_is_b2b:
    profile = get_back_to_back_profile(away_team_id)
    if not profile.small_sample:
        off_adj = profile.b2b_off_delta * 0.5
        def_adj = max(0, profile.b2b_def_delta * 0.5)
        print(f"\nAway Team B2B Adjustments (if applied):")
        print(f"  Offensive: {off_adj:+.1f} pts (to away score)")
        print(f"  Defensive: {def_adj:+.1f} pts (to home score)")
    else:
        print(f"\nAway Team: Small sample ({profile.b2b_games} games) - no adjustment")
