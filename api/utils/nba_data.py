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
# CACHING WRAPPER (to avoid rate limits)
# ============================================================================

_cache = {}
_cache_timeout = {}

def cache_result(timeout_seconds=3600):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            current_time = time.time()

            # Check if cached and not expired
            if cache_key in _cache and cache_key in _cache_timeout:
                if current_time - _cache_timeout[cache_key] < timeout_seconds:
                    print(f"Cache hit for {func.__name__}")
                    return _cache[cache_key]

            # Call function and cache result
            print(f"Cache miss for {func.__name__}, fetching from API...")
            result = func(*args, **kwargs)
            _cache[cache_key] = result
            _cache_timeout[cache_key] = current_time

            return result
        return wrapper
    return decorator

def safe_api_call(func):
    """Decorator to add error handling to API calls"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Add delay to respect rate limits (100ms for faster loads)
            time.sleep(0.1)
            return func(*args, **kwargs)
        except Exception as e:
            print(f"API Error in {func.__name__}: {str(e)}")
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

@cache_result(timeout_seconds=3600)
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

@cache_result(timeout_seconds=3600)
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

@cache_result(timeout_seconds=3600)
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

@cache_result(timeout_seconds=3600)
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

@cache_result(timeout_seconds=1800)
def get_todays_games():
    """
    Get all games scheduled for today
    Uses direct HTTP request to avoid nba_api ScoreboardV2 bug

    Returns:
        list of dicts with game info
    """
    today = datetime.now().strftime('%m/%d/%Y')

    try:
        # Add delay to respect rate limits
        time.sleep(0.2)

        # Direct HTTP request to NBA Stats API
        url = "https://stats.nba.com/stats/scoreboardv2"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.nba.com/',
            'Origin': 'https://www.nba.com',
        }
        params = {
            'GameDate': today,
            'LeagueID': '00',
            'DayOffset': '0'
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        # The structure is: resultSets -> [GameHeader, LineScore, etc.]
        if not data or 'resultSets' not in data:
            print("No result sets in scoreboard response")
            return []

        result_sets = data['resultSets']

        # Find GameHeader and LineScore
        game_header = None
        line_score = None

        for rs in result_sets:
            if rs['name'] == 'GameHeader':
                game_header = rs
            elif rs['name'] == 'LineScore':
                line_score = rs

        if not game_header or not game_header['rowSet']:
            print(f"No games scheduled for {today}")
            return []

        # Get column indices for GameHeader
        gh_headers = game_header['headers']
        game_id_idx = gh_headers.index('GAME_ID')
        game_date_idx = gh_headers.index('GAME_DATE_EST')
        game_status_idx = gh_headers.index('GAME_STATUS_TEXT')
        home_team_id_idx = gh_headers.index('HOME_TEAM_ID')
        visitor_team_id_idx = gh_headers.index('VISITOR_TEAM_ID')

        # Get column indices for LineScore if available
        score_map = {}
        if line_score and line_score['rowSet']:
            ls_headers = line_score['headers']
            ls_game_id_idx = ls_headers.index('GAME_ID')
            ls_team_id_idx = ls_headers.index('TEAM_ID')
            ls_pts_idx = ls_headers.index('PTS')

            # Build a map of game_id -> team_id -> points
            for row in line_score['rowSet']:
                gid = row[ls_game_id_idx]
                tid = row[ls_team_id_idx]
                pts = row[ls_pts_idx] if row[ls_pts_idx] is not None else 0
                if gid not in score_map:
                    score_map[gid] = {}
                score_map[gid][tid] = int(pts) if isinstance(pts, (int, float)) else 0

        # Get all teams for lookups
        all_teams = get_all_teams()

        games_list = []
        for game_row in game_header['rowSet']:
            game_id = game_row[game_id_idx]
            home_team_id = int(game_row[home_team_id_idx])
            away_team_id = int(game_row[visitor_team_id_idx])

            # Get team abbreviations
            home_team_data = next((t for t in all_teams if t['id'] == home_team_id), None)
            away_team_data = next((t for t in all_teams if t['id'] == away_team_id), None)

            # Get scores from score_map
            home_score = score_map.get(game_id, {}).get(home_team_id, 0)
            away_score = score_map.get(game_id, {}).get(away_team_id, 0)

            games_list.append({
                'game_id': game_id,
                'game_date': game_row[game_date_idx],
                'game_status': game_row[game_status_idx],
                'home_team_id': home_team_id,
                'home_team_name': home_team_data['abbreviation'] if home_team_data else 'UNK',
                'home_team_score': home_score,
                'away_team_id': away_team_id,
                'away_team_name': away_team_data['abbreviation'] if away_team_data else 'UNK',
                'away_team_score': away_score,
            })

        print(f"Successfully fetched {len(games_list)} game(s) for {today}")
        return games_list

    except requests.RequestException as e:
        print(f"HTTP Error fetching games: {str(e)}")
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

    Returns comprehensive dict with all stats needed for O/U prediction
    """
    print(f"Fetching matchup data for teams {home_team_id} vs {away_team_id} (Season: {season})")

    # Use threading to fetch data in parallel for faster loading
    import concurrent.futures

    def fetch_team_data(team_id):
        return {
            'stats': get_team_stats(team_id, season),
            'advanced': get_team_advanced_stats(team_id, season),
            'opponent': get_team_opponent_stats(team_id, season),
            'recent_games': []  # Skip recent games for speed (historical data anyway)
        }

    # Fetch both teams in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_home = executor.submit(fetch_team_data, home_team_id)
        future_away = executor.submit(fetch_team_data, away_team_id)

        home_data = future_home.result()
        away_data = future_away.result()

    # Validate that critical data was fetched successfully
    if not home_data or not away_data:
        print("ERROR: Failed to fetch team data")
        return None

    # Check if stats are missing (API calls failed)
    if home_data.get('stats') is None or away_data.get('stats') is None:
        print("ERROR: Team stats API calls failed")
        return None

    # Warn if advanced stats are missing (not critical, but impacts prediction quality)
    if home_data.get('advanced') is None or away_data.get('advanced') is None:
        print("WARNING: Advanced stats API calls failed - prediction quality may be reduced")

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
