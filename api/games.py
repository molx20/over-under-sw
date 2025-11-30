"""
API endpoint to get today's games with predictions
"""
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
from datetime import datetime, timezone
import sys
import os

# Add the api directory to path
sys.path.append(os.path.dirname(__file__))

# Initialize NBA data database if it doesn't exist (Railway deployment)
try:
    from utils.init_db_on_startup import init_nba_data_db_if_needed
    init_nba_data_db_if_needed()
except Exception as e:
    print(f"Warning: Could not initialize NBA data DB: {e}")

from utils.db_queries import get_todays_games, get_matchup_data, get_all_teams
from utils.prediction_engine import predict_game_total

# In-memory prediction cache for serverless function instance
# Cache key: (home_team_id, away_team_id, betting_line)
# This provides fast responses for concurrent/repeat requests within function lifetime
_prediction_cache = {}
_CACHE_MAX_SIZE = 128

def get_cached_prediction(home_team_id, away_team_id, betting_line):
    """
    Get prediction from cache or generate new one

    Args:
        home_team_id: Home team ID
        away_team_id: Away team ID
        betting_line: Betting line (can be None)

    Returns:
        Prediction dictionary or None on error
    """
    cache_key = (int(home_team_id), int(away_team_id), betting_line)

    # Check cache
    if cache_key in _prediction_cache:
        print(f'[cache] HIT: Returning cached prediction for game {away_team_id}@{home_team_id} (line: {betting_line})')
        return _prediction_cache[cache_key]

    print(f'[cache] MISS: Generating prediction for game {away_team_id}@{home_team_id} (line: {betting_line})')

    # Get matchup data (this has its own 4-hour cache)
    matchup_data = get_matchup_data(home_team_id, away_team_id)
    if matchup_data is None:
        print('[cache] ERROR: Failed to fetch matchup data')
        return None

    # Generate prediction
    prediction = predict_game_total(
        matchup_data['home'],
        matchup_data['away'],
        betting_line
    )

    # Store in cache with simple FIFO eviction
    if len(_prediction_cache) >= _CACHE_MAX_SIZE:
        # Remove oldest entry (first inserted)
        oldest_key = next(iter(_prediction_cache))
        print(f'[cache] EVICT: Removing oldest entry {oldest_key}')
        _prediction_cache.pop(oldest_key)

    _prediction_cache[cache_key] = prediction
    print(f'[cache] STORE: Cached prediction for {cache_key}')

    return prediction


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        try:
            # Parse URL
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            query_params = parse_qs(parsed_path.query)

            # Route based on query params - if game_id is present, it's a game detail request
            if 'game_id' in query_params:
                self.handle_game_detail(query_params)
            else:
                # Default to games list
                self.handle_games(query_params)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_response(500, str(e))

    def handle_games(self, query_params):
        """Get all games for today with predictions"""
        try:
            print('[games] Fetching today\'s games from NBA API...')
            # Get games
            games = get_todays_games()

            if games is None:
                print('[games] ERROR: NBA API returned None')
                self.send_error_response(500, 'Failed to fetch games from NBA API')
                return

            print(f'[games] Successfully fetched {len(games)} games')

            # Format games for response (no predictions on list view for speed)
            # Predictions will be generated on-demand when viewing game details
            games_with_predictions = []
            for game in games:
                games_with_predictions.append({
                    'game_id': game['game_id'],
                    'home_team': {
                        'id': game['home_team_id'],
                        'name': game['home_team_name'],
                        'abbreviation': game['home_team_name'],
                        'score': game['home_team_score'],
                    },
                    'away_team': {
                        'id': game['away_team_id'],
                        'name': game['away_team_name'],
                        'abbreviation': game['away_team_name'],
                        'score': game['away_team_score'],
                    },
                    'game_time': game['game_status'],
                    'game_status': game['game_status'],
                    'prediction': None,  # Will be fetched on game detail page
                })

            # Use Mountain Time for consistency with NBA game schedules
            # NBA games are dated in US timezones, not UTC
            from datetime import timedelta
            mountain_tz = timezone(timedelta(hours=-7))  # MST (UTC-7)
            mt_time = datetime.now(mountain_tz)

            response = {
                'success': True,
                'date': mt_time.strftime('%Y-%m-%d'),
                'games': games_with_predictions,
                'count': len(games_with_predictions),
                'last_updated': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
            }

            # Cache at CDN edge: fresh for 30s, stale-while-revalidate for 5min
            self.send_json_response(response, cache_control='public, s-maxage=30, stale-while-revalidate=300')

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_response(500, str(e))

    def handle_game_detail(self, query_params):
        """Get detailed game information"""
        try:
            # Get parameters
            game_id = query_params.get('game_id', [None])[0]

            if not game_id:
                print('[game_detail] ERROR: Missing game_id parameter')
                self.send_error_response(400, 'Missing game_id parameter')
                return

            print(f'[game_detail] Fetching detail for game {game_id}')

            # Find the game in today's games
            games = get_todays_games()

            if not games:
                print('[game_detail] ERROR: No games available from NBA API')
                self.send_error_response(404, 'No games available today')
                return

            game = next((g for g in games if str(g.get('game_id')) == str(game_id)), None)

            if not game:
                print(f'[game_detail] ERROR: Game {game_id} not found in today\'s games')
                self.send_error_response(404, f'Game {game_id} not found')
                return

            print(f'[game_detail] Found game: {game.get("away_team_name")} @ {game.get("home_team_name")}')

            home_team_id = game['home_team_id']
            away_team_id = game['away_team_id']

            # Get betting line
            betting_line_str = query_params.get('betting_line', [None])[0]
            betting_line = float(betting_line_str) if betting_line_str else None

            # Get cached prediction (or generate new one)
            print(f'[game_detail] Fetching prediction for teams {home_team_id} vs {away_team_id} (betting_line: {betting_line})')
            prediction = get_cached_prediction(int(home_team_id), int(away_team_id), betting_line)

            if prediction is None:
                print('[game_detail] ERROR: Failed to generate prediction')
                self.send_error_response(500, 'The NBA API is currently slow or unavailable. Please try again in a moment. If this persists, the stats API may be experiencing issues.')
                return

            print(f'[game_detail] Prediction ready: {prediction.get("recommendation")} ({prediction.get("confidence")}% confidence)')

            # Get matchup data for stats display (will use existing cache)
            matchup_data = get_matchup_data(int(home_team_id), int(away_team_id))

            if matchup_data is None:
                print('[game_detail] ERROR: Failed to fetch matchup data for stats display')
                self.send_error_response(500, 'Failed to fetch game stats')
                return

            # Get team info
            all_teams = get_all_teams()
            home_team_info = next((t for t in all_teams if t['id'] == int(home_team_id)), {})
            away_team_info = next((t for t in all_teams if t['id'] == int(away_team_id)), {})

            # Safely extract stats
            home_overall = matchup_data['home']['stats'].get('overall', {}) if matchup_data['home'].get('stats') else {}
            away_overall = matchup_data['away']['stats'].get('overall', {}) if matchup_data['away'].get('stats') else {}
            home_adv = matchup_data['home'].get('advanced') or {}
            away_adv = matchup_data['away'].get('advanced') or {}
            home_opp = matchup_data['home'].get('opponent') or {}
            away_opp = matchup_data['away'].get('opponent') or {}

            response = {
                'success': True,
                'home_team': {
                    'id': home_team_id,
                    'name': home_team_info.get('full_name', 'Home Team'),
                    'abbreviation': home_team_info.get('abbreviation', 'HOM'),
                },
                'away_team': {
                    'id': away_team_id,
                    'name': away_team_info.get('full_name', 'Away Team'),
                    'abbreviation': away_team_info.get('abbreviation', 'AWY'),
                },
                'prediction': prediction,
                'home_stats': {
                    'overall': {
                        'ppg': round(home_overall.get('PTS', 0), 1),
                        'fg_pct': round(home_overall.get('FG_PCT', 0) * 100, 1),
                        'fg3_pct': round(home_overall.get('FG3_PCT', 0) * 100, 1),
                        'ft_pct': round(home_overall.get('FT_PCT', 0) * 100, 1),
                        'opp_ppg': round(home_opp.get('OPP_PTS', 0), 1),
                        'wins': home_overall.get('W', 0),
                        'losses': home_overall.get('L', 0),
                        'ortg': round(home_adv.get('OFF_RATING', 0), 1),
                        'drtg': round(home_adv.get('DEF_RATING', 0), 1),
                        'pace': round(home_adv.get('PACE', 0), 1),
                        'net_rtg': round(home_adv.get('NET_RATING', 0), 1),
                    }
                },
                'away_stats': {
                    'overall': {
                        'ppg': round(away_overall.get('PTS', 0), 1),
                        'fg_pct': round(away_overall.get('FG_PCT', 0) * 100, 1),
                        'fg3_pct': round(away_overall.get('FG3_PCT', 0) * 100, 1),
                        'ft_pct': round(away_overall.get('FT_PCT', 0) * 100, 1),
                        'opp_ppg': round(away_opp.get('OPP_PTS', 0), 1),
                        'wins': away_overall.get('W', 0),
                        'losses': away_overall.get('L', 0),
                        'ortg': round(away_adv.get('OFF_RATING', 0), 1),
                        'drtg': round(away_adv.get('DEF_RATING', 0), 1),
                        'pace': round(away_adv.get('PACE', 0), 1),
                        'net_rtg': round(away_adv.get('NET_RATING', 0), 1),
                    }
                },
                'home_recent_games': [
                    {
                        'matchup': game.get('MATCHUP', ''),
                        'total': game.get('PTS', 0),
                        'result': game.get('WL', ''),
                    }
                    for game in matchup_data['home'].get('recent_games', [])[:5]
                ],
                'away_recent_games': [
                    {
                        'matchup': game.get('MATCHUP', ''),
                        'total': game.get('PTS', 0),
                        'result': game.get('WL', ''),
                    }
                    for game in matchup_data['away'].get('recent_games', [])[:5]
                ],
            }

            # Cache at CDN edge: fresh for 30s, stale-while-revalidate for 5min
            self.send_json_response(response, cache_control='public, s-maxage=30, stale-while-revalidate=300')

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_response(500, str(e))

    def send_json_response(self, data, status_code=200, cache_control=None):
        """Send JSON response with optional cache control"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')

        # Add cache control headers for CDN caching
        if cache_control:
            self.send_header('Cache-Control', cache_control)

        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_error_response(self, status_code, error_message):
        """Send error response"""
        response = {
            'success': False,
            'error': error_message
        }
        self.send_json_response(response, status_code)
