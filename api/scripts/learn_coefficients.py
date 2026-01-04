#!/usr/bin/env python3
"""
Learn and Save Coefficients Script

One-time script to learn data-driven coefficients from historical NBA game data.
Runs weighted OLS regression on Oct 21, 2025 - Jan 3, 2026 game logs.

Usage:
    python3 api/scripts/learn_coefficients.py

Output:
    - Learns a3, b3, a2, b2 (shooting adjustment coefficients)
    - Learns FTA coefficient (possession formula weight)
    - Learns blend weights (team vs opponent)
    - Validates R² > 0.75 for all regressions
    - Saves to learned_coefficients table with is_active=1

Requires:
    - nba_data.db with team_game_logs data (Oct 21 - Jan 3)
    - learned_coefficients table (run migration first)
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from api.utils.coefficient_learner import (
    learn_shooting_coefficients,
    learn_possession_coefficient,
    learn_blend_weights,
    save_coefficients_to_db,
    get_games_in_window
)


def main():
    """
    Main execution: Learn all coefficients and save to database
    """
    # Configuration
    season = '2025-26'
    start_date = '2025-10-21'
    end_date = '2026-01-03'

    print("=" * 60)
    print("COEFFICIENT LEARNING SCRIPT")
    print("=" * 60)
    print(f"Season: {season}")
    print(f"Training Window: {start_date} to {end_date}")
    print()

    # Step 1: Verify data availability
    print("[1/6] Checking data availability...")
    try:
        games_df = get_games_in_window(start_date, end_date, season)
        games_count = len(games_df)
        print(f"      ✓ Found {games_count} game logs")

        if games_count < 100:
            print(f"      ⚠ Warning: Only {games_count} games found (expected ~1,200)")
            response = input("      Continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("      Aborting.")
                return

    except Exception as e:
        print(f"      ✗ Error fetching games: {e}")
        return

    print()

    # Step 2: Learn 3P shooting coefficients
    print("[2/6] Learning 3P% adjustment coefficients...")
    try:
        a3, b3, r2_3p = learn_shooting_coefficients(season, start_date, end_date, shot_type='3p')
        print(f"      ✓ a3={a3:.4f}, b3={b3:.4f}, R²={r2_3p:.4f}")

        if r2_3p < 0.75:
            print(f"      ⚠ WARNING: R² ({r2_3p:.3f}) below threshold (0.75)")

    except Exception as e:
        print(f"      ✗ Error: {e}")
        return

    print()

    # Step 3: Learn 2P shooting coefficients
    print("[3/6] Learning 2P% adjustment coefficients...")
    try:
        a2, b2, r2_2p = learn_shooting_coefficients(season, start_date, end_date, shot_type='2p')
        print(f"      ✓ a2={a2:.4f}, b2={b2:.4f}, R²={r2_2p:.4f}")

        if r2_2p < 0.75:
            print(f"      ⚠ WARNING: R² ({r2_2p:.3f}) below threshold (0.75)")

    except Exception as e:
        print(f"      ✗ Error: {e}")
        return

    print()

    # Step 4: Learn FTA coefficient
    print("[4/6] Learning FTA coefficient (possession formula)...")
    try:
        fta_coeff, r2_poss = learn_possession_coefficient(season, start_date, end_date)
        print(f"      ✓ fta_coefficient={fta_coeff:.4f}, R²={r2_poss:.4f}")
        print(f"      (Replaces hardcoded 0.44)")

        if r2_poss < 0.75:
            print(f"      ⚠ WARNING: R² ({r2_poss:.3f}) below threshold (0.75)")

    except Exception as e:
        print(f"      ✗ Error: {e}")
        return

    print()

    # Step 5: Learn blend weights
    print("[5/6] Learning blend weights (team vs opponent)...")
    try:
        w_team, w_opp = learn_blend_weights(season, start_date, end_date)
        print(f"      ✓ team_weight={w_team:.2f}, opp_weight={w_opp:.2f}")
        print(f"      (Replaces hardcoded 0.88/0.12)")

    except Exception as e:
        print(f"      ✗ Error: {e}")
        return

    print()

    # Step 6: Save to database
    print("[6/6] Saving coefficients to database...")

    coeffs = {
        'coefficient_set_id': f'{season}_v1',
        'season': season,
        'version': 'v1',
        'a3': a3,
        'b3': b3,
        'a2': a2,
        'b2': b2,
        'fta_coefficient': fta_coeff,
        'blend_weight_team': w_team,
        'blend_weight_opp': w_opp,
        'training_window_start': start_date,
        'training_window_end': end_date,
        'games_count': games_count,
        'r_squared_3p': r2_3p,
        'r_squared_2p': r2_2p,
        'r_squared_poss': r2_poss
    }

    try:
        save_coefficients_to_db(coeffs)
        print(f"      ✓ Saved coefficient set: {coeffs['coefficient_set_id']}")
        print(f"      ✓ Set as active (is_active=1)")

    except ValueError as e:
        print(f"      ✗ Validation failed: {e}")
        print()
        print("      COEFFICIENTS NOT SAVED (quality threshold not met)")
        print("      Please investigate data quality issues before deployment.")
        return

    except Exception as e:
        print(f"      ✗ Database error: {e}")
        return

    print()
    print("=" * 60)
    print("✅ COEFFICIENT LEARNING COMPLETE")
    print("=" * 60)
    print()
    print("Quality Summary:")
    print(f"  3P% Regression:      R² = {r2_3p:.4f} {'✓' if r2_3p >= 0.75 else '✗'}")
    print(f"  2P% Regression:      R² = {r2_2p:.4f} {'✓' if r2_2p >= 0.75 else '✗'}")
    print(f"  Possession Regression: R² = {r2_poss:.4f} {'✓' if r2_poss >= 0.75 else '✗'}")
    print()
    print("Learned Coefficients:")
    print(f"  Shooting (3P): a3={a3:.4f}, b3={b3:.4f}")
    print(f"  Shooting (2P): a2={a2:.4f}, b2={b2:.4f}")
    print(f"  Possession:    FTA coeff={fta_coeff:.4f}")
    print(f"  Blending:      Team={w_team:.2f}, Opp={w_opp:.2f}")
    print()
    print("Next Steps:")
    print("  1. Verify coefficients are reasonable (no extreme values)")
    print("  2. Run backend locally to test API responses")
    print("  3. Deploy backend to production")
    print("  4. Deploy frontend with Translation (Counts) section")
    print()


if __name__ == '__main__':
    main()
