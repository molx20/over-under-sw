"""
NBA Data Query Module

SQLite-only data access layer for request handlers.
This module provides all data needed by the API endpoints.

IMPORTANT: This module must NEVER import nba_api.
All data is fetched from SQLite (synced by sync_nba_data.py).

If data is missing, this module returns league-average fallback values
to ensure predictions can always be generated.
"""

import sqlite3
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

# Database path
NBA_DATA_DB_PATH = get_db_path('nba_data.db')

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================================
# TEAMS QUERIES
# ============================================================================

def get_all_teams(season: str = '2025-26') -> List[Dict]:
    """
    Get all NBA teams

    Returns:
        List of team dicts with id, abbreviation, full_name
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT team_id as id, team_abbreviation as abbreviation, full_name
        FROM nba_teams
        WHERE season = ?
        ORDER BY full_name
    ''', (season,))

    teams = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return teams


def get_team_by_id(team_id: int) -> Optional[Dict]:
    """Get team by ID"""
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT team_id as id, team_abbreviation as abbreviation, full_name
        FROM nba_teams
        WHERE team_id = ?
    ''', (team_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_team_by_abbreviation(abbr: str) -> Optional[Dict]:
    """Get team by abbreviation"""
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT team_id as id, team_abbreviation as abbreviation, full_name
        FROM nba_teams
        WHERE team_abbreviation = ?
    ''', (abbr.upper(),))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_team_id(team_name: str) -> Optional[int]:
    """
    Get team ID by name (e.g., 'Lakers', 'Nets')
    Matches against full_name or abbreviation
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Try exact abbreviation match first
    cursor.execute('''
        SELECT team_id
        FROM nba_teams
        WHERE team_abbreviation = ?
    ''', (team_name.upper(),))

    row = cursor.fetchone()
    if row:
        conn.close()
        return row['team_id']

    # Try partial match on full_name
    cursor.execute('''
        SELECT team_id
        FROM nba_teams
        WHERE LOWER(full_name) LIKE ?
        LIMIT 1
    ''', (f'%{team_name.lower()}%',))

    row = cursor.fetchone()
    conn.close()

    return row['team_id'] if row else None

# ============================================================================
# SEASON STATS QUERIES
# ============================================================================

def get_team_stats(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get team traditional stats with home/away splits

    Returns:
        {
            'overall': {...},
            'home': {...},
            'away': {...}
        }

        Each split contains: PTS, FG_PCT, FG3_PCT, FT_PCT, W, L, etc.
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Query all splits
    cursor.execute('''
        SELECT *
        FROM team_season_stats
        WHERE team_id = ? AND season = ?
    ''', (team_id, season))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        logger.warning(f"No stats found for team {team_id}, using fallback")
        return _get_league_average_fallback(season, 'stats')

    result = {'overall': {}, 'home': {}, 'away': {}}

    for row in rows:
        split_type = row['split_type']
        result[split_type] = {
            'GP': row['games_played'],
            'W': row['wins'],
            'L': row['losses'],
            'PTS': row['ppg'],
            'FG_PCT': row['fg_pct'],
            'FG3_PCT': row['fg3_pct'],
            'FT_PCT': row['ft_pct'],
            'REB': row['rebounds'],
            'AST': row['assists'],
            'STL': row['steals'],
            'BLK': row['blocks'],
            'TOV': row['turnovers'],
            # Shot attempts for MatchupIndicators
            'FGA': row['fg2a'] + row['fg3a'],  # Total FG attempts = 2PA + 3PA
            'FG3A': row['fg3a'],
            'FTA': row['fta'],
        }

    return result


def get_team_advanced_stats(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get team advanced stats (ORTG, DRTG, PACE, etc.)

    Returns dict with OFF_RATING, DEF_RATING, NET_RATING, PACE, TS_PCT, EFG_PCT
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT *
        FROM team_season_stats
        WHERE team_id = ? AND season = ? AND split_type = 'overall'
    ''', (team_id, season))

    row = cursor.fetchone()
    conn.close()

    if not row:
        logger.warning(f"No advanced stats found for team {team_id}, using fallback")
        return _get_league_average_fallback(season, 'advanced')

    return {
        'OFF_RATING': row['off_rtg'],
        'DEF_RATING': row['def_rtg'],
        'NET_RATING': row['net_rtg'],
        'PACE': row['pace'],
        'TS_PCT': row['true_shooting_pct'],
        'EFG_PCT': row['efg_pct'],
    }


def get_team_opponent_stats(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get opponent stats (what opponents score against this team)

    Returns dict with OPP_PTS, etc.
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT *
        FROM team_season_stats
        WHERE team_id = ? AND season = ? AND split_type = 'overall'
    ''', (team_id, season))

    row = cursor.fetchone()
    conn.close()

    if not row:
        logger.warning(f"No opponent stats found for team {team_id}, using fallback")
        return _get_league_average_fallback(season, 'opponent')

    return {
        'OPP_PTS': row['opp_ppg'],
        'GP': row['games_played'],
    }


def get_team_stats_with_ranks(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get team stats with league rankings (replaces team_rankings.py)

    Returns:
        {
            'team_id': int,
            'team_abbreviation': str,
            'season': str,
            'stats': {
                'ppg': {'value': float, 'rank': int},
                'opp_ppg': {'value': float, 'rank': int},
                ...
            }
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Get team abbreviation
    team = get_team_by_id(team_id)
    if not team:
        return None

    cursor.execute('''
        SELECT *
        FROM team_season_stats
        WHERE team_id = ? AND season = ? AND split_type = 'overall'
    ''', (team_id, season))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'team_id': team_id,
        'team_abbreviation': team['abbreviation'],
        'season': season,
        'stats': {
            'ppg': {'value': row['ppg'], 'rank': row['ppg_rank']},
            'opp_ppg': {'value': row['opp_ppg'], 'rank': row['opp_ppg_rank']},
            'fg_pct': {'value': row['fg_pct'], 'rank': row['fg_pct_rank']},
            'three_pct': {'value': row['fg3_pct'], 'rank': row['fg3_pct_rank']},
            'ft_pct': {'value': row['ft_pct'], 'rank': row['ft_pct_rank']},
            'off_rtg': {'value': row['off_rtg'], 'rank': row['off_rtg_rank']},
            'def_rtg': {'value': row['def_rtg'], 'rank': row['def_rtg_rank']},
            'net_rtg': {'value': row['net_rtg'], 'rank': row['net_rtg_rank']},
            'pace': {'value': row['pace'], 'rank': row['pace_rank']},
            'opp_fg3_pct_rank': {'value': row['opp_fg3_pct'] if 'opp_fg3_pct' in row.keys() else None, 'rank': row['opp_fg3_pct_rank'] if 'opp_fg3_pct_rank' in row.keys() else None},
            'opp_tov': {'value': row['opp_tov'] if 'opp_tov' in row.keys() else None, 'rank': row['opp_tov_rank'] if 'opp_tov_rank' in row.keys() else None},
            'opp_assists': {'value': row['opp_assists'] if 'opp_assists' in row.keys() else None, 'rank': row['opp_assists_rank'] if 'opp_assists_rank' in row.keys() else None},
            # Add stats needed for expected vs actual comparison
            'fta': {'value': row['fta'] if 'fta' in row.keys() else None, 'rank': None},
            'turnovers': {'value': row['turnovers'] if 'turnovers' in row.keys() else None, 'rank': None},
            'fg3a': {'value': row['fg3a'] if 'fg3a' in row.keys() else None, 'rank': None},
        }
    }

# ============================================================================
# GAME LOGS QUERIES
# ============================================================================

def get_team_last_n_games(team_id: int, n: int = 5, season: str = '2025-26') -> List[Dict]:
    """
    Get team's last N games

    Returns:
        List of game dicts with GAME_ID, GAME_DATE, MATCHUP, PTS, OPP_PTS, WL, etc.

    Note: If GAME_FILTER_MODE=REGULAR_PLUS_ALL_CUP, only returns Regular Season + NBA Cup games
    """
    import os
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Apply game filtering if enabled
    filter_mode = os.environ.get('GAME_FILTER_MODE', 'DISABLED')
    if filter_mode == 'REGULAR_PLUS_ALL_CUP':
        cursor.execute('''
            SELECT *
            FROM team_game_logs
            WHERE team_id = ? AND season = ?
              AND game_type IN ('Regular Season', 'NBA Cup')
            ORDER BY game_date DESC
            LIMIT ?
        ''', (team_id, season, n))
    else:
        cursor.execute('''
            SELECT *
            FROM team_game_logs
            WHERE team_id = ? AND season = ?
            ORDER BY game_date DESC
            LIMIT ?
        ''', (team_id, season, n))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        logger.warning(f"No game logs found for team {team_id}, returning empty list")
        return []

    return [
        {
            'GAME_ID': row['game_id'],
            'GAME_DATE': row['game_date'],
            'MATCHUP': row['matchup'],
            'PTS': row['team_pts'],
            'OPP_PTS': row['opp_pts'],
            'WL': row['win_loss'],
            'OFF_RATING': row['off_rating'],
            'DEF_RATING': row['def_rating'],
            'PACE': row['pace'],
            'FG_PCT': row['fg_pct'],
            'FG3_PCT': row['fg3_pct'],
            'FT_PCT': row['ft_pct'],
            'REB': row['rebounds'],
            'AST': row['assists'],
            'TOV': row['turnovers'],
            'FGM': row['fgm'],  # Fixed: column is 'fgm' not 'fg_made'
            'FG3A': row['fg3a'],
            'FG3M': row['fg3m'],
            'PTS_PAINT': row['points_in_paint'],
            'OPP_PTS_PAINT': row['opp_points_in_paint'],
            'PTS_FB': row['fast_break_points'],
            'PTS_2ND_CHANCE': row['second_chance_points'],
        }
        for row in rows
    ]


def get_team_last_n_stats_comparison(team_id: int, n: int = 5, season: str = '2025-26') -> Optional[Dict]:
    """
    Get team's last N games stats with comparison to season averages.

    Args:
        team_id: NBA team ID
        n: Number of recent games to average (default 5)
        season: Season string

    Returns:
        Dict with:
        - last_n_games_count: Actual number of games found
        - stats: Dict of stat_key -> {
            'last_n_value': float,  # Average over last N games
            'season_value': float,  # Full season average
            'delta': float          # last_n_value - season_value
          }
        - data_quality: 'excellent' (5+ games), 'good' (3-4), 'poor' (<3), 'none' (0)

    Stats included: ppg, opp_ppg, fg_pct, three_pct, ft_pct, off_rtg, def_rtg, net_rtg, pace
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Get last N games
    cursor.execute('''
        SELECT
            team_pts, opp_pts,
            fg_pct, fg3_pct, ft_pct,
            off_rating, def_rating, pace
        FROM team_game_logs
        WHERE team_id = ? AND season = ?
        ORDER BY game_date DESC
        LIMIT ?
    ''', (team_id, season, n))

    rows = cursor.fetchall()
    games_count = len(rows)

    if games_count == 0:
        conn.close()
        return None

    # Calculate last-N averages (handle None values)
    last_n_ppg = sum(row['team_pts'] for row in rows if row['team_pts'] is not None) / games_count
    last_n_opp_ppg = sum(row['opp_pts'] for row in rows if row['opp_pts'] is not None) / games_count

    # For percentages, filter out None values
    fg_pct_values = [row['fg_pct'] for row in rows if row['fg_pct'] is not None]
    fg3_pct_values = [row['fg3_pct'] for row in rows if row['fg3_pct'] is not None]
    ft_pct_values = [row['ft_pct'] for row in rows if row['ft_pct'] is not None]
    off_rating_values = [row['off_rating'] for row in rows if row['off_rating'] is not None]
    def_rating_values = [row['def_rating'] for row in rows if row['def_rating'] is not None]
    pace_values = [row['pace'] for row in rows if row['pace'] is not None]

    last_n_fg_pct = sum(fg_pct_values) / len(fg_pct_values) if fg_pct_values else 0
    last_n_fg3_pct = sum(fg3_pct_values) / len(fg3_pct_values) if fg3_pct_values else 0
    last_n_ft_pct = sum(ft_pct_values) / len(ft_pct_values) if ft_pct_values else 0
    last_n_off_rtg = sum(off_rating_values) / len(off_rating_values) if off_rating_values else 0
    last_n_def_rtg = sum(def_rating_values) / len(def_rating_values) if def_rating_values else 0
    last_n_pace = sum(pace_values) / len(pace_values) if pace_values else 0

    # Get season averages from team_season_stats
    cursor.execute('''
        SELECT
            ppg, opp_ppg,
            fg_pct, fg3_pct, ft_pct,
            off_rtg, def_rtg, net_rtg, pace
        FROM team_season_stats
        WHERE team_id = ? AND season = ? AND split_type = 'overall'
    ''', (team_id, season))

    season_row = cursor.fetchone()
    conn.close()

    if not season_row:
        return None

    # Calculate deltas and build response
    season_ppg = season_row['ppg'] or 0
    season_opp_ppg = season_row['opp_ppg'] or 0
    season_fg_pct = (season_row['fg_pct'] or 0) * 100  # Convert to percentage
    season_fg3_pct = (season_row['fg3_pct'] or 0) * 100
    season_ft_pct = (season_row['ft_pct'] or 0) * 100
    season_off_rtg = season_row['off_rtg'] or 0
    season_def_rtg = season_row['def_rtg'] or 0
    season_net_rtg = season_row['net_rtg'] or 0
    season_pace = season_row['pace'] or 0

    # Determine data quality
    if games_count >= 5:
        quality = 'excellent'
    elif games_count >= 3:
        quality = 'good'
    else:
        quality = 'poor'

    return {
        'last_n_games_count': games_count,
        'data_quality': quality,
        'stats': {
            'ppg': {
                'last_n_value': round(last_n_ppg, 1),
                'season_value': round(season_ppg, 1),
                'delta': round(last_n_ppg - season_ppg, 1)
            },
            'opp_ppg': {
                'last_n_value': round(last_n_opp_ppg, 1),
                'season_value': round(season_opp_ppg, 1),
                'delta': round(last_n_opp_ppg - season_opp_ppg, 1)
            },
            'fg_pct': {
                'last_n_value': round(last_n_fg_pct * 100, 1),
                'season_value': round(season_fg_pct, 1),
                'delta': round((last_n_fg_pct * 100) - season_fg_pct, 1)
            },
            'three_pct': {
                'last_n_value': round(last_n_fg3_pct * 100, 1),
                'season_value': round(season_fg3_pct, 1),
                'delta': round((last_n_fg3_pct * 100) - season_fg3_pct, 1)
            },
            'ft_pct': {
                'last_n_value': round(last_n_ft_pct * 100, 1),
                'season_value': round(season_ft_pct, 1),
                'delta': round((last_n_ft_pct * 100) - season_ft_pct, 1)
            },
            'off_rtg': {
                'last_n_value': round(last_n_off_rtg, 1),
                'season_value': round(season_off_rtg, 1),
                'delta': round(last_n_off_rtg - season_off_rtg, 1)
            },
            'def_rtg': {
                'last_n_value': round(last_n_def_rtg, 1),
                'season_value': round(season_def_rtg, 1),
                'delta': round(last_n_def_rtg - season_def_rtg, 1)
            },
            'net_rtg': {
                'last_n_value': round(last_n_off_rtg - last_n_def_rtg, 1),
                'season_value': round(season_net_rtg, 1),
                'delta': round((last_n_off_rtg - last_n_def_rtg) - season_net_rtg, 1)
            },
            'pace': {
                'last_n_value': round(last_n_pace, 1),
                'season_value': round(season_pace, 1),
                'delta': round(last_n_pace - season_pace, 1)
            }
        }
    }

# ============================================================================
# TODAY'S GAMES QUERIES
# ============================================================================

def get_todays_games(season: str = '2025-26') -> List[Dict]:
    """
    Get all games scheduled for today and tomorrow (to handle timezone edge cases)

    Returns upcoming games so users always see the next games regardless of timezone.

    Returns:
        List of game dicts with game_id, home_team_id, away_team_id, scores, status
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Get today's date in Eastern Time (NBA schedules use ET)
    from datetime import timezone, timedelta
    import logging

    logger = logging.getLogger(__name__)

    # Define timezones with proper DST handling (matching sync logic)
    # America/Denver: auto-switches between MST (UTC-7) and MDT (UTC-6)
    # America/New_York: auto-switches between EST (UTC-5) and EDT (UTC-4)
    mt_tz = ZoneInfo("America/Denver")
    et_tz = ZoneInfo("America/New_York")

    # Calculate current times
    utc_now = datetime.now(timezone.utc)
    mt_now = datetime.now(mt_tz)
    et_now = datetime.now(et_tz)

    # Log timezone context
    logger.info(f"[BOARD] UTC now: {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"[BOARD] MT  now: {mt_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"[BOARD] ET  now: {et_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Get yesterday, today, AND tomorrow in Eastern Time
    # Yesterday is included because games can run late into the night (past midnight ET)
    # This ensures users always see current/upcoming games regardless of timezone
    yesterday_et = (et_now - timedelta(days=1)).strftime('%Y-%m-%d')
    today_et = et_now.strftime('%Y-%m-%d')
    tomorrow_et = (et_now + timedelta(days=1)).strftime('%Y-%m-%d')

    logger.info(f"[BOARD] Fetching games for ET dates: {yesterday_et}, {today_et}, {tomorrow_et}")

    # Query for yesterday, today, AND tomorrow's ET games
    # This ensures we catch late-night games and upcoming games
    cursor.execute('''
        SELECT *
        FROM todays_games
        WHERE game_date IN (?, ?, ?) AND season = ?
        ORDER BY game_date, game_time_utc
    ''', (yesterday_et, today_et, tomorrow_et, season))

    rows = cursor.fetchall()
    conn.close()

    logger.info(f"[BOARD] Found {len(rows)} total games")

    return [
        {
            'game_id': row['game_id'],
            'game_date': row['game_date'],
            'game_status': row['game_status_text'],
            'home_team_id': row['home_team_id'],
            'home_team_name': row['home_team_name'],
            'home_team_score': row['home_team_score'],
            'away_team_id': row['away_team_id'],
            'away_team_name': row['away_team_name'],
            'away_team_score': row['away_team_score'],
        }
        for row in rows
    ]

# ============================================================================
# MATCHUP DATA (Combines multiple queries)
# ============================================================================

def get_matchup_data(home_team_id: int, away_team_id: int,
                    season: str = '2025-26') -> Optional[Dict]:
    """
    Get comprehensive matchup data for prediction

    This replaces the nba_data.get_matchup_data() function.
    All data comes from SQLite instead of live nba_api calls.

    Returns:
        {
            'home': {
                'stats': {...},
                'advanced': {...},
                'opponent': {...},
                'recent_games': [...]
            },
            'away': {
                'stats': {...},
                'advanced': {...},
                'opponent': {...},
                'recent_games': [...]
            },
            'season_used': str
        }
    """
    logger.info(f"Fetching matchup data for teams {home_team_id} vs {away_team_id} from SQLite")

    # Fetch home team data
    home_stats = get_team_stats(home_team_id, season)
    home_advanced = get_team_advanced_stats(home_team_id, season)
    home_opponent = get_team_opponent_stats(home_team_id, season)
    home_recent = get_team_last_n_games(home_team_id, n=10, season=season)

    # Fetch away team data
    away_stats = get_team_stats(away_team_id, season)
    away_advanced = get_team_advanced_stats(away_team_id, season)
    away_opponent = get_team_opponent_stats(away_team_id, season)
    away_recent = get_team_last_n_games(away_team_id, n=10, season=season)

    # Check if we got critical data
    if not home_stats or not away_stats:
        logger.error(f"Missing critical stats for matchup {home_team_id} vs {away_team_id}")
        return None

    return {
        'home': {
            'stats': home_stats,
            'advanced': home_advanced,
            'opponent': home_opponent,
            'recent_games': home_recent
        },
        'away': {
            'stats': away_stats,
            'advanced': away_advanced,
            'opponent': away_opponent,
            'recent_games': away_recent
        },
        'season_used': season
    }

# ============================================================================
# LEAGUE AVERAGE FALLBACKS
# ============================================================================

def _get_league_average_fallback(season: str, stat_type: str) -> Dict:
    """
    Get league average fallback values when team data is missing

    Args:
        season: Season string
        stat_type: 'stats', 'advanced', or 'opponent'

    Returns:
        Dict with league average values
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM league_averages WHERE season = ?', (season,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        # Hardcoded defaults if no league averages in DB
        logger.warning(f"No league averages found for {season}, using hardcoded defaults")
        ppg, pace, off_rtg, def_rtg = 115.0, 100.0, 115.0, 115.0
        fg_pct, fg3_pct, ft_pct = 46.5, 36.0, 78.0
    else:
        ppg = row['ppg']
        pace = row['pace']
        off_rtg = row['off_rtg']
        def_rtg = row['def_rtg']
        fg_pct = row['fg_pct']
        fg3_pct = row['fg3_pct']
        ft_pct = row['ft_pct']

    logger.info(f"Using league average fallback: {stat_type}")

    if stat_type == 'stats':
        return {
            'overall': {
                'GP': 0,
                'W': 0,
                'L': 0,
                'PTS': ppg,
                'FG_PCT': fg_pct / 100,
                'FG3_PCT': fg3_pct / 100,
                'FT_PCT': ft_pct / 100,
                'REB': 45.0,
                'AST': 25.0,
                'STL': 7.5,
                'BLK': 5.0,
                'TOV': 13.0,
                # Shot attempts for MatchupIndicators
                'FGA': 88.0,  # League average ~88 FGA/game
                'FG3A': 35.0,  # League average ~35 3PA/game
                'FTA': 23.0,  # League average ~23 FTA/game
            },
            'home': {},
            'away': {}
        }
    elif stat_type == 'advanced':
        return {
            'OFF_RATING': off_rtg,
            'DEF_RATING': def_rtg,
            'NET_RATING': 0.0,
            'PACE': pace,
            'TS_PCT': 0.575,
            'EFG_PCT': 0.535,
        }
    elif stat_type == 'opponent':
        return {
            'OPP_PTS': ppg,
            'GP': 0,
        }
    else:
        return {}


# ============================================================================
# TEAM PROFILES QUERIES
# ============================================================================

def get_team_profile(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get team's prediction profile with weights and tier labels

    Returns:
        Dict with pace_label, variance_label, home_away_label, matchup_label,
        season_weight, recent_weight, pace_weight, def_weight, home_away_weight
        or None if profile doesn't exist
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT *
        FROM team_profiles
        WHERE team_id = ? AND season = ?
    ''', (team_id, season))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'team_id': row['team_id'],
        'season': row['season'],
        'pace_label': row['pace_label'],
        'variance_label': row['variance_label'],
        'home_away_label': row['home_away_label'],
        'matchup_label': row['matchup_label'],
        'season_weight': row['season_weight'],
        'recent_weight': row['recent_weight'],
        'pace_weight': row['pace_weight'],
        'def_weight': row['def_weight'],
        'home_away_weight': row['home_away_weight'],
        'updated_at': row['updated_at'],
    }


def upsert_team_profile(profile_dict: Dict) -> None:
    """
    Insert or update a team profile

    Args:
        profile_dict: Dict with team_id, season, labels, weights, and updated_at
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO team_profiles (
            team_id, season,
            pace_label, variance_label, home_away_label, matchup_label,
            season_weight, recent_weight, pace_weight, def_weight, home_away_weight,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        profile_dict['team_id'],
        profile_dict['season'],
        profile_dict['pace_label'],
        profile_dict['variance_label'],
        profile_dict['home_away_label'],
        profile_dict['matchup_label'],
        profile_dict['season_weight'],
        profile_dict['recent_weight'],
        profile_dict['pace_weight'],
        profile_dict['def_weight'],
        profile_dict['home_away_weight'],
        profile_dict['updated_at'],
    ))

    conn.commit()
    conn.close()


# ============================================================================
# SCORING VS PACE
# ============================================================================

def get_pace_bucket(pace: float) -> str:
    """
    Classify a pace value into slow/normal/fast bucket

    Args:
        pace: Pace value (possessions per 48 minutes)

    Returns:
        'slow', 'normal', or 'fast'
    """
    from api.utils.pace_constants import PACE_SLOW_THRESHOLD, PACE_FAST_THRESHOLD

    if pace < PACE_SLOW_THRESHOLD:
        return 'slow'
    elif pace > PACE_FAST_THRESHOLD:
        return 'fast'
    else:
        return 'normal'


def get_team_scoring_vs_pace(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get team's scoring splits by pace bucket

    Args:
        team_id: Team's NBA ID
        season: Season string

    Returns:
        Dict with pace buckets as keys ('slow', 'normal', 'fast'), each containing:
        - avg_points: Average points scored in that pace bucket
        - games: Number of games in that bucket
        or None if no data exists
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT pace_bucket, avg_points_for, games_played
        FROM team_scoring_vs_pace
        WHERE team_id = ? AND season = ?
    ''', (team_id, season))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    result = {}
    for row in rows:
        result[row['pace_bucket']] = {
            'avg_points': row['avg_points_for'],
            'games': row['games_played']
        }

    return result


def upsert_team_scoring_vs_pace(team_id: int, season: str, pace_bucket: str,
                                  avg_points: float, games: int, updated_at: str) -> None:
    """
    Insert or update team scoring vs pace data

    Args:
        team_id: Team's NBA ID
        season: Season string
        pace_bucket: 'slow', 'normal', or 'fast'
        avg_points: Average points scored in this pace bucket
        games: Number of games in this bucket
        updated_at: ISO timestamp
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO team_scoring_vs_pace (
            team_id, season, pace_bucket, avg_points_for, games_played, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (team_id, season, pace_bucket, avg_points, games, updated_at))

    conn.commit()
    conn.close()


# ============================================================================
# DATA FRESHNESS
# ============================================================================

def get_data_freshness() -> Dict:
    """
    Check data freshness for monitoring

    Returns:
        {
            'teams': {'count': int, 'last_sync': str},
            'season_stats': {'count': int, 'last_sync': str},
            'game_logs': {'count': int, 'last_sync': str},
            'todays_games': {'count': int, 'last_sync': str},
            'is_stale': bool (True if any data >12 hours old)
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    freshness = {}
    now = datetime.now()
    is_stale = False

    # Check teams
    cursor.execute('SELECT COUNT(*), MAX(last_updated) FROM nba_teams')
    row = cursor.fetchone()
    freshness['teams'] = {'count': row[0], 'last_sync': row[1]}
    if row[1]:
        try:
            age = (now - datetime.fromisoformat(row[1])).total_seconds() / 3600
            if age > 12:
                is_stale = True
        except:
            pass

    # Check season stats
    cursor.execute('SELECT COUNT(*), MAX(synced_at) FROM team_season_stats')
    row = cursor.fetchone()
    freshness['season_stats'] = {'count': row[0], 'last_sync': row[1]}
    if row[1]:
        try:
            age = (now - datetime.fromisoformat(row[1])).total_seconds() / 3600
            if age > 12:
                is_stale = True
        except:
            pass

    # Check game logs
    cursor.execute('SELECT COUNT(*), MAX(synced_at) FROM team_game_logs')
    row = cursor.fetchone()
    freshness['game_logs'] = {'count': row[0], 'last_sync': row[1]}
    if row[1]:
        try:
            age = (now - datetime.fromisoformat(row[1])).total_seconds() / 3600
            if age > 12:
                is_stale = True
        except:
            pass

    # Check today's games
    cursor.execute('SELECT COUNT(*), MAX(synced_at) FROM todays_games')
    row = cursor.fetchone()
    freshness['todays_games'] = {'count': row[0], 'last_sync': row[1]}

    conn.close()

    freshness['is_stale'] = is_stale

    return freshness


# ============================================================================
# GAME ACTUAL TOTALS (for Model Evaluation)
# ============================================================================

def get_game_actual_total(game_id: str) -> Optional[int]:
    """
    Get the actual total points for a completed game.

    This is used for model evaluation to compare predicted totals vs actual results.
    The actual_total_points is simply home_score + away_score for completed games.

    Args:
        game_id: NBA game ID (e.g., "0022500338")

    Returns:
        Integer total points if game is completed, None if game not found or incomplete

    Example:
        >>> actual_total = get_game_actual_total("0022500338")
        >>> predicted_total = 225.5
        >>> error = abs(predicted_total - actual_total)
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT actual_total_points
        FROM games
        WHERE id = ? AND status = 'final' AND actual_total_points IS NOT NULL
    """, (game_id,))

    row = cursor.fetchone()
    conn.close()

    return row['actual_total_points'] if row else None


def get_game_box_score(game_id: str, team_id: int) -> Optional[Dict]:
    """
    Get box score statistics for a specific team in a specific game.

    Args:
        game_id: NBA game ID (e.g., "0022500338")
        team_id: Team ID

    Returns:
        Dictionary with box score stats:
        {
            'pace': float,
            'fga': int,
            'fta': int,
            'turnovers': int,
            'offensive_rebounds': int,
            'fg3a': int,
            'fg3m': int,
            'fg3_pct': float
        }
        None if not found
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            pace,
            fga,
            fta,
            turnovers,
            offensive_rebounds,
            fg3a,
            fg3m,
            fg3_pct
        FROM team_game_logs
        WHERE game_id = ? AND team_id = ?
    """, (game_id, team_id))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'pace': row['pace'],
            'fga': row['fga'],
            'fta': row['fta'],
            'turnovers': row['turnovers'],
            'offensive_rebounds': row['offensive_rebounds'],
            'fg3a': row['fg3a'],
            'fg3m': row['fg3m'],
            'fg3_pct': row['fg3_pct']
        }
    return None


def get_completed_games_with_actuals(season: str = '2025-26', limit: Optional[int] = None) -> List[Dict]:
    """
    Get all completed games with actual total points for evaluation.

    This is used to evaluate model performance across multiple games.

    Args:
        season: NBA season (e.g., '2025-26')
        limit: Optional limit on number of games returned

    Returns:
        List of dicts with game_id, game_date, home_team_id, away_team_id,
        home_score, away_score, actual_total_points

    Example:
        >>> games = get_completed_games_with_actuals('2025-26', limit=100)
        >>> for game in games:
        >>>     predicted = predict_game_total(game['game_id'])
        >>>     actual = game['actual_total_points']
        >>>     error = abs(predicted - actual)
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            id as game_id,
            game_date,
            home_team_id,
            away_team_id,
            home_score,
            away_score,
            actual_total_points
        FROM games
        WHERE season = ?
          AND status = 'final'
          AND actual_total_points IS NOT NULL
        ORDER BY game_date DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query, (season,))

    games = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return games
