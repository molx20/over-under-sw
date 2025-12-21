"""Test B2B detection in prediction engine"""
from api.utils.prediction_engine import predict_game_total
import json

# Test with game 0022500338 (both teams on B2B)
print("Testing prediction for game 0022500338 (both teams on B2B)")
print("="*70)

result = predict_game_total('0022500338', betting_line=220.5)

print("\n=== PREDICTION RESULT ===")
print(f"Predicted Total: {result['predicted_total']}")
print(f"Betting Line: {result['betting_line']}")
print(f"Recommendation: {result['recommendation']}")

print("\n=== BACK-TO-BACK DEBUG ===")
b2b_debug = result.get('back_to_back_debug', {})
print(json.dumps(b2b_debug, indent=2))

print("\n=== BREAKDOWN ===")
print(f"Home Projected: {result['breakdown']['home_projected']}")
print(f"Away Projected: {result['breakdown']['away_projected']}")
