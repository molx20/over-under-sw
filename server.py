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

app = Flask(__name__, static_folder='dist', static_url_path='')
CORS(app)

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

        et_offset = timedelta(hours=-5)
        et_time = datetime.now(timezone.utc) + et_offset

        response = {
            'success': True,
            'date': et_time.strftime('%Y-%m-%d'),
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
