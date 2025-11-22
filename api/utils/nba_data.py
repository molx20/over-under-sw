"""
NBA API wrapper functions with caching and error handling
"""
from nba_api.stats.endpoints import (
    leaguegamefinder,
    teamdashboardbygeneralsplits,
    teamgamelog,
    commonteamroster,
)
from nba_api.stats.static import teams
from datetime import datetime, timedelta
import pandas as pd
import time
import requests
from functools import wraps

# ============================================================================
# HTTP SESSION WITH CONNECTION POOLING
# ============================================================================

# Create a persistent session for HTTP keep-alive and connection pooling
# This reduces latency by reusing TCP connections and SSL sessions
_http_session = requests.Session()
_http_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
})

# Configure connection pool
# - pool_connections: Number of connection pools to cache
# - pool_maxsize: Maximum number of connections to save in the pool
from requests.adapters import HTTPAdapter
adapter = HTTPAdapter(
    pool_connections=10,  # Number of connection pools
    pool_maxsize=20,      # Max connections per pool
    max_retries=2,        # Retry failed requests
    pool_block=False      # Don't block when pool is full
)
_http_session.mount('https://', adapter)
_http_session.mount('http://', adapter)

# ============================================================================
# CACHING WRAPPER (LRU with memory limits)
# ============================================================================

# Import bounded LRU cache manager
try:
    from api.utils.cache_manager import cached, get_cache_stats, clear_cache
except ImportError:
    from cache_manager import cached, get_cache_stats, clear_cache

_last_game_date = None  # Track the last date we fetched games for

def clear_games_cache():
    """
    Clear only the games cache (when date changes at 3 AM MST).
    Note: With new LRU cache, we clear all cache for simplicity.
    Individual key clearing could be added if needed.
    """
    clear_cache()
    print("[cache] Cleared games cache")

def cache_result(timeout_seconds=3600):
    """
    Decorator to cache function results with LRU eviction.
    This replaces the old unbounded cache.
    """
    return cached(ttl_seconds=timeout_seconds)

def safe_api_call(func):
    """Decorator to add error handling and retries to API calls"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        retry_delay = 1.0  # Start with 1 second

        for attempt in range(max_retries):
            try:
                # Add minimal delay to respect rate limits (50ms)
                time.sleep(0.05)
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error_msg = str(e)

                if attempt < max_retries - 1:
                    # Retry on timeout or connection errors
                    if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower():
                        print(f"API Error in {func.__name__} (attempt {attempt + 1}/{max_retries}): {error_msg}")
                        print(f"Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue

                # Final attempt failed or non-retryable error
                print(f"API Error in {func.__name__}: {error_msg}")
                return None

        return None
    return wrapper

# ============================================================================
# TEAM DATA FUNCTIONS
# ============================================================================

def get_all_teams():
    """Get list of all NBA teams with IDs"""
    return teams.get_teams()

def get_team_id(team_name):
    """Get team ID by name (e.g., 'Lakers', 'Nets')"""
    all_teams = teams.get_teams()
    team = [t for t in all_teams if team_name.lower() in t['full_name'].lower() or
            team_name.lower() in t['nickname'].lower()]
    return team[0]['id'] if team else None

@cache_result(timeout_seconds=14400)  # 4 hours - stats don't change often
@safe_api_call
def get_team_stats(team_id, season='2025-26', per_mode='PerGame'):
    """
    Get team traditional stats with home/away splits
    Using 2025-26 season data (current season)

    Args:
        team_id: NBA team ID
        season: Season (e.g., '2025-26')
        per_mode: 'PerGame', 'Totals', or 'Per100Possessions'

    Returns:
        dict with overall, home, and away stats
    """
    dashboard = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
        team_id=team_id,
        season=season,
        per_mode_detailed=per_mode,
        measure_type_detailed_defense='Base'
    )

    # Get overall, home, and away splits
    splits = dashboard.get_data_frames()[0]

    if len(splits) == 0:
        return {
            'overall': {},
            'home': {},
            'away': {}
        }

    # API returns different GROUP_VALUE formats depending on parameters
    # Try to find 'Overall', 'Home', 'Road' first, otherwise use first row as overall
    overall_data = splits[splits['GROUP_VALUE'] == 'Overall']
    if len(overall_data) == 0:
        # If no 'Overall' found, use first row (likely season year like '2023-24')
        overall = splits.iloc[0].to_dict() if len(splits) > 0 else {}
    else:
        overall = overall_data.to_dict('records')[0]

    home_data = splits[splits['GROUP_VALUE'] == 'Home']
    home = home_data.to_dict('records')[0] if len(home_data) > 0 else {}

    away_data = splits[splits['GROUP_VALUE'] == 'Road']
    away = away_data.to_dict('records')[0] if len(away_data) > 0 else {}

    return {
        'overall': overall,
        'home': home,
        'away': away
    }

@cache_result(timeout_seconds=14400)  # 4 hours
@safe_api_call
def get_team_advanced_stats(team_id, season='2025-26'):
    """
    Get team advanced stats (ORTG, DRTG, PACE, etc.)
    """
    dashboard = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
        team_id=team_id,
        season=season,
        measure_type_detailed_defense='Advanced'
    )

    splits = dashboard.get_data_frames()[0]

    if len(splits) == 0:
        return {}

    # Try to find 'Overall' first, otherwise use first row
    overall_data = splits[splits['GROUP_VALUE'] == 'Overall']
    if len(overall_data) == 0:
        overall = splits.iloc[0].to_dict() if len(splits) > 0 else {}
    else:
        overall = overall_data.to_dict('records')[0]

    return overall

@cache_result(timeout_seconds=14400)  # 4 hours
@safe_api_call
def get_team_opponent_stats(team_id, season='2025-26'):
    """
    Get opponent stats (what opponents score against this team)
    NOTE: Opponent endpoint returns TOTAL stats, so we convert to per-game
    """
    dashboard = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
        team_id=team_id,
        season=season,
        measure_type_detailed_defense='Opponent'
    )

    splits = dashboard.get_data_frames()[0]

    if len(splits) == 0:
        return {}

    # Try to find 'Overall' first, otherwise use first row
    overall_data = splits[splits['GROUP_VALUE'] == 'Overall']
    if len(overall_data) == 0:
        overall = splits.iloc[0].to_dict() if len(splits) > 0 else {}
    else:
        overall = overall_data.to_dict('records')[0]

    # Convert total stats to per-game stats
    gp = overall.get('GP', 1)  # Games played
    if gp > 0:
        # Convert counting stats to per-game averages
        for key in overall.keys():
            if key.startswith('OPP_') and key not in ['OPP_FG_PCT', 'OPP_FG3_PCT', 'OPP_FT_PCT'] and not key.endswith('_RANK'):
                if isinstance(overall[key], (int, float)) and overall[key] != 0:
                    overall[key] = overall[key] / gp

    return overall

@cache_result(timeout_seconds=14400)  # 4 hours
@safe_api_call
def get_team_last_n_games(team_id, n=5, season='2025-26'):
    """
    Get team's last N games
    """
    gamelog = teamgamelog.TeamGameLog(
        team_id=team_id,
        season=season
    )

    games = gamelog.get_data_frames()[0]
    return games.head(n).to_dict('records') if len(games) > 0 else []

# ============================================================================
# GAME SCHEDULE FUNCTIONS
# ============================================================================

def is_2025_26_season_game(game_id):
    """
    Check if a game ID corresponds to the 2025-26 NBA season.

    NBA game IDs follow the format: 00[Season][GameNumber]
    - Season 2025-26 uses ID: 225 (25 from 2025, 26 truncated to last digit)
    - Regular season games: 0022500001, 0022500002, etc.
    - Preseason: 0012500001, etc.
    - Playoffs would be: 0042500001, etc.

    Args:
        game_id: NBA game ID string or int

    Returns:
        bool: True if game is from 2025-26 season
    """
    game_id_str = str(game_id)

    # Check if game ID starts with season prefix for 2025-26
    # Preseason (01), Regular season (02), All-Star (03), Playoffs (04)
    valid_prefixes = [
        '001225',  # Preseason 2025-26
        '0022500',  # Regular season 2025-26 (with extra digit)
        '002250',   # Regular season 2025-26 (alternate format)
        '00225',    # Regular season 2025-26 (base)
        '003225',   # All-Star 2025-26
        '004225',   # Playoffs 2025-26
    ]

    return any(game_id_str.startswith(prefix) for prefix in valid_prefixes)


@cache_result(timeout_seconds=300)  # 5 minutes - shorter cache for faster updates
def get_todays_games():
    """
    Get all games scheduled for today from the 2025-26 season

    Uses NBA CDN endpoint which is more reliable than stats.nba.com
    The CDN always returns the current day's games.

    Returns:
        list of dicts with game info, filtered to 2025-26 season only
    """
    # Use Mountain Time for date tracking
    global _last_game_date
    from datetime import timezone, timedelta
    mst_offset = timedelta(hours=-7)  # MST (UTC-7)
    mst_time = datetime.now(timezone.utc) + mst_offset
    today_str = mst_time.strftime('%Y-%m-%d')

    # Clear cache if date changed
    if _last_game_date is not None and _last_game_date != today_str:
        print(f"Date changed from {_last_game_date} to {today_str}, clearing cache")
        clear_games_cache()
    _last_game_date = today_str

    print(f"Fetching today's games (MST time: {mst_time.strftime('%Y-%m-%d %I:%M %p')})")

    # Still use ET offset for game time display (NBA standard)
    et_offset = timedelta(hours=-5)  # EST (UTC-5)

    try:
        # Minimal delay for CDN endpoint
        time.sleep(0.05)

        # Use NBA CDN endpoint - more reliable and rarely blocked
        # This endpoint provides today's scoreboard in JSON format
        url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"

        # Use persistent session for HTTP keep-alive (headers already configured)
        response = _http_session.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()

        # CDN structure: { "scoreboard": { "gameDate": "...", "games": [...] } }
        if not data or 'scoreboard' not in data:
            print("No scoreboard data in CDN response")
            return []

        scoreboard = data['scoreboard']
        games = scoreboard.get('games', [])

        if not games:
            print(f"No games found in CDN response for today")
            return []

        # Get all teams for lookups
        all_teams = get_all_teams()

        games_list = []
        filtered_count = 0

        for game in games:
            game_id = game.get('gameId', '')

            # FILTER: Only include 2025-26 season games
            if not is_2025_26_season_game(game_id):
                filtered_count += 1
                print(f"Filtered out game {game_id} - not 2025-26 season")
                continue

            # Extract game info from CDN format
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})

            home_team_id = home_team.get('teamId', 0)
            away_team_id = away_team.get('teamId', 0)

            # Get team data for abbreviations
            home_team_data = next((t for t in all_teams if t['id'] == home_team_id), None)
            away_team_data = next((t for t in all_teams if t['id'] == away_team_id), None)

            # Get game status
            game_status_text = game.get('gameStatusText', '')
            if not game_status_text:
                game_time_utc = game.get('gameTimeUTC', '')
                if game_time_utc:
                    # Parse and convert to ET
                    try:
                        from dateutil import parser
                        game_dt = parser.parse(game_time_utc)
                        game_et = game_dt.astimezone(timezone.utc) + et_offset
                        game_status_text = game_et.strftime('%-I:%M %p ET')
                    except:
                        game_status_text = game.get('gameStatus', 1)
                else:
                    game_status_text = game.get('gameStatus', 1)

            # Get scores
            home_score = home_team.get('score', 0)
            away_score = away_team.get('score', 0)

            games_list.append({
                'game_id': game_id,
                'game_date': scoreboard.get('gameDate', today_str),
                'game_status': game_status_text,
                'home_team_id': home_team_id,
                'home_team_name': home_team.get('teamTricode', home_team_data['abbreviation'] if home_team_data else 'UNK'),
                'home_team_score': home_score,
                'away_team_id': away_team_id,
                'away_team_name': away_team.get('teamTricode', away_team_data['abbreviation'] if away_team_data else 'UNK'),
                'away_team_score': away_score,
            })

        print(f"Successfully fetched {len(games_list)} game(s) for {today_str} (filtered {filtered_count} non-2025-26 games)")
        return games_list

    except requests.RequestException as e:
        print(f"HTTP Error fetching games from CDN: {str(e)}")
        # Fallback to empty list if CDN fails
        return []
    except Exception as e:
        print(f"Error in get_todays_games: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

@cache_result(timeout_seconds=1800)
@safe_api_call
def get_games_by_date(date_str):
    """
    Get games for a specific date

    Args:
        date_str: Date in format 'YYYY-MM-DD' or 'MM/DD/YYYY'
    """
    # Convert to NBA API format if needed
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    except:
        date_obj = datetime.strptime(date_str, '%m/%d/%Y')

    formatted_date = date_obj.strftime('%Y-%m-%d')

    scoreboard = scoreboardv2.ScoreboardV2(game_date=formatted_date)
    games = scoreboard.get_data_frames()[0]

    return games.to_dict('records')

# ============================================================================
# INJURY & ROSTER FUNCTIONS
# ============================================================================

@cache_result(timeout_seconds=7200)
@safe_api_call
def get_team_roster(team_id, season='2025-26'):
    """
    Get current team roster
    """
    roster = commonteamroster.CommonTeamRoster(
        team_id=team_id,
        season=season
    )

    players = roster.get_data_frames()[0]
    return players.to_dict('records') if len(players) > 0 else []

# ============================================================================
# HELPER FUNCTIONS FOR PREDICTIONS
# ============================================================================

def get_matchup_data(home_team_id, away_team_id, season='2025-26'):
    """
    Get all relevant data for a matchup prediction
    Using 2025-26 season data (current season)

    Returns comprehensive dict with all stats needed for O/U prediction.
    Now more resilient - provides partial data if some API calls fail.
    """
    print(f"Fetching matchup data for teams {home_team_id} vs {away_team_id} (Season: {season})")

    # Use threading to fetch data in parallel for faster loading
    import concurrent.futures

    def fetch_team_data(team_id):
        """Fetch team data with individual error handling for each stat type"""
        print(f"  Fetching stats for team {team_id}...")

        # Fetch each stat type independently - don't let one failure break everything
        stats = get_team_stats(team_id, season)
        if stats is None:
            print(f"  WARNING: Failed to fetch basic stats for team {team_id}")

        advanced = get_team_advanced_stats(team_id, season)
        if advanced is None:
            print(f"  WARNING: Failed to fetch advanced stats for team {team_id}")

        opponent = get_team_opponent_stats(team_id, season)
        if opponent is None:
            print(f"  WARNING: Failed to fetch opponent stats for team {team_id}")

        recent_games = get_team_last_n_games(team_id, n=10, season=season)
        if recent_games is None:
            print(f"  WARNING: Failed to fetch recent games for team {team_id}")
            recent_games = []  # Default to empty list

        return {
            'stats': stats,
            'advanced': advanced,
            'opponent': opponent,
            'recent_games': recent_games
        }

    # Fetch both teams in parallel with timeout protection
    # Railway has 10min limit, use 8min timeout to allow for processing
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_home = executor.submit(fetch_team_data, home_team_id)
            future_away = executor.submit(fetch_team_data, away_team_id)

            # Wait for results with 480-second timeout (8 minutes)
            home_data = future_home.result(timeout=480)
            away_data = future_away.result(timeout=480)

    except concurrent.futures.TimeoutError:
        print("ERROR: NBA API timeout - requests took longer than 8 minutes")
        print("This usually happens when the NBA API is extremely slow or down")
        print("Suggestion: Try again in 30-60 seconds or use cached data if available")
        return None
    except Exception as e:
        print(f"ERROR: Exception while fetching team data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

    # Validate that we got at least basic data
    if not home_data or not away_data:
        print("ERROR: Failed to fetch team data structures")
        return None

    # Check if CRITICAL stats are missing (overall stats needed for prediction)
    home_stats = home_data.get('stats')
    away_stats = away_data.get('stats')

    if home_stats is None or away_stats is None:
        print("ERROR: Critical team stats API calls failed")
        print(f"  Home stats: {'✓' if home_stats else '✗'}")
        print(f"  Away stats: {'✓' if away_stats else '✗'}")
        return None

    # Log what we successfully fetched
    home_complete = all([
        home_data.get('stats'),
        home_data.get('advanced'),
        home_data.get('opponent'),
        home_data.get('recent_games')
    ])
    away_complete = all([
        away_data.get('stats'),
        away_data.get('advanced'),
        away_data.get('opponent'),
        away_data.get('recent_games')
    ])

    if home_complete and away_complete:
        print("✓ Successfully fetched complete matchup data")
    else:
        print("⚠ Fetched partial matchup data (some stats missing but prediction can continue)")

    return {
        'home': home_data,
        'away': away_data,
        'season_used': season
    }

# ============================================================================
# BATCH OPERATIONS (with rate limiting)
# ============================================================================

def batch_fetch_teams(team_ids, season='2025-26'):
    """
    Fetch stats for multiple teams with proper rate limiting
    """
    results = {}
    for team_id in team_ids:
        print(f"Fetching data for team {team_id}...")
        results[team_id] = {
            'stats': get_team_stats(team_id, season),
            'advanced': get_team_advanced_stats(team_id, season),
            'opponent': get_team_opponent_stats(team_id, season),
        }
        # Delay is handled by @safe_api_call decorator
    return results

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clear_cache():
    """Clear all cached data (useful for testing)"""
    global _cache, _cache_timeout
    _cache = {}
    _cache_timeout = {}
    print("Cache cleared")

def get_cache_info():
    """Get information about cached items"""
    return {
        'cached_items': len(_cache),
        'cache_keys': list(_cache.keys())[:10]  # Show first 10 keys
    }
