"""
Team Statistics Rankings Module

This module calculates and caches league rankings for team statistics.
Rankings are based on 2025-26 season data and cached in SQLite for performance.

RANKING RULES:
- Rank 1 is always "best"
- For offensive stats (PPG, FG%, 3P%, FT%, OFF RTG, NET RTG, PACE): HIGHER is better
- For defensive stats (OPP PPG, DEF RTG): LOWER is better

Example: If a team has the highest PPG, they get rank 1.
         If a team has the lowest OPP PPG (fewest points allowed), they get rank 1.
"""

from datetime import datetime, timedelta
import sqlite3
import os
import threading
from typing import Dict, List, Optional
from api.utils.db_queries import get_all_teams, get_matchup_data

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
except ImportError:
    try:
        from db_config import get_db_path
    except ImportError:
        # Fallback for standalone execution
        get_db_path = None

# Database path for rankings cache (now uses centralized config)
DB_PATH = get_db_path('team_rankings.db') if get_db_path else os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'data', 'team_rankings.db'
)

# Import connection pool
try:
    from api.utils.connection_pool import get_db_pool
except ImportError:
    try:
        from connection_pool import get_db_pool
    except ImportError:
        # Fallback for standalone execution
        get_db_pool = None

# Background refresh state
_refresh_thread = None
_refresh_lock = threading.Lock()


def _get_connection():
    """Get database connection (pooled if available, direct otherwise)."""
    if get_db_pool:
        pool = get_db_pool('team_rankings')
        return pool.get_connection()
    else:
        # Fallback for standalone execution
        class DirectConnection:
            def __enter__(self):
                os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
                self.conn = sqlite3.connect(DB_PATH)
                self.conn.row_factory = sqlite3.Row
                return self.conn
            def __exit__(self, *args):
                self.conn.close()
        return DirectConnection()


def init_rankings_db():
    """Initialize the rankings cache database"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with _get_connection() as conn:
        cursor = conn.cursor()

        # Create rankings cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_rankings (
                team_id INTEGER PRIMARY KEY,
                team_abbreviation TEXT NOT NULL,
                season TEXT NOT NULL,

                -- Raw stat values
                ppg REAL,
                opp_ppg REAL,
                fg_pct REAL,
                three_pct REAL,
                ft_pct REAL,
                off_rtg REAL,
                def_rtg REAL,
                net_rtg REAL,
                pace REAL,

                -- Rankings (1 = best)
                ppg_rank INTEGER,
                opp_ppg_rank INTEGER,
                fg_pct_rank INTEGER,
                three_pct_rank INTEGER,
                ft_pct_rank INTEGER,
                off_rtg_rank INTEGER,
                def_rtg_rank INTEGER,
                net_rtg_rank INTEGER,
                pace_rank INTEGER,

                -- Cache metadata
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Index for fast lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_team_season
            ON team_rankings(team_id, season)
        ''')

        conn.commit()


def should_refresh_rankings(season: str = '2025-26') -> bool:
    """
    Check if rankings cache needs to be refreshed

    Refresh if:
    - No data exists
    - Data is older than 6 hours (stats change after games)
    - Season doesn't match
    """
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT updated_at, COUNT(*) as team_count
                FROM team_rankings
                WHERE season = ?
                GROUP BY updated_at
                ORDER BY updated_at DESC
                LIMIT 1
            ''', (season,))

            result = cursor.fetchone()

            if not result or result[1] < 20:  # Need at least 20 teams
                return True

            # Check if data is older than 6 hours
            last_update = datetime.fromisoformat(result[0])
            age = datetime.now() - last_update
            return age > timedelta(hours=6)

    except Exception as e:
        print(f'[team_rankings] Error checking cache freshness: {e}')
        return True


def calculate_rankings_from_api(season: str = '2025-26') -> List[Dict]:
    """
    Fetch all team stats from NBA API and calculate rankings

    Returns list of dicts with team stats and their rankings
    """
    print(f'[team_rankings] Calculating rankings for {season} season...')

    # Get all NBA teams
    all_teams = get_all_teams()
    if not all_teams:
        raise Exception('Failed to fetch teams from NBA API')

    print(f'[team_rankings] Fetching stats for {len(all_teams)} teams...')

    # Collect stats for all teams
    team_stats_list = []

    for team in all_teams:
        try:
            team_id = team['id']
            team_abbr = team['abbreviation']

            # Fetch matchup data (this gets us team stats)
            # We use a dummy opponent (just pick first team) since we only need one team's stats
            matchup_data = get_matchup_data(team_id, all_teams[0]['id'])

            if not matchup_data or 'home' not in matchup_data:
                print(f'[team_rankings] Warning: Failed to fetch stats for {team_abbr}')
                continue

            # Extract stats from the matchup data
            stats = matchup_data['home']['stats'].get('overall', {}) if matchup_data['home'].get('stats') else {}
            advanced = matchup_data['home'].get('advanced') or {}
            opponent = matchup_data['home'].get('opponent') or {}

            team_stats = {
                'team_id': team_id,
                'team_abbreviation': team_abbr,
                'season': season,
                'ppg': round(stats.get('PTS', 0), 1),
                'opp_ppg': round(opponent.get('OPP_PTS', 0), 1),
                'fg_pct': round(stats.get('FG_PCT', 0) * 100, 1),
                'three_pct': round(stats.get('FG3_PCT', 0) * 100, 1),
                'ft_pct': round(stats.get('FT_PCT', 0) * 100, 1),
                'off_rtg': round(advanced.get('OFF_RATING', 0), 1),
                'def_rtg': round(advanced.get('DEF_RATING', 0), 1),
                'net_rtg': round(advanced.get('NET_RATING', 0), 1),
                'pace': round(advanced.get('PACE', 0), 1),
            }

            team_stats_list.append(team_stats)

        except Exception as e:
            print(f'[team_rankings] Error fetching stats for team {team_id}: {e}')
            continue

    if len(team_stats_list) < 10:
        raise Exception(f'Failed to fetch enough team data (got {len(team_stats_list)}/30)')

    print(f'[team_rankings] Successfully fetched stats for {len(team_stats_list)} teams')

    # Calculate rankings for each stat
    # HIGHER is better: ppg, fg_pct, three_pct, ft_pct, off_rtg, net_rtg, pace
    # LOWER is better: opp_ppg, def_rtg

    stats_to_rank_high = ['ppg', 'fg_pct', 'three_pct', 'ft_pct', 'off_rtg', 'net_rtg', 'pace']
    stats_to_rank_low = ['opp_ppg', 'def_rtg']

    # Rank stats where higher is better
    for stat in stats_to_rank_high:
        # Sort descending (highest first)
        sorted_teams = sorted(team_stats_list, key=lambda x: x[stat], reverse=True)
        for rank, team in enumerate(sorted_teams, start=1):
            team[f'{stat}_rank'] = rank

    # Rank stats where lower is better
    for stat in stats_to_rank_low:
        # Sort ascending (lowest first)
        sorted_teams = sorted(team_stats_list, key=lambda x: x[stat])
        for rank, team in enumerate(sorted_teams, start=1):
            team[f'{stat}_rank'] = rank

    print(f'[team_rankings] Rankings calculated successfully')
    return team_stats_list


def save_rankings_to_cache(rankings: List[Dict]):
    """Save calculated rankings to SQLite cache"""
    print(f'[team_rankings] Saving {len(rankings)} team rankings to cache...')

    with _get_connection() as conn:
        cursor = conn.cursor()

        # Clear existing data for this season
        season = rankings[0]['season'] if rankings else '2025-26'
        cursor.execute('DELETE FROM team_rankings WHERE season = ?', (season,))

        # Insert new rankings
        for team in rankings:
            cursor.execute('''
                INSERT INTO team_rankings (
                    team_id, team_abbreviation, season,
                    ppg, opp_ppg, fg_pct, three_pct, ft_pct,
                    off_rtg, def_rtg, net_rtg, pace,
                    ppg_rank, opp_ppg_rank, fg_pct_rank, three_pct_rank, ft_pct_rank,
                    off_rtg_rank, def_rtg_rank, net_rtg_rank, pace_rank
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                team['team_id'], team['team_abbreviation'], team['season'],
                team['ppg'], team['opp_ppg'], team['fg_pct'], team['three_pct'], team['ft_pct'],
                team['off_rtg'], team['def_rtg'], team['net_rtg'], team['pace'],
                team['ppg_rank'], team['opp_ppg_rank'], team['fg_pct_rank'],
                team['three_pct_rank'], team['ft_pct_rank'],
                team['off_rtg_rank'], team['def_rtg_rank'], team['net_rtg_rank'], team['pace_rank']
            ))

        conn.commit()
        print(f'[team_rankings] Rankings saved to cache')


def get_team_rankings_from_cache(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """Get team rankings from cache"""
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT
                    team_id, team_abbreviation, season,
                    ppg, opp_ppg, fg_pct, three_pct, ft_pct, off_rtg, def_rtg, net_rtg, pace,
                    ppg_rank, opp_ppg_rank, fg_pct_rank, three_pct_rank, ft_pct_rank,
                    off_rtg_rank, def_rtg_rank, net_rtg_rank, pace_rank
                FROM team_rankings
                WHERE team_id = ? AND season = ?
            ''', (team_id, season))

            row = cursor.fetchone()

            if not row:
                return None

            return {
                'team_id': row[0],
                'team_abbreviation': row[1],
                'season': row[2],
                'stats': {
                    'ppg': {'value': row[3], 'rank': row[12]},
                    'opp_ppg': {'value': row[4], 'rank': row[13]},
                    'fg_pct': {'value': row[5], 'rank': row[14]},
                    'three_pct': {'value': row[6], 'rank': row[15]},
                    'ft_pct': {'value': row[7], 'rank': row[16]},
                    'off_rtg': {'value': row[8], 'rank': row[17]},
                    'def_rtg': {'value': row[9], 'rank': row[18]},
                    'net_rtg': {'value': row[10], 'rank': row[19]},
                    'pace': {'value': row[11], 'rank': row[20]},
                }
            }

    except Exception as e:
        print(f'[team_rankings] Error fetching from cache: {e}')
        return None


def _background_refresh_rankings(season: str):
    """Background task to refresh rankings (runs in separate thread)."""
    try:
        print(f'[team_rankings] Background refresh started for {season}')
        rankings = calculate_rankings_from_api(season)
        save_rankings_to_cache(rankings)
        print(f'[team_rankings] Background refresh completed for {season}')
    except Exception as e:
        print(f'[team_rankings] Background refresh failed: {e}')
    finally:
        global _refresh_thread
        with _refresh_lock:
            _refresh_thread = None


def refresh_rankings_if_needed(season: str = '2025-26', background: bool = True):
    """
    Refresh rankings cache if needed.

    Args:
        season: Season string (e.g. '2025-26')
        background: If True, refresh in background thread (serve stale data).
                    If False, refresh synchronously (blocks request).
    """
    global _refresh_thread

    if not should_refresh_rankings(season):
        print(f'[team_rankings] Using cached rankings')
        return

    if background:
        # Serve stale data while refreshing in background
        with _refresh_lock:
            if _refresh_thread is None or not _refresh_thread.is_alive():
                print(f'[team_rankings] Starting background refresh (serving stale data)')
                _refresh_thread = threading.Thread(
                    target=_background_refresh_rankings,
                    args=(season,),
                    daemon=True
                )
                _refresh_thread.start()
            else:
                print(f'[team_rankings] Background refresh already in progress')
    else:
        # Synchronous refresh (blocks request)
        print(f'[team_rankings] Synchronous refresh started')
        rankings = calculate_rankings_from_api(season)
        save_rankings_to_cache(rankings)


def get_team_stats_with_ranks(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get team stats with league rankings

    Args:
        team_id: NBA team ID
        season: Season string (e.g. '2025-26')

    Returns:
        Dict with team stats and rankings, or None if not found

    Example return:
        {
            'team_id': 1610612747,
            'team_abbreviation': 'LAL',
            'season': '2025-26',
            'stats': {
                'ppg': {'value': 111.7, 'rank': 18},
                'opp_ppg': {'value': 116.3, 'rank': 25},
                ...
            }
        }
    """
    # Initialize DB if needed
    init_rankings_db()

    # Refresh cache if needed (async-safe, uses file lock)
    refresh_rankings_if_needed(season)

    # Get from cache
    return get_team_rankings_from_cache(team_id, season)


# Initialize database on module import
init_rankings_db()
