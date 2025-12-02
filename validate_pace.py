#!/usr/bin/env python3
"""
Validate pace calculation by comparing with NBA API's official box score stats.
"""
import sys
import os
import time

sys.path.append(os.path.dirname(__file__))

from nba_api.stats.endpoints import boxscoreadvancedv2

def check_game_pace(game_id: str, team1_name: str, team2_name: str):
    """Fetch official pace from NBA API for a specific game"""
    try:
        print(f"\nFetching box score for game {game_id}...")
        time.sleep(0.6)  # Rate limiting

        box = boxscoreadvancedv2.BoxScoreAdvancedV2(game_id=game_id)
        df = box.get_data_frames()[0]  # Team stats

        print(f"  Columns: {df.columns.tolist()}")

        if len(df) >= 2:
            if 'PACE' in df.columns:
                team1_pace = df.iloc[0]['PACE']
                team2_pace = df.iloc[1]['PACE']
                team1 = df.iloc[0]['TEAM_NAME'] if 'TEAM_NAME' in df.columns else df.iloc[0]['TEAM_ABBREVIATION']
                team2 = df.iloc[1]['TEAM_NAME'] if 'TEAM_NAME' in df.columns else df.iloc[1]['TEAM_ABBREVIATION']

                print(f"  {team1}: {team1_pace}")
                print(f"  {team2}: {team2_pace}")

                return (team1_pace, team2_pace)
            else:
                print(f"  Warning: PACE column not found")
                return (None, None)
        else:
            print(f"  Warning: Expected 2 teams, got {len(df)}")
            return (None, None)

    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return (None, None)

if __name__ == '__main__':
    print("=" * 60)
    print("Validating Pace Calculation with NBA API")
    print("=" * 60)

    # Utah Jazz recent games
    games = [
        ('0022500301', 'UTA', 'HOU'),  # 2025-11-30
        ('0022500077', 'UTA', 'SAC'),  # 2025-11-28
        ('0022500291', 'UTA', 'GSW'),  # 2025-11-24
        ('0022500282', 'UTA', 'LAL'),  # 2025-11-23
        ('0022500055', 'UTA', 'OKC'),  # 2025-11-21
    ]

    print("\nChecking Utah Jazz last 5 games...")

    paces = []
    for game_id, team1, team2 in games:
        pace1, pace2 = check_game_pace(game_id, team1, team2)
        if pace1 is not None and pace2 is not None:
            # Both teams should have same pace
            avg_pace = (pace1 + pace2) / 2
            paces.append(avg_pace)
            print(f"  Average: {avg_pace:.2f}")

    if paces:
        print("\n" + "=" * 60)
        print(f"NBA API Last 5 Average Pace: {sum(paces) / len(paces):.2f}")
        print("=" * 60)
