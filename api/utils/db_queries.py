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
from datetime import datetime
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
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

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
        }
        for row in rows
    ]

# ============================================================================
# TODAY'S GAMES QUERIES
# ============================================================================

def get_todays_games(season: str = '2024-25') -> List[Dict]:
    """
    Get all games scheduled for today

    Returns:
        List of game dicts with game_id, home_team_id, away_team_id, scores, status
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Get today's date in US Mountain Time (NBA schedules use US timezones)
    from datetime import timezone, timedelta
    mountain_tz = timezone(timedelta(hours=-7))  # MST (UTC-7)
    today = datetime.now(mountain_tz).strftime('%Y-%m-%d')

    cursor.execute('''
        SELECT *
        FROM todays_games
        WHERE game_date = ? AND season = ?
        ORDER BY game_time_utc
    ''', (today, season))

    rows = cursor.fetchall()
    conn.close()

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
                    season: str = '2024-25') -> Optional[Dict]:
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
