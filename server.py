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

app = Flask(__name__, static_folder='dist', static_url_path='')
CORS(app)

# Initialize database on startup
db.init_db()

# In-memory prediction cache
_prediction_cache = {}
_CACHE_MAX_SIZE = 128

def get_cached_prediction(home_team_id, away_team_id, betting_line):
    """Get prediction from cache or generate new one"""
    cache_key = (int(home_team_id), int(away_team_id), betting_line)

    if cache_key in _prediction_cache:
        print(f'[cache] HIT: Returning cached prediction for game {away_team_id}@{home_team_id} (line: {betting_line})')
        return _prediction_cache[cache_key]

    print(f'[cache] MISS: Generating prediction for game {away_team_id}@{home_team_id} (line: {betting_line})')

    matchup_data = get_matchup_data(home_team_id, away_team_id)
    if matchup_data is None:
        print('[cache] ERROR: Failed to fetch matchup data')
        return None

    prediction = predict_game_total(
        matchup_data['home'],
        matchup_data['away'],
        betting_line
    )

    if len(_prediction_cache) >= _CACHE_MAX_SIZE:
        oldest_key = next(iter(_prediction_cache))
        print(f'[cache] EVICT: Removing oldest entry {oldest_key}')
        _prediction_cache.pop(oldest_key)

    _prediction_cache[cache_key] = prediction
    print(f'[cache] STORE: Cached prediction for {cache_key}')

    return prediction

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
    try:
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

        return jsonify(response)

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
        prediction = get_cached_prediction(int(home_team_id), int(away_team_id), betting_line)

        if prediction is None:
            print('[game_detail] ERROR: Failed to generate prediction')
            return jsonify({
                'success': False,
                'error': 'The NBA API is currently slow or unavailable. Please try again in a moment.'
            }), 500

        print(f'[game_detail] Prediction ready: {prediction.get("recommendation")} ({prediction.get("confidence")}% confidence)')

        matchup_data = get_matchup_data(int(home_team_id), int(away_team_id))

        if matchup_data is None:
            print('[game_detail] ERROR: Failed to fetch matchup data for stats display')
            return jsonify({
                'success': False,
                'error': 'Failed to fetch game stats'
            }), 500

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
            matchup_data = get_matchup_data(home_team_id, away_team_id)
            if matchup_data is None:
                raise Exception('Failed to fetch matchup data from NBA API')

            # Get prediction using the complex engine
            prediction = predict_game_total(
                matchup_data['home'],
                matchup_data['away'],
                betting_line=None  # No line yet
            )

            pred_home = prediction['projected_home_score']
            pred_away = prediction['projected_away_score']
            pred_total = prediction['projected_total']

        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Prediction failed: {str(e)}'
            }), 400

        # Extract game date from game_id or use current date
        game_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        # Save to database
        result = db.save_prediction(
            game_id=game_id,
            home_team=home_team,
            away_team=away_team,
            game_date=game_date,
            pred_home=pred_home,
            pred_away=pred_away,
            pred_total=pred_total,
            model_version='complex_v1'
        )

        if not result['success']:
            return jsonify(result), 400

        print(f'[save-prediction] ✓ Saved prediction: {pred_total} total')

        # Add full prediction details to response
        result['prediction']['home'] = pred_home
        result['prediction']['away'] = pred_away
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

        # 7. Run line-aware learning (NEW)
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
            'model_committed': model_committed
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
