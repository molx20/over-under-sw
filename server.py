"""
Flask server for NBA Over/Under predictor
Railway deployment
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timezone, timedelta
import sys
import os

# Add the api directory to path
sys.path.append(os.path.dirname(__file__))

from api.utils.nba_data import get_todays_games, get_matchup_data, get_all_teams
from api.utils.prediction_engine import predict_game_total
from api.utils import db
from api.utils import team_ratings_model
from api.utils import team_rankings
from api.utils.performance import create_timing_middleware
import json
import os

# Load model parameters on startup
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'api', 'data', 'model.json')
try:
    with open(MODEL_PATH, 'r') as f:
        model_params = json.load(f)
    print(f"[server] Loaded model parameters: version {model_params.get('version', 'unknown')}")
except Exception as e:
    print(f"[server] Warning: Could not load model.json: {e}")
    model_params = {
        'parameters': {'recent_games_n': 10},
        'feature_weights': {}
    }

app = Flask(__name__, static_folder='dist', static_url_path='')
CORS(app)

# Enable performance logging middleware
create_timing_middleware(app)

# Add cache control headers to prevent browser caching issues on deployment
@app.after_request
def add_cache_headers(response):
    """
    Add cache control headers to prevent stale frontend after deployments.

    Strategy:
    - index.html: No cache (always fetch fresh)
    - JS/CSS assets: Cache for 1 year (Vite adds hashes to filenames)
    - API responses: No cache (always fresh data)
    """
    # Don't cache index.html - always fetch fresh on reload
    if request.path == '/' or request.path.endswith('.html'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

    # Cache JS/CSS assets aggressively (Vite adds content hashes to filenames)
    elif request.path.endswith(('.js', '.css', '.woff', '.woff2', '.ttf', '.eot')):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'

    # Don't cache API responses
    elif request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

    # Images can be cached for a day
    elif request.path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico')):
        response.headers['Cache-Control'] = 'public, max-age=86400'

    return response

# Initialize database on startup
db.init_db()

# Self-learning disabled - using deterministic predictions
print("[startup] Running in deterministic mode (no automated learning)")

# Force WAL mode and verify connection health on all database pools
print("[startup] Initializing database connections...")
try:
    from api.utils.connection_pool import get_db_pool

    for db_name in ['predictions', 'team_rankings']:
        pool = get_db_pool(db_name)
        with pool.get_connection() as conn:
            # Force WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            # Verify connection is healthy
            conn.execute("SELECT 1")
            print(f"[startup] ✓ {db_name} database ready (WAL mode enabled)")
except Exception as e:
    print(f"[startup] Warning: Database initialization had issues: {e}")

# In-memory prediction cache
_prediction_cache = {}
_CACHE_MAX_SIZE = 128

def get_cached_prediction(home_team_id, away_team_id, betting_line):
    """
    Get prediction from cache or generate new one.

    Returns:
        tuple: (prediction_dict, matchup_data_dict) or (None, None) on error
    """
    cache_key = (int(home_team_id), int(away_team_id), betting_line)

    if cache_key in _prediction_cache:
        print(f'[cache] HIT: Returning cached prediction for game {away_team_id}@{home_team_id} (line: {betting_line})')
        cached_prediction, cached_matchup_data = _prediction_cache[cache_key]
        return cached_prediction, cached_matchup_data

    print(f'[cache] MISS: Generating prediction for game {away_team_id}@{home_team_id} (line: {betting_line})')

    matchup_data = get_matchup_data(home_team_id, away_team_id)
    if matchup_data is None:
        print('[cache] ERROR: Failed to fetch matchup data')
        return None, None

    # Get team abbreviations for trend analysis
    all_teams = get_all_teams()
    home_team_info = next((t for t in all_teams if t['id'] == int(home_team_id)), None)
    away_team_info = next((t for t in all_teams if t['id'] == int(away_team_id)), None)

    prediction = predict_game_total(
        matchup_data['home'],
        matchup_data['away'],
        betting_line,
        home_team_id=int(home_team_id),
        away_team_id=int(away_team_id),
        home_team_abbr=home_team_info['abbreviation'] if home_team_info else None,
        away_team_abbr=away_team_info['abbreviation'] if away_team_info else None,
        season='2025-26'
    )

    if len(_prediction_cache) >= _CACHE_MAX_SIZE:
        oldest_key = next(iter(_prediction_cache))
        print(f'[cache] EVICT: Removing oldest entry {oldest_key}')
        _prediction_cache.pop(oldest_key)

    # Cache both prediction and matchup_data to avoid duplicate API calls
    _prediction_cache[cache_key] = (prediction, matchup_data)
    print(f'[cache] STORE: Cached prediction and matchup data for {cache_key}')

    return prediction, matchup_data

@app.route('/')
def index():
    """Serve the React app"""
    return app.send_static_file('index.html')

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

@app.route('/api/games')
def get_games():
    """Get all games for today with predictions"""
    from api.utils.performance import log_slow_operation

    try:
        with log_slow_operation("Fetch today's games", threshold_ms=1000):
            print('[games] Fetching today\'s games from NBA API...')
            games = get_todays_games()

            if games is None:
                print('[games] ERROR: NBA API returned None')
                return jsonify({
                    'success': False,
                    'error': 'Failed to fetch games from NBA API'
                }), 500

            print(f'[games] Successfully fetched {len(games)} games')

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
                'prediction': None,
            })

        # Use MST for date display (matches game fetching logic)
        mst_offset = timedelta(hours=-7)
        mst_time = datetime.now(timezone.utc) + mst_offset

        # After 3 AM MST, show tomorrow's date
        if mst_time.hour >= 3:
            display_date = (mst_time + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            display_date = mst_time.strftime('%Y-%m-%d')

        response = {
            'success': True,
            'date': display_date,
            'games': games_with_predictions,
            'count': len(games_with_predictions),
            'last_updated': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        }

        # Add caching headers for faster subsequent loads
        resp = jsonify(response)
        resp.cache_control.max_age = 30  # Cache for 30 seconds in browser
        resp.cache_control.public = True
        return resp

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/game_detail')
def game_detail():
    """Get detailed game information"""
    try:
        game_id = request.args.get('game_id')

        if not game_id:
            print('[game_detail] ERROR: Missing game_id parameter')
            return jsonify({
                'success': False,
                'error': 'Missing game_id parameter'
            }), 400

        print(f'[game_detail] Fetching detail for game {game_id}')

        games = get_todays_games()

        if not games:
            print('[game_detail] ERROR: No games available from NBA API')
            return jsonify({
                'success': False,
                'error': 'No games available today'
            }), 404

        game = next((g for g in games if str(g.get('game_id')) == str(game_id)), None)

        if not game:
            print(f'[game_detail] ERROR: Game {game_id} not found in today\'s games')
            return jsonify({
                'success': False,
                'error': f'Game {game_id} not found'
            }), 404

        print(f'[game_detail] Found game: {game.get("away_team_name")} @ {game.get("home_team_name")}')

        home_team_id = game['home_team_id']
        away_team_id = game['away_team_id']

        betting_line_str = request.args.get('betting_line')
        betting_line = float(betting_line_str) if betting_line_str else None

        print(f'[game_detail] Fetching prediction for teams {home_team_id} vs {away_team_id} (betting_line: {betting_line})')
        prediction, matchup_data = get_cached_prediction(int(home_team_id), int(away_team_id), betting_line)

        if prediction is None or matchup_data is None:
            print('[game_detail] ERROR: Failed to generate prediction or fetch matchup data')
            return jsonify({
                'success': False,
                'error': 'The NBA API is currently slow or unavailable. Please try again in a moment.'
            }), 500

        print(f'[game_detail] Prediction ready: {prediction.get("recommendation")} ({prediction.get("confidence")}% confidence)')

        all_teams = get_all_teams()
        home_team_info = next((t for t in all_teams if t['id'] == int(home_team_id)), {})
        away_team_info = next((t for t in all_teams if t['id'] == int(away_team_id)), {})

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

        return jsonify(response)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/team-stats-with-ranks')
def team_stats_with_ranks():
    """
    Get team statistics with league rankings

    Query params:
        - team_id: NBA team ID (required)
        - season: Season string, defaults to '2025-26'

    Returns:
        {
            'success': True,
            'team_id': 1610612747,
            'team_abbreviation': 'LAL',
            'season': '2025-26',
            'stats': {
                'ppg': {'value': 111.7, 'rank': 18},
                'opp_ppg': {'value': 116.3, 'rank': 25},
                'fg_pct': {'value': 47.3, 'rank': 12},
                'three_pct': {'value': 35.9, 'rank': 9},
                'ft_pct': {'value': 83.3, 'rank': 4},
                'off_rtg': {'value': 113.9, 'rank': 15},
                'def_rtg': {'value': 118.5, 'rank': 27},
                'net_rtg': {'value': -4.6, 'rank': 24},
                'pace': {'value': 96.7, 'rank': 20}
            }
        }
    """
    try:
        team_id = request.args.get('team_id')
        season = request.args.get('season', '2025-26')

        if not team_id:
            return jsonify({
                'success': False,
                'error': 'Missing team_id parameter'
            }), 400

        print(f'[team_stats_with_ranks] Fetching stats with ranks for team {team_id}, season {season}')

        # Get team stats with rankings
        team_data = team_rankings.get_team_stats_with_ranks(int(team_id), season)

        if not team_data:
            return jsonify({
                'success': False,
                'error': f'Stats not found for team {team_id}'
            }), 404

        return jsonify({
            'success': True,
            **team_data
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/predict', methods=['POST'])
def predict():
    """Make a prediction for a game"""
    try:
        data = request.get_json()
        home_team_id = data.get('home_team_id')
        away_team_id = data.get('away_team_id')
        betting_line = data.get('betting_line')

        if not home_team_id or not away_team_id:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400

        prediction = get_cached_prediction(int(home_team_id), int(away_team_id), betting_line)

        if prediction is None:
            return jsonify({
                'success': False,
                'error': 'Failed to generate prediction'
            }), 500

        return jsonify({
            'success': True,
            'prediction': prediction
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback"""
    try:
        data = request.get_json()
        print(f'[feedback] Received: {data}')

        return jsonify({
            'success': True,
            'message': 'Feedback received'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== SELF-LEARNING PREDICTION ENDPOINTS ==========

@app.route('/api/save-prediction', methods=['POST'])
def save_prediction():
    """
    Save a pre-game prediction for later comparison with sportsbook line and actual results

    Request body:
    {
        "game_id": "0022500123",
        "home_team": "BOS",
        "away_team": "LAL"
    }
    """
    from api.utils.performance import log_slow_operation

    try:
        data = request.get_json()

        # Validate required fields
        game_id = data.get('game_id')
        home_team = data.get('home_team')
        away_team = data.get('away_team')

        if not all([game_id, home_team, away_team]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: game_id, home_team, away_team'
            }), 400

        print(f'[save-prediction] Generating prediction for {away_team} @ {home_team} (game {game_id})')

        # Get team IDs for the complex prediction engine
        all_teams = get_all_teams()
        home_team_data = next((t for t in all_teams if t['abbreviation'] == home_team), None)
        away_team_data = next((t for t in all_teams if t['abbreviation'] == away_team), None)

        if not home_team_data or not away_team_data:
            return jsonify({
                'success': False,
                'error': f'Team not found: {home_team if not home_team_data else away_team}'
            }), 400

        home_team_id = home_team_data['id']
        away_team_id = away_team_data['id']

        # Use the COMPLEX prediction engine (same as dashboard)
        try:
            with log_slow_operation("Fetch matchup data from NBA API", threshold_ms=3000):
                matchup_data = get_matchup_data(home_team_id, away_team_id)
                if matchup_data is None:
                    error_details = """
NBA API Failed to Return Data

Possible causes:
1. NBA API is currently slow or down (check stats.nba.com)
2. Rate limiting after multiple requests
3. Network connectivity issues
4. Invalid team IDs

What to try:
• Wait 30-60 seconds and try again
• Check if the NBA API is operational at https://stats.nba.com
• Try a different game
• Check Railway logs for detailed error messages
                    """
                    print(f'[save-prediction] NBA API failure for teams {home_team} vs {away_team}')
                    return jsonify({
                        'success': False,
                        'error': 'NBA API is currently unavailable',
                        'details': error_details.strip(),
                        'retry': True
                    }), 503  # Service Unavailable

            with log_slow_operation("Generate base prediction", threshold_ms=500):
                # Get BASE prediction using the complex engine
                prediction = predict_game_total(
                    matchup_data['home'],
                    matchup_data['away'],
                    betting_line=None  # No line yet
                )

                base_home = prediction['breakdown']['home_projected']
                base_away = prediction['breakdown']['away_projected']
                base_total = prediction['predicted_total']

                print(f'[save-prediction] Base prediction: {base_total} ({base_home} - {base_away})')

        except KeyError as e:
            print(f'[save-prediction] Data structure error: {str(e)}')
            return jsonify({
                'success': False,
                'error': f'Incomplete data from NBA API (missing {str(e)})',
                'retry': True
            }), 500
        except Exception as e:
            print(f'[save-prediction] Unexpected error: {str(e)}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Prediction failed: {str(e)}',
                'retry': False
            }), 500

        # Extract game date from game_id or use current date
        game_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        # Build feature vector for analytics (no learning applied)
        feature_correction = 0.0  # Always 0 in deterministic mode
        feature_vector_dict = None
        feature_metadata = None

        try:
            from api.utils.feature_builder import build_feature_vector
            import json

            with log_slow_operation("Build feature vector (rankings + recent games)", threshold_ms=2000):
                print(f'[save-prediction] Building feature vector for analytics...')
                feature_data = build_feature_vector(
                    home_team=home_team,
                    away_team=away_team,
                    game_id=game_id,
                    as_of_date=game_date,
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    n_recent_games=model_params.get('parameters', {}).get('recent_games_n', 10),
                    season='2025-26'
                )

            # Store feature data for analytics only (no weights applied)
            feature_vector_dict = json.dumps(feature_data['features'])
            feature_metadata = json.dumps(feature_data['metadata'])
            print(f'[save-prediction] Feature vector saved for analytics (no correction applied)')

        except Exception as e:
            print(f'[save-prediction] Warning: Could not compute features: {e}')
            print('[save-prediction] Continuing with base prediction')
            # Continue with base prediction

        # Use base total directly (no learned feature correction)
        intermediate_total = base_total

        # Apply deterministic opponent-profile adjustment (NEW LAYER)
        try:
            from api.utils.opponent_profile_adjustment import compute_opponent_profile_adjustment

            print('[save-prediction] Computing opponent-profile adjustment...')
            opp_adjustment_result = compute_opponent_profile_adjustment(
                home_tricode=home_team,
                away_tricode=away_team,
                as_of_date=game_date,
                base_total=base_total,
                base_home=base_home,
                base_away=base_away
            )

            opponent_adjustment = opp_adjustment_result['adjustment']
            print(f'[save-prediction] Opponent-profile adjustment: {opponent_adjustment:+.2f}')

            # Final prediction = base + learned_features + deterministic_opponent_adjustment
            pred_total = intermediate_total + opponent_adjustment
            pred_home = opp_adjustment_result['adjusted_home']
            pred_away = opp_adjustment_result['adjusted_away']

        except Exception as e:
            print(f'[save-prediction] Warning: Could not compute opponent adjustment: {e}')
            print('[save-prediction] Falling back to intermediate prediction (base + features)')
            # Fallback: use intermediate total without opponent adjustment
            opponent_adjustment = 0.0
            opp_adjustment_result = None
            pred_total = intermediate_total

            # Split intermediate total into team scores
            base_ratio = base_home / (base_home + base_away) if (base_home + base_away) > 0 else 0.5
            pred_home = pred_total * base_ratio
            pred_away = pred_total * (1 - base_ratio)

        print(f'[save-prediction] Final prediction: {pred_total:.1f} ({pred_home:.1f} - {pred_away:.1f})')
        print(f'[save-prediction] Breakdown: base={base_total:.1f}, feature_corr={feature_correction:+.1f}, opp_adj={opponent_adjustment:+.1f}')

        # Save to database with feature data
        result = db.save_prediction(
            game_id=game_id,
            home_team=home_team,
            away_team=away_team,
            game_date=game_date,
            pred_home=pred_home,
            pred_away=pred_away,
            pred_total=pred_total,
            model_version='3.0',
            base_prediction=base_total,
            feature_correction=feature_correction,
            feature_vector=feature_vector_dict,
            feature_metadata=feature_metadata
        )

        if not result['success']:
            return jsonify(result), 400

        print(f'[save-prediction] ✓ Saved prediction: {pred_total} total')

        # Build detailed response with all prediction layers
        result['prediction'] = {
            'base': {
                'total': base_total,
                'home': base_home,
                'away': base_away
            },
            'with_learned_features': {
                'total': base_total + feature_correction,
                'correction': feature_correction
            },
            'with_opponent_profile': {
                'total': pred_total,
                'home': pred_home,
                'away': pred_away,
                'adjustment': opponent_adjustment,
                'explanation': opp_adjustment_result['explanation'] if opp_adjustment_result else 'No adjustment applied'
            },
            'layers_breakdown': {
                'base': base_total,
                'feature_correction': feature_correction,
                'opponent_adjustment': opponent_adjustment,
                'final': pred_total
            },
            'recommendation': prediction.get('recommendation', ''),
            'confidence': prediction.get('confidence', 0)
        }

        # Add opponent details if available
        if opp_adjustment_result:
            result['prediction']['opponent_details'] = opp_adjustment_result['details']

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/submit-line', methods=['POST'])
def submit_line():
    """
    Submit the sportsbook closing total line for a game

    Request body:
    {
        "game_id": "0022500123",
        "sportsbook_total_line": 218.5
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        game_id = data.get('game_id')
        sportsbook_total_line = data.get('sportsbook_total_line')

        if not game_id or sportsbook_total_line is None:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: game_id, sportsbook_total_line'
            }), 400

        # Validate line is a number
        try:
            sportsbook_total_line = float(sportsbook_total_line)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'sportsbook_total_line must be a number'
            }), 400

        print(f'[submit-line] Submitting line {sportsbook_total_line} for game {game_id}')

        # Save to database
        result = db.submit_line(game_id, sportsbook_total_line)

        if not result['success']:
            return jsonify(result), 404

        print(f'[submit-line] ✓ Line submitted successfully')

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Learning endpoint removed - system is now deterministic


@app.route('/api/prediction-history', methods=['GET'])
def prediction_history():
    """
    Get prediction history with optional filters

    Query params:
        - limit: Number of records (default 50)
        - with_learning: Only show predictions with completed learning (default false)
    """
    try:
        limit = int(request.args.get('limit', 50))
        with_learning = request.args.get('with_learning', 'false').lower() == 'true'

        if with_learning:
            predictions = db.get_predictions_with_learning(limit=limit)
        else:
            predictions = db.get_all_predictions(limit=limit)

        # Calculate performance stats
        stats = db.get_model_performance_stats(days=30)

        return jsonify({
            'success': True,
            'predictions': predictions,
            'stats': stats,
            'count': len(predictions)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Automated learning endpoints removed - system is now deterministic


# Catch-all route to serve React app for client-side routing
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    """Serve React app for all non-API routes"""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return app.send_static_file(path)
    else:
        return app.send_static_file('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
