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
from api.utils.github_persistence import commit_model_to_github
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

# Initialize database on startup
db.init_db()

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

    prediction = predict_game_total(
        matchup_data['home'],
        matchup_data['away'],
        betting_line
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

        # Build feature vector and compute correction
        feature_correction = 0.0
        feature_vector_dict = None
        feature_metadata = None

        try:
            from api.utils.feature_builder import build_feature_vector, compute_feature_correction
            import json

            with log_slow_operation("Build feature vector (rankings + recent games)", threshold_ms=2000):
                print(f'[save-prediction] Building feature vector...')
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

            # Load feature weights from model
            feature_weights = model_params.get('feature_weights', {})

            # Compute correction: w·x
            feature_correction = compute_feature_correction(
                feature_data['features'],
                feature_weights
            )

            print(f'[save-prediction] Feature correction: {feature_correction:+.2f}')

            # Store feature data for database
            feature_vector_dict = json.dumps(feature_data['features'])
            feature_metadata = json.dumps(feature_data['metadata'])

        except Exception as e:
            print(f'[save-prediction] Warning: Could not compute features: {e}')
            print('[save-prediction] Falling back to base prediction only')
            # Continue with base prediction, feature_correction = 0

        # Apply correction to base prediction
        pred_total = base_total + feature_correction

        # Split total back into team scores, preserving original ratio
        base_ratio = base_home / (base_home + base_away) if (base_home + base_away) > 0 else 0.5
        pred_home = pred_total * base_ratio
        pred_away = pred_total * (1 - base_ratio)

        print(f'[save-prediction] Final prediction: {pred_total:.1f} ({pred_home:.1f} - {pred_away:.1f})')

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

        # Add full prediction details to response
        result['prediction']['home'] = pred_home
        result['prediction']['away'] = pred_away
        result['prediction']['base'] = base_total
        result['prediction']['correction'] = feature_correction
        result['prediction']['recommendation'] = prediction.get('recommendation', '')
        result['prediction']['confidence'] = prediction.get('confidence', 0)

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


@app.route('/api/run-learning', methods=['POST'])
def run_learning():
    """
    Run post-game learning after a game completes

    This endpoint:
    1. Fetches the final score from NBA API
    2. Compares model prediction vs sportsbook line vs actual result
    3. Updates team ratings and total_bias
    4. Commits updated model to GitHub
    5. Saves error metrics to database

    Request body:
    {
        "game_id": "0022500123"
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        game_id = data.get('game_id')

        if not game_id:
            return jsonify({
                'success': False,
                'error': 'Missing required field: game_id'
            }), 400

        print(f'[run-learning] Starting learning process for game {game_id}')

        # 1. Get the saved prediction from database
        prediction_data = db.get_prediction(game_id)

        if not prediction_data:
            return jsonify({
                'success': False,
                'error': f'No prediction found for game {game_id}. Save a prediction first.'
            }), 404

        # 2. Fetch final score from NBA API
        print(f'[run-learning] Fetching final score from NBA API...')
        games = get_todays_games()

        if not games:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch games from NBA API'
            }), 500

        game = next((g for g in games if str(g.get('game_id')) == str(game_id)), None)

        if not game:
            return jsonify({
                'success': False,
                'error': f'Game {game_id} not found in NBA API response'
            }), 404

        # 3. Check if game is finished
        game_status = game.get('game_status', '')
        if game_status != 'Final':
            return jsonify({
                'success': False,
                'error': f'Game is not finished yet. Current status: {game_status}'
            }), 400

        # 4. Get actual scores
        actual_home = game.get('home_team_score')
        actual_away = game.get('away_team_score')

        if actual_home is None or actual_away is None:
            return jsonify({
                'success': False,
                'error': 'Final scores not available in NBA API response'
            }), 500

        actual_total = actual_home + actual_away

        print(f'[run-learning] Final score: {prediction_data["away_team"]} {actual_away}, {prediction_data["home_team"]} {actual_home} (Total: {actual_total})')

        # 5. Update actual results in database
        db.update_actual_results(game_id, actual_home, actual_away)

        # 6. Run team rating updates (existing logic)
        print(f'[run-learning] Updating team ratings...')
        rating_update = team_ratings_model.update_ratings(
            home_tricode=prediction_data['home_team'],
            away_tricode=prediction_data['away_team'],
            home_pts_final=actual_home,
            away_pts_final=actual_away
        )

        # 7. Run line-aware learning (existing)
        line_metrics = None
        if prediction_data['sportsbook_total_line'] is not None:
            print(f'[run-learning] Running line-aware learning...')
            line_metrics = team_ratings_model.update_from_sportsbook_line(
                pred_total=prediction_data['pred_total'],
                sportsbook_line=prediction_data['sportsbook_total_line'],
                actual_total=actual_total
            )

            # 8. Save error metrics to database
            db.update_error_metrics(game_id, {
                'model_error': line_metrics['model_error'],
                'line_error': line_metrics['line_error'],
                'model_abs_error': line_metrics['model_abs_error'],
                'line_abs_error': line_metrics['line_abs_error'],
                'model_beat_line': line_metrics['model_beat_line']
            })

            print(f'[run-learning] Model error: {line_metrics["model_abs_error"]}, Line error: {line_metrics["line_abs_error"]}')
            print(f'[run-learning] {"✓ Model beat line!" if line_metrics["model_beat_line"] else "✗ Line beat model"}')
        else:
            print(f'[run-learning] No sportsbook line submitted, skipping line-aware learning')

            # Still save basic error metrics
            model_error = actual_total - prediction_data['pred_total']
            db.update_error_metrics(game_id, {
                'model_error': model_error,
                'line_error': None,
                'model_abs_error': abs(model_error),
                'line_abs_error': None,
                'model_beat_line': None
            })

        # 7b. Update feature weights (NEW)
        feature_weights_updated = False
        if prediction_data.get('feature_vector'):
            try:
                import json
                print(f'[run-learning] Updating feature weights...')

                # Load stored feature vector
                feature_vector = json.loads(prediction_data['feature_vector'])

                # Compute model error
                model_error = actual_total - prediction_data['pred_total']

                # Get current model and feature weights
                model = team_ratings_model.load_model()
                feature_weights = model.get('feature_weights', {})
                feature_lr = model['parameters'].get('feature_learning_rate', 0.01)

                # Update each feature weight: w = w + η * error * x
                for feature_name, feature_value in feature_vector.items():
                    old_weight = feature_weights.get(feature_name, 0.0)
                    new_weight = old_weight + (feature_lr * model_error * feature_value)

                    # Clamp weights to [-10, +10] to prevent runaway values
                    new_weight = max(-10.0, min(10.0, new_weight))

                    feature_weights[feature_name] = round(new_weight, 4)

                # Update model with new feature weights
                model['feature_weights'] = feature_weights
                team_ratings_model.save_model(model)
                feature_weights_updated = True

                print(f'[run-learning] ✓ Feature weights updated (error: {model_error:+.1f})')

            except Exception as e:
                print(f'[run-learning] Warning: Could not update feature weights: {e}')
        else:
            print(f'[run-learning] No feature vector found, skipping feature weight updates')

        # 7c. Record game to team_game_history for both teams (NEW)
        try:
            from api.utils.matchup_profile import update_team_game_history_entry

            print(f'[run-learning] Recording game to team_game_history...')

            # Get team IDs
            all_teams = get_all_teams()
            home_team_data = next((t for t in all_teams if t['abbreviation'] == prediction_data['home_team']), None)
            away_team_data = next((t for t in all_teams if t['abbreviation'] == prediction_data['away_team']), None)

            if home_team_data and away_team_data:
                # Record home team's performance
                update_team_game_history_entry(
                    game_id=game_id,
                    team_tricode=prediction_data['home_team'],
                    opponent_tricode=prediction_data['away_team'],
                    stats={
                        'points_scored': actual_home,
                        'points_allowed': actual_away,
                        'is_home': True
                    },
                    game_date=prediction_data['game_date']
                )

                # Record away team's performance
                update_team_game_history_entry(
                    game_id=game_id,
                    team_tricode=prediction_data['away_team'],
                    opponent_tricode=prediction_data['home_team'],
                    stats={
                        'points_scored': actual_away,
                        'points_allowed': actual_home,
                        'is_home': False
                    },
                    game_date=prediction_data['game_date']
                )

                print(f'[run-learning] ✓ Game recorded to team_game_history for both teams')
            else:
                print(f'[run-learning] Warning: Could not find team data for history recording')

        except Exception as e:
            print(f'[run-learning] Warning: Could not record game to team_game_history: {e}')

        # 9. Commit updated model to GitHub (optional - works without GH_TOKEN in local dev)
        print(f'[run-learning] Committing model to GitHub...')

        # Use the updated model from line_metrics if available, otherwise from rating_update
        updated_model = line_metrics['updated_model'] if line_metrics else rating_update['updated_model']

        model_committed = False
        try:
            commit_result = commit_model_to_github(
                updated_model,
                commit_message=f"Learn from game {game_id}: {prediction_data['away_team']}@{prediction_data['home_team']} ({actual_away}-{actual_home})"
            )
            model_committed = commit_result.get('success', False) if commit_result else False
        except ValueError as e:
            print(f'[run-learning] ⚠ GitHub commit skipped: {str(e)}')
        except Exception as e:
            print(f'[run-learning] ⚠ GitHub commit failed: {str(e)}')

        if model_committed:
            print(f'[run-learning] ✓ Model committed to GitHub')
        else:
            print(f'[run-learning] ℹ Local model updated (GitHub commit skipped)')

        # 10. Build response
        response = {
            'success': True,
            'game_id': game_id,
            'actual_total': actual_total,
            'pred_total': prediction_data['pred_total'],
            'model_committed': model_committed,
            'feature_weights_updated': feature_weights_updated
        }

        # Add line comparison if available
        if line_metrics:
            response.update({
                'sportsbook_line': prediction_data['sportsbook_total_line'],
                'model_error': line_metrics['model_error'],
                'line_error': line_metrics['line_error'],
                'model_beat_line': line_metrics['model_beat_line'],
                'total_bias_update': {
                    'old': line_metrics['old_total_bias'],
                    'new': line_metrics['new_total_bias'],
                    'adjustment': line_metrics['bias_adjustment']
                }
            })

        # Add team rating updates
        response['updates'] = {
            f'{prediction_data["home_team"]}_off': rating_update['new_ratings'][prediction_data['home_team']]['off'],
            f'{prediction_data["home_team"]}_def': rating_update['new_ratings'][prediction_data['home_team']]['def'],
            f'{prediction_data["away_team"]}_off': rating_update['new_ratings'][prediction_data['away_team']]['off'],
            f'{prediction_data["away_team"]}_def': rating_update['new_ratings'][prediction_data['away_team']]['def']
        }

        print(f'[run-learning] ✓ Learning complete!')

        return jsonify(response)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
