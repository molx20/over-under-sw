#!/usr/bin/env python3
"""
Test fatigue adjustment logic
"""

import sys
sys.path.insert(0, '/Users/malcolmlittle/NBA OVER UNDER SW')

from datetime import datetime, timedelta
from api.utils.prediction_engine import apply_fatigue_penalty

print("=" * 80)
print("FATIGUE ADJUSTMENT UNIT TESTS")
print("=" * 80)
print()

# Helper to create mock recent games
def create_mock_game(days_ago, pts, opp_pts):
    """Create a mock game with date and scores"""
    game_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    return {
        'GAME_DATE': game_date,
        'PTS': pts,
        'OPP_PTS': opp_pts
    }


# Test 1: Neither team on B2B, no recent extreme games
print("TEST 1: Well-rested teams (no fatigue)")
print("-" * 80)
home_games = [create_mock_game(3, 110, 105)]  # 3 days ago
away_games = [create_mock_game(4, 115, 108)]  # 4 days ago
predicted_total = 225.0

adjusted, penalty, explanation = apply_fatigue_penalty(predicted_total, home_games, away_games)

print(f"Initial total: {predicted_total}")
print(f"Adjusted total: {adjusted}")
print(f"Penalty: {penalty}")
print(f"Explanation: {explanation}")

assert penalty == 0, f"Expected no penalty, got {penalty}"
assert adjusted == predicted_total, f"Expected no change, got {adjusted} vs {predicted_total}"
print("✓ PASS: No fatigue penalty applied\n")


# Test 2: One team on B2B, normal recent game
print("TEST 2: Back-to-back (normal game)")
print("-" * 80)
home_games = [create_mock_game(1, 110, 105)]  # Yesterday (B2B)
away_games = [create_mock_game(3, 115, 108)]  # 3 days ago
predicted_total = 225.0

adjusted, penalty, explanation = apply_fatigue_penalty(predicted_total, home_games, away_games)

print(f"Initial total: {predicted_total}")
print(f"Adjusted total: {adjusted}")
print(f"Penalty: {penalty}")
print(f"Explanation: {explanation}")

assert penalty == 4.0, f"Expected B2B penalty of 4, got {penalty}"
assert adjusted == 221.0, f"Expected 221.0, got {adjusted}"
print("✓ PASS: B2B penalty of 4 points applied\n")


# Test 3: Both teams on B2B
print("TEST 3: Both teams on back-to-back")
print("-" * 80)
home_games = [create_mock_game(1, 112, 108)]  # Yesterday (B2B)
away_games = [create_mock_game(1, 118, 110)]  # Yesterday (B2B)
predicted_total = 230.0

adjusted, penalty, explanation = apply_fatigue_penalty(predicted_total, home_games, away_games)

print(f"Initial total: {predicted_total}")
print(f"Adjusted total: {adjusted}")
print(f"Penalty: {penalty}")
print(f"Explanation: {explanation}")

assert penalty == 4.0, f"Expected B2B penalty of 4, got {penalty}"
assert adjusted == 226.0, f"Expected 226.0, got {adjusted}"
assert "Both teams" in explanation, f"Expected 'Both teams' in explanation"
print("✓ PASS: B2B penalty applied for both teams\n")


# Test 4: One team played 280+ total within 2 days
print("TEST 4: Recent extreme shootout game (280+ points)")
print("-" * 80)
home_games = [create_mock_game(2, 145, 140)]  # 2 days ago, 285 total
away_games = [create_mock_game(3, 110, 105)]  # 3 days ago, normal
predicted_total = 228.0

adjusted, penalty, explanation = apply_fatigue_penalty(predicted_total, home_games, away_games)

print(f"Initial total: {predicted_total}")
print(f"Adjusted total: {adjusted}")
print(f"Penalty: {penalty}")
print(f"Explanation: {explanation}")

assert penalty == 7.0, f"Expected OT/Shootout penalty of 7, got {penalty}"
assert adjusted == 221.0, f"Expected 221.0, got {adjusted}"
assert "285" in explanation or "extreme" in explanation.lower(), f"Expected shootout info in explanation"
print("✓ PASS: Extreme game penalty of 7 points applied\n")


# Test 5: One team played likely OT game (270+ total) within 2 days
print("TEST 5: Likely overtime game (270+ points)")
print("-" * 80)
home_games = [create_mock_game(3, 110, 105)]  # 3 days ago, normal
away_games = [create_mock_game(1, 140, 135)]  # Yesterday, 275 total (likely OT)
predicted_total = 232.0

adjusted, penalty, explanation = apply_fatigue_penalty(predicted_total, home_games, away_games)

print(f"Initial total: {predicted_total}")
print(f"Adjusted total: {adjusted}")
print(f"Penalty: {penalty}")
print(f"Explanation: {explanation}")

assert penalty == 7.0, f"Expected OT/Shootout penalty of 7, got {penalty}"
assert adjusted == 225.0, f"Expected 225.0, got {adjusted}"
print("✓ PASS: Likely OT penalty of 7 points applied\n")


# Test 6: Team on B2B, but previous game was extreme (should use higher penalty)
print("TEST 6: B2B with extreme previous game (higher penalty takes precedence)")
print("-" * 80)
home_games = [create_mock_game(1, 148, 142)]  # Yesterday B2B with 290 total
away_games = [create_mock_game(4, 110, 105)]  # 4 days ago, normal
predicted_total = 235.0

adjusted, penalty, explanation = apply_fatigue_penalty(predicted_total, home_games, away_games)

print(f"Initial total: {predicted_total}")
print(f"Adjusted total: {adjusted}")
print(f"Penalty: {penalty}")
print(f"Explanation: {explanation}")

assert penalty == 7.0, f"Expected extreme game penalty of 7 (not B2B 4), got {penalty}"
assert adjusted == 228.0, f"Expected 228.0, got {adjusted}"
print("✓ PASS: Extreme game penalty overrides B2B penalty\n")


# Test 7: No recent games data
print("TEST 7: No recent games data")
print("-" * 80)
home_games = []  # No data
away_games = []  # No data
predicted_total = 220.0

adjusted, penalty, explanation = apply_fatigue_penalty(predicted_total, home_games, away_games)

print(f"Initial total: {predicted_total}")
print(f"Adjusted total: {adjusted}")
print(f"Penalty: {penalty}")
print(f"Explanation: {explanation}")

assert penalty == 0, f"Expected no penalty, got {penalty}"
assert adjusted == predicted_total, f"Expected no change"
print("✓ PASS: No penalty when data unavailable\n")


print("=" * 80)
print("ALL TESTS PASSED ✓")
print("=" * 80)
print()
print("Summary:")
print("- Well-rested teams: No penalty")
print("- Back-to-back (normal): -4 points")
print("- Back-to-back (both teams): -4 points")
print("- Recent extreme game (280+): -7 points")
print("- Recent likely OT (270+): -7 points")
print("- Extreme game overrides B2B: -7 points (not -4)")
print("- No data: No penalty")
print()
