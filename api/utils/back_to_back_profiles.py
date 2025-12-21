"""
Back-to-Back (B2B) Profile Calculator

Computes team-specific back-to-back performance metrics by analyzing
historical game logs where is_back_to_back = true.

Profiles include:
- B2B offensive performance (PPG vs season average)
- B2B defensive performance (Opp PPG vs season average)
- B2B pace changes (pace vs season average)
- Sample size indicators
"""

import sqlite3
from typing import Dict, Optional, Any

DB_PATH = 'api/data/nba_data.db'


class BackToBackProfile:
    """
    Container for a team's back-to-back performance profile
    """
    def __init__(self, team_id: int):
        self.team_id = team_id

        # B2B stats
        self.b2b_games = 0
        self.b2b_ppg = 0.0
        self.b2b_opp_ppg = 0.0
        self.b2b_pace = 0.0

        # Season stats (for comparison)
        self.season_ppg = 0.0
        self.season_opp_ppg = 0.0
        self.season_pace = 0.0

        # Deltas (B2B vs Season)
        self.b2b_off_delta = 0.0  # negative = scores less on B2Bs
        self.b2b_def_delta = 0.0  # positive = allows more on B2Bs
        self.b2b_pace_delta = 0.0  # positive = faster on B2Bs

        # Data quality flag
        self.small_sample = True  # True if b2b_games < 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for JSON serialization"""
        return {
            'team_id': self.team_id,
            'b2b_games': self.b2b_games,
            'b2b_ppg': round(self.b2b_ppg, 1),
            'b2b_opp_ppg': round(self.b2b_opp_ppg, 1),
            'b2b_pace': round(self.b2b_pace, 1),
            'season_ppg': round(self.season_ppg, 1),
            'season_opp_ppg': round(self.season_opp_ppg, 1),
            'season_pace': round(self.season_pace, 1),
            'b2b_off_delta': round(self.b2b_off_delta, 1),
            'b2b_def_delta': round(self.b2b_def_delta, 1),
            'b2b_pace_delta': round(self.b2b_pace_delta, 1),
            'small_sample': self.small_sample
        }

    def __repr__(self):
        return (f"BackToBackProfile(team_id={self.team_id}, "
                f"b2b_games={self.b2b_games}, "
                f"off_delta={self.b2b_off_delta:.1f}, "
                f"def_delta={self.b2b_def_delta:.1f}, "
                f"pace_delta={self.b2b_pace_delta:.1f}, "
                f"small_sample={self.small_sample})")


def get_back_to_back_profile(team_id: int, season: str = '2025-26') -> BackToBackProfile:
    """
    Compute back-to-back performance profile for a specific team.

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')

    Returns:
        BackToBackProfile with B2B stats and deltas
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    profile = BackToBackProfile(team_id)

    # ===== STEP 1: Get season averages (all games) =====
    cursor.execute("""
        SELECT
            COUNT(*) as games,
            AVG(team_pts) as avg_ppg,
            AVG(opp_pts) as avg_opp_ppg,
            AVG(pace) as avg_pace
        FROM team_game_logs
        WHERE team_id = ?
          AND season = ?
    """, (team_id, season))

    season_row = cursor.fetchone()
    if not season_row or season_row[0] == 0:
        # No games found for this team
        conn.close()
        return profile

    season_games, season_ppg, season_opp_ppg, season_pace = season_row
    profile.season_ppg = season_ppg or 0.0
    profile.season_opp_ppg = season_opp_ppg or 0.0
    profile.season_pace = season_pace or 0.0

    # ===== STEP 2: Get B2B averages (only B2B games) =====
    cursor.execute("""
        SELECT
            COUNT(*) as b2b_games,
            AVG(team_pts) as avg_ppg,
            AVG(opp_pts) as avg_opp_ppg,
            AVG(pace) as avg_pace
        FROM team_game_logs
        WHERE team_id = ?
          AND season = ?
          AND is_back_to_back = 1
    """, (team_id, season))

    b2b_row = cursor.fetchone()
    if not b2b_row or b2b_row[0] == 0:
        # No B2B games found - return profile with zero deltas
        conn.close()
        return profile

    b2b_games, b2b_ppg, b2b_opp_ppg, b2b_pace = b2b_row
    profile.b2b_games = b2b_games or 0
    profile.b2b_ppg = b2b_ppg or 0.0
    profile.b2b_opp_ppg = b2b_opp_ppg or 0.0
    profile.b2b_pace = b2b_pace or 0.0

    # ===== STEP 3: Compute deltas =====
    profile.b2b_off_delta = profile.b2b_ppg - profile.season_ppg
    profile.b2b_def_delta = profile.b2b_opp_ppg - profile.season_opp_ppg
    profile.b2b_pace_delta = profile.b2b_pace - profile.season_pace

    # ===== STEP 4: Set sample size flag =====
    profile.small_sample = profile.b2b_games < 3

    conn.close()
    return profile


def is_team_on_back_to_back(team_id: int, game_id: str) -> bool:
    """
    Check if a team is on a back-to-back for a specific game.

    Args:
        team_id: NBA team ID
        game_id: Game ID to check

    Returns:
        True if team is on second night of B2B, False otherwise
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT is_back_to_back
        FROM team_game_logs
        WHERE team_id = ? AND game_id = ?
    """, (team_id, game_id))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return False

    return bool(row[0])


def get_team_rest_days(team_id: int, game_id: str) -> Optional[int]:
    """
    Get the number of rest days before a specific game.

    Args:
        team_id: NBA team ID
        game_id: Game ID to check

    Returns:
        Number of rest days, or None if first game of season
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT rest_days
        FROM team_game_logs
        WHERE team_id = ? AND game_id = ?
    """, (team_id, game_id))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return row[0]


# ===== Testing / Debug Functions =====

def print_team_b2b_summary(team_id: int, season: str = '2025-26'):
    """Print a human-readable summary of a team's B2B profile"""
    profile = get_back_to_back_profile(team_id, season)

    print(f"\n{'='*60}")
    print(f"Back-to-Back Profile for Team {team_id} ({season})")
    print(f"{'='*60}")
    print(f"B2B Games: {profile.b2b_games}")
    print(f"Sample Size: {'⚠️  Small Sample (< 3 games)' if profile.small_sample else '✓ Sufficient Data'}")
    print(f"\n{'Metric':<20} {'Season':>10} {'B2B':>10} {'Delta':>10}")
    print(f"{'-'*60}")
    print(f"{'PPG':<20} {profile.season_ppg:>10.1f} {profile.b2b_ppg:>10.1f} {profile.b2b_off_delta:>+10.1f}")
    print(f"{'Opp PPG':<20} {profile.season_opp_ppg:>10.1f} {profile.b2b_opp_ppg:>10.1f} {profile.b2b_def_delta:>+10.1f}")
    print(f"{'Pace':<20} {profile.season_pace:>10.1f} {profile.b2b_pace:>10.1f} {profile.b2b_pace_delta:>+10.1f}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    # Test with a few teams
    import sys

    if len(sys.argv) > 1:
        team_id = int(sys.argv[1])
        print_team_b2b_summary(team_id)
    else:
        # Test with first 5 teams
        print("Testing B2B profiles for first 5 teams:")
        for team_id in [1610612737, 1610612738, 1610612739, 1610612740, 1610612741]:
            print_team_b2b_summary(team_id)
