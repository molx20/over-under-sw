"""
Team Profile and Matchup Profile Builders for v5.0 Prediction Engine

These helpers build comprehensive team and matchup profiles using only current-season
game logs from the team_game_logs table.

TeamProfile: Season and recent stats for a single team
MatchupProfile: Head-to-head and opponent-type patterns
"""

import sqlite3
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@dataclass
class TeamProfile:
    """
    Comprehensive team profile built from current season game logs.

    Contains:
    - Season averages (all games)
    - Last 5 game averages (recent form)
    - Home/Away splits
    - Key stats: PPG, Pace, 3PT, TO, FT, AST, ORtg, DRtg
    """
    team_id: int
    team_name: str
    season: str

    # Season averages (all games)
    season_ppg: float
    season_opp_ppg: float
    season_pace: float
    season_ortg: float
    season_drtg: float
    season_fg3_pct: float
    season_ft_pct: float
    season_assists: float
    season_turnovers: float
    season_games: int

    # Last 5 games (recent form)
    last_5_ppg: float
    last_5_opp_ppg: float
    last_5_pace: float
    last_5_ortg: float
    last_5_drtg: float
    last_5_fg3_pct: float
    last_5_assists: float
    last_5_turnovers: float

    # Home/Away splits
    home_ppg: float
    home_games: int
    away_ppg: float
    away_games: int

    # Derived metrics
    recent_ortg_change: float  # last_5_ortg - season_ortg

    def __repr__(self):
        return (f"TeamProfile({self.team_name}: "
                f"Season={self.season_ppg:.1f}ppg, "
                f"Last5={self.last_5_ppg:.1f}ppg, "
                f"Pace={self.season_pace:.1f})")


@dataclass
class MatchupProfile:
    """
    Matchup-specific profile analyzing head-to-head and opponent-type patterns.

    Contains:
    - Direct H2H results vs this specific opponent
    - Performance vs fast/slow opponents
    - Performance vs good/bad defenses
    """
    team_id: int
    opponent_id: int
    season: str

    # Head-to-head vs this opponent
    h2h_games: int
    h2h_ppg: float
    h2h_opp_ppg: float
    h2h_pace: float

    # Performance vs fast opponents (pace > 101)
    vs_fast_games: int
    vs_fast_ppg: float
    vs_fast_opp_ppg: float

    # Performance vs slow opponents (pace < 98)
    vs_slow_games: int
    vs_slow_ppg: float
    vs_slow_opp_ppg: float

    # Performance vs good defenses (DRtg rank 1-10)
    vs_good_def_games: int
    vs_good_def_ppg: float

    # Performance vs bad defenses (DRtg rank 21-30)
    vs_bad_def_games: int
    vs_bad_def_ppg: float

    def __repr__(self):
        return (f"MatchupProfile(H2H: {self.h2h_games} games, "
                f"PPG={self.h2h_ppg:.1f} vs {self.h2h_opp_ppg:.1f})")


def build_team_profile(team_id: int, season: str = '2025-26',
                       as_of_date: Optional[str] = None) -> Optional[TeamProfile]:
    """
    Build comprehensive TeamProfile from team_game_logs.

    Args:
        team_id: NBA team ID
        season: NBA season (e.g., '2025-26')
        as_of_date: Optional date cutoff (ISO format) for backtesting

    Returns:
        TeamProfile object or None if insufficient data
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Get team name
    cursor.execute("SELECT full_name FROM nba_teams WHERE team_id = ?", (team_id,))
    team_row = cursor.fetchone()
    if not team_row:
        conn.close()
        return None
    team_name = team_row['full_name']

    # Build WHERE clause for date filtering
    date_filter = ""
    params = [team_id, season]
    if as_of_date:
        date_filter = "AND game_date < ?"
        params.append(as_of_date)

    # Get all games for season averages
    cursor.execute(f"""
        SELECT
            COUNT(*) as games,
            AVG(team_pts) as ppg,
            AVG(opp_pts) as opp_ppg,
            AVG(pace) as pace,
            AVG(off_rating) as ortg,
            AVG(def_rating) as drtg,
            AVG(fg3_pct) as fg3_pct,
            AVG(ft_pct) as ft_pct,
            AVG(assists) as assists,
            AVG(turnovers) as turnovers
        FROM team_game_logs
        WHERE team_id = ? AND season = ? {date_filter}
    """, params)

    season_stats = cursor.fetchone()
    if not season_stats or season_stats['games'] < 5:
        conn.close()
        return None

    # Get last 5 games
    cursor.execute(f"""
        SELECT
            team_pts, opp_pts, pace, off_rating, def_rating,
            fg3_pct, assists, turnovers
        FROM team_game_logs
        WHERE team_id = ? AND season = ? {date_filter}
        ORDER BY game_date DESC
        LIMIT 5
    """, params)

    last_5_games = cursor.fetchall()
    if len(last_5_games) < 5:
        # Use whatever we have if less than 5 games
        last_5_games = last_5_games or [season_stats]

    last_5_ppg = sum(g['team_pts'] for g in last_5_games) / len(last_5_games)
    last_5_opp_ppg = sum(g['opp_pts'] for g in last_5_games) / len(last_5_games)
    last_5_pace = sum(g['pace'] for g in last_5_games if g['pace']) / len(last_5_games)
    last_5_ortg = sum(g['off_rating'] for g in last_5_games if g['off_rating']) / len(last_5_games)
    last_5_drtg = sum(g['def_rating'] for g in last_5_games if g['def_rating']) / len(last_5_games)
    last_5_fg3_pct = sum(g['fg3_pct'] for g in last_5_games if g['fg3_pct']) / len(last_5_games)
    last_5_assists = sum(g['assists'] for g in last_5_games if g['assists']) / len(last_5_games)
    last_5_turnovers = sum(g['turnovers'] for g in last_5_games if g['turnovers']) / len(last_5_games)

    # Get home/away splits
    cursor.execute(f"""
        SELECT
            COUNT(*) as games,
            AVG(team_pts) as ppg
        FROM team_game_logs
        WHERE team_id = ? AND season = ? AND is_home = 1 {date_filter}
    """, params)
    home_stats = cursor.fetchone()

    cursor.execute(f"""
        SELECT
            COUNT(*) as games,
            AVG(team_pts) as ppg
        FROM team_game_logs
        WHERE team_id = ? AND season = ? AND is_home = 0 {date_filter}
    """, params)
    away_stats = cursor.fetchone()

    conn.close()

    # Build profile
    profile = TeamProfile(
        team_id=team_id,
        team_name=team_name,
        season=season,

        # Season averages
        season_ppg=float(season_stats['ppg']),
        season_opp_ppg=float(season_stats['opp_ppg']),
        season_pace=float(season_stats['pace'] or 100.0),
        season_ortg=float(season_stats['ortg'] or 110.0),
        season_drtg=float(season_stats['drtg'] or 110.0),
        season_fg3_pct=float(season_stats['fg3_pct'] or 0.35),
        season_ft_pct=float(season_stats['ft_pct'] or 0.75),
        season_assists=float(season_stats['assists'] or 25.0),
        season_turnovers=float(season_stats['turnovers'] or 13.0),
        season_games=int(season_stats['games']),

        # Last 5 games
        last_5_ppg=float(last_5_ppg),
        last_5_opp_ppg=float(last_5_opp_ppg),
        last_5_pace=float(last_5_pace),
        last_5_ortg=float(last_5_ortg),
        last_5_drtg=float(last_5_drtg),
        last_5_fg3_pct=float(last_5_fg3_pct),
        last_5_assists=float(last_5_assists),
        last_5_turnovers=float(last_5_turnovers),

        # Home/Away splits
        home_ppg=float(home_stats['ppg'] or season_stats['ppg']),
        home_games=int(home_stats['games']),
        away_ppg=float(away_stats['ppg'] or season_stats['ppg']),
        away_games=int(away_stats['games']),

        # Derived
        recent_ortg_change=float(last_5_ortg - season_stats['ortg'])
    )

    return profile


def build_matchup_profile(team_id: int, opponent_id: int, season: str = '2025-26',
                         as_of_date: Optional[str] = None) -> MatchupProfile:
    """
    Build MatchupProfile analyzing head-to-head and opponent-type patterns.

    Args:
        team_id: NBA team ID
        opponent_id: Opponent team ID
        season: NBA season (e.g., '2025-26')
        as_of_date: Optional date cutoff for backtesting

    Returns:
        MatchupProfile object (may have 0 games for some categories)
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Build WHERE clause
    date_filter = ""
    params_team = [team_id, season]
    if as_of_date:
        date_filter = "AND game_date < ?"
        params_team.append(as_of_date)

    # Head-to-head vs this specific opponent
    params_h2h = [team_id, season, opponent_id]
    if as_of_date:
        params_h2h.append(as_of_date)

    cursor.execute(f"""
        SELECT
            COUNT(*) as games,
            AVG(team_pts) as ppg,
            AVG(opp_pts) as opp_ppg,
            AVG(pace) as pace
        FROM team_game_logs
        WHERE team_id = ? AND season = ? AND opponent_team_id = ? {date_filter}
    """, params_h2h)

    h2h = cursor.fetchone()

    # Performance vs fast opponents (pace > 101)
    cursor.execute(f"""
        SELECT
            COUNT(*) as games,
            AVG(team_pts) as ppg,
            AVG(opp_pts) as opp_ppg
        FROM team_game_logs
        WHERE team_id = ? AND season = ? AND pace > 101 {date_filter}
    """, params_team)

    vs_fast = cursor.fetchone()

    # Performance vs slow opponents (pace < 98)
    cursor.execute(f"""
        SELECT
            COUNT(*) as games,
            AVG(team_pts) as ppg,
            AVG(opp_pts) as opp_ppg
        FROM team_game_logs
        WHERE team_id = ? AND season = ? AND pace < 98 {date_filter}
    """, params_team)

    vs_slow = cursor.fetchone()

    # Performance vs good defenses (DRtg rank 1-10)
    # We'll approximate by using def_rtg < 110
    cursor.execute(f"""
        SELECT
            COUNT(*) as games,
            AVG(team_pts) as ppg
        FROM team_game_logs tgl
        JOIN team_season_stats tss ON tgl.opponent_team_id = tss.team_id AND tgl.season = tss.season
        WHERE tgl.team_id = ? AND tgl.season = ?
          AND tss.split_type = 'Overall'
          AND tss.def_rtg < 110 {date_filter}
    """, params_team)

    vs_good_def = cursor.fetchone()

    # Performance vs bad defenses (DRtg rank 21-30)
    # Approximate by def_rtg > 115
    cursor.execute(f"""
        SELECT
            COUNT(*) as games,
            AVG(team_pts) as ppg
        FROM team_game_logs tgl
        JOIN team_season_stats tss ON tgl.opponent_team_id = tss.team_id AND tgl.season = tss.season
        WHERE tgl.team_id = ? AND tgl.season = ?
          AND tss.split_type = 'Overall'
          AND tss.def_rtg > 115 {date_filter}
    """, params_team)

    vs_bad_def = cursor.fetchone()

    conn.close()

    # Build profile with safe defaults
    profile = MatchupProfile(
        team_id=team_id,
        opponent_id=opponent_id,
        season=season,

        # Head-to-head
        h2h_games=int(h2h['games']),
        h2h_ppg=float(h2h['ppg'] or 0),
        h2h_opp_ppg=float(h2h['opp_ppg'] or 0),
        h2h_pace=float(h2h['pace'] or 100.0),

        # Vs fast
        vs_fast_games=int(vs_fast['games']),
        vs_fast_ppg=float(vs_fast['ppg'] or 0),
        vs_fast_opp_ppg=float(vs_fast['opp_ppg'] or 0),

        # Vs slow
        vs_slow_games=int(vs_slow['games']),
        vs_slow_ppg=float(vs_slow['ppg'] or 0),
        vs_slow_opp_ppg=float(vs_slow['opp_ppg'] or 0),

        # Vs good defense
        vs_good_def_games=int(vs_good_def['games']),
        vs_good_def_ppg=float(vs_good_def['ppg'] or 0),

        # Vs bad defense
        vs_bad_def_games=int(vs_bad_def['games']),
        vs_bad_def_ppg=float(vs_bad_def['ppg'] or 0)
    )

    return profile
