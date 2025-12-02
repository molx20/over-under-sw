#!/usr/bin/env python3
"""
Debug the SAC @ UTA game pace calculation.
Compare our formula with what might be causing the discrepancy.
"""
import sys
import os
import time

sys.path.append(os.path.dirname(__file__))

from nba_api.stats.endpoints import boxscoretraditionalv2

def debug_game_pace(game_id: str):
    """Fetch box score and manually calculate pace"""
    try:
        print(f"Fetching box score for game {game_id}...")
        time.sleep(0.6)

        box = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
        team_stats = box.get_data_frames()[1]  # Team stats (not player stats)

        print("\n" + "=" * 80)
        print("TEAM BOX SCORE DATA")
        print("=" * 80)

        for idx, row in team_stats.iterrows():
            team_name = row['TEAM_NAME']
            team_abbr = row['TEAM_ABBREVIATION']

            pts = row['PTS']
            fga = row['FGA']
            fta = row['FTA']
            oreb = row['OREB']
            tov = row['TOV']

            # Calculate possessions using our formula
            possessions = fga + (0.44 * fta) - oreb + tov

            print(f"\n{team_name} ({team_abbr}):")
            print(f"  Points: {pts}")
            print(f"  FGA: {fga}")
            print(f"  FTA: {fta}")
            print(f"  OREB: {oreb}")
            print(f"  TOV: {tov}")
            print(f"  Possessions (FGA + 0.44*FTA - OREB + TOV): {possessions:.2f}")
            print(f"  OffRtg (PTS / Poss * 100): {(pts / possessions * 100):.2f}")

        # Calculate game pace
        if len(team_stats) == 2:
            team1 = team_stats.iloc[0]
            team2 = team_stats.iloc[1]

            poss1 = team1['FGA'] + (0.44 * team1['FTA']) - team1['OREB'] + team1['TOV']
            poss2 = team2['FGA'] + (0.44 * team2['FTA']) - team2['OREB'] + team2['TOV']

            game_pace = (poss1 + poss2) / 2

            print("\n" + "=" * 80)
            print("GAME PACE CALCULATION")
            print("=" * 80)
            print(f"Team 1 Possessions: {poss1:.2f}")
            print(f"Team 2 Possessions: {poss2:.2f}")
            print(f"Game Pace (average): {game_pace:.2f}")

            # Try alternative possession formulas
            print("\n" + "=" * 80)
            print("ALTERNATIVE FORMULAS")
            print("=" * 80)

            # Formula 1: Dean Oliver's formula (more precise)
            # Poss = 0.96 * (FGA + 0.44 * FTA - OREB + TOV)
            poss1_alt1 = 0.96 * (team1['FGA'] + 0.44 * team1['FTA'] - team1['OREB'] + team1['TOV'])
            poss2_alt1 = 0.96 * (team2['FGA'] + 0.44 * team2['FTA'] - team2['OREB'] + team2['TOV'])
            pace_alt1 = (poss1_alt1 + poss2_alt1) / 2
            print(f"With 0.96 multiplier: {pace_alt1:.2f}")

            # Formula 2: Using team rebounds
            # This is closer to NBA's official formula
            team1_reb = team1['REB']
            team2_reb = team2['REB']
            team1_dreb = team1_reb - team1['OREB']
            team2_dreb = team2_reb - team2['OREB']

            poss1_alt2 = team1['FGA'] + 0.44 * team1['FTA'] - team1['OREB'] + team1['TOV']
            poss2_alt2 = team2['FGA'] + 0.44 * team2['FTA'] - team2['OREB'] + team2['TOV']
            # Adjust for offensive rebounds
            poss1_alt3 = team1['FGA'] - team1['FGM'] - (team1_reb - team1['OREB'] - (team2_reb - team2['OREB'])) + team1['FTA'] * 0.44 + team1['TOV']
            poss2_alt3 = team2['FGA'] - team2['FGM'] - (team2_reb - team2['OREB'] - (team1_reb - team1['OREB'])) + team2['FTA'] * 0.44 + team2['TOV']

            print(f"Team 1 with rebound adjustment: {poss1_alt3:.2f}")
            print(f"Team 2 with rebound adjustment: {poss2_alt3:.2f}")
            print(f"Game Pace with rebound adjustment: {(poss1_alt3 + poss2_alt3) / 2:.2f}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 80)
    print("DEBUG: SAC @ UTA Game Pace (Game ID: 0022500077)")
    print("=" * 80)
    print()

    debug_game_pace('0022500077')
