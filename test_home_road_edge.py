"""
Test script for the new Context Home/Road Edge module

This demonstrates the enhanced home/road edge calculation that replaces
the old static Home Court Advantage + Road Penalty logic.
"""

import json
import requests

def test_home_road_edge():
    """Test the home/road edge calculation for a real game"""

    # Use today's ORL @ NYK game
    game_id = "0022500357"

    print("=" * 70)
    print("CONTEXT HOME/ROAD EDGE TEST")
    print("=" * 70)
    print(f"\nTesting game ID: {game_id}")
    print(f"Fetching prediction from API...")

    # Get prediction
    response = requests.get(f"http://127.0.0.1:8080/api/game_detail?game_id={game_id}")
    data = response.json()

    if 'error' in data:
        print(f"\n❌ Error: {data['error']}")
        return

    pred = data.get('prediction', {})
    hre = pred.get('home_road_edge', {})
    breakdown = pred.get('breakdown', {})

    home_team = data.get('home_team', {}).get('abbreviation', 'HOME')
    away_team = data.get('away_team', {}).get('abbreviation', 'AWAY')

    print(f"\n{away_team} @ {home_team}")
    print("-" * 70)

    # Show overall prediction
    print(f"\n📊 PREDICTION SUMMARY:")
    print(f"   Predicted Total: {pred.get('predicted_total', 'N/A')}")
    print(f"   Betting Line: {pred.get('betting_line', 'N/A')}")
    print(f"   Recommendation: {pred.get('recommendation', 'N/A')}")

    # Show home/road edge breakdown
    print(f"\n🏠 HOME/ROAD EDGE BREAKDOWN:")
    print(f"   Home Edge: +{hre.get('home_edge_points', 0):.1f} pts")
    print(f"   Away Edge: {hre.get('away_edge_points', 0):+.1f} pts")
    print(f"   Net Advantage: {hre.get('home_edge_points', 0) + abs(hre.get('away_edge_points', 0)):.1f} pts for {home_team}")

    # Show components
    print(f"\n🔍 COMPONENT BREAKDOWN:")
    components = hre.get('components', {})
    for comp, val in components.items():
        if comp != 'base_hca':
            print(f"   {comp.replace('_', ' ').title()}: {val:+.2f}")

    # Show 5th grade explanations
    print(f"\n📖 SIMPLE EXPLANATIONS (5th Grade Level):")
    reasons = hre.get('reasons_5th_grade', {})
    for key, reason in reasons.items():
        print(f"   • {reason}")

    # Compare with old system
    old_hca = breakdown.get('home_court_advantage', 0)
    old_road_penalty = breakdown.get('road_penalty', 0)
    old_total = old_hca + old_road_penalty
    new_total = hre.get('home_edge_points', 0) + hre.get('away_edge_points', 0)

    print(f"\n⚖️  COMPARISON WITH OLD SYSTEM:")
    print(f"   Old HCA: +{old_hca:.1f} pts")
    print(f"   Old Road Penalty: {old_road_penalty:+.1f} pts")
    print(f"   Old Total Impact: {old_total:+.1f} pts")
    print(f"   ")
    print(f"   New Home Edge: +{hre.get('home_edge_points', 0):.1f} pts")
    print(f"   New Away Edge: {hre.get('away_edge_points', 0):+.1f} pts")
    print(f"   New Total Impact: {new_total:+.1f} pts")
    print(f"   ")
    print(f"   Difference: {new_total - old_total:+.1f} pts (more nuanced with new system)")

    print("\n" + "=" * 70)
    print("✅ Test completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    test_home_road_edge()
