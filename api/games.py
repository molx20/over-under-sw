"""
API endpoint to get today's games with predictions
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timezone
import sys
import os

# Add the api directory to path
sys.path.append(os.path.dirname(__file__))

from utils.nba_data import get_todays_games, get_matchup_data
from utils.prediction_engine import predict_game_total

app = Flask(__name__)
CORS(app)

@app.route('/api/game_detail', methods=['GET'])
def get_game_detail():
    """
    Get detailed game information with all stats used for prediction
    Query params:
        game_id: NBA game ID (will extract team IDs from cached games)
    """
    try:
        # Get game_id parameter
        game_id = request.args.get('game_id')

        if not game_id:
            return jsonify({
                'success': False,
                'error': 'Missing game_id parameter'
            }), 400

        # Find the game in today's games to get team IDs
        games = get_todays_games()

        if not games:
            return jsonify({
                'success': False,
                'error': 'No games available today'
            }), 404

        game = next((g for g in games if g.get('game_id') == game_id), None)

        if not game:
            # If not found, try matching with string conversion
            game = next((g for g in games if str(g.get('game_id')) == str(game_id)), None)

        if not game:
            return jsonify({
                'success': False,
                'error': f'Game {game_id} not found. Available games: {[g.get("game_id") for g in games]}'
            }), 404

        home_team_id = game['home_team_id']
        away_team_id = game['away_team_id']

        # Get betting line from query params (optional)
        betting_line = request.args.get('betting_line', type=float)

        # Get comprehensive matchup data
        matchup_data = get_matchup_data(int(home_team_id), int(away_team_id))

        if matchup_data is None:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch matchup data from NBA API. Please try again later.'
            }), 500

        # Generate prediction (betting_line can be None)
        prediction = predict_game_total(
            matchup_data['home'],
            matchup_data['away'],
            betting_line
        )

        # Get team info
        from utils.nba_data import get_all_teams
        all_teams = get_all_teams()
        home_team_info = next((t for t in all_teams if t['id'] == int(home_team_id)), {})
        away_team_info = next((t for t in all_teams if t['id'] == int(away_team_id)), {})

        # Safely extract stats with defaults
        home_overall = matchup_data['home']['stats'].get('overall', {}) if matchup_data['home'].get('stats') else {}
        away_overall = matchup_data['away']['stats'].get('overall', {}) if matchup_data['away'].get('stats') else {}
        home_adv = matchup_data['home'].get('advanced') or {}
        away_adv = matchup_data['away'].get('advanced') or {}
        home_opp = matchup_data['home'].get('opponent') or {}
        away_opp = matchup_data['away'].get('opponent') or {}

        # Format detailed response with ALL stats - NESTED STRUCTURE for frontend
        return jsonify({
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
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/games', methods=['GET'])
def get_games():
    """
    Get all games for today with predictions
    Query params:
        date: YYYY-MM-DD format (optional, defaults to today)
    """
    try:
        # Get date from query params
        date_str = request.args.get('date')
        if date_str:
            # For now, we'll use today's games
            # In the future, implement get_games_by_date
            pass

        # Get games
        games = get_todays_games()

        if games is None:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch games from NBA API'
            }), 500

        # Add predictions to each game
        games_with_predictions = []
        for game in games:
            try:
                # Get comprehensive matchup data
                matchup_data = get_matchup_data(
                    game['home_team_id'],
                    game['away_team_id']
                )

                if matchup_data is None:
                    print(f"Failed to get matchup data for game {game.get('game_id')}")
                    games_with_predictions.append({
                        **game,
                        'prediction': None,
                        'error': 'Failed to fetch team stats'
                    })
                    continue

                # Generate betting line (mock for now - in production, fetch from odds API)
                # For demo purposes, we'll use a reasonable baseline
                mock_line = 220.5

                # Generate prediction using new data structure
                prediction = predict_game_total(
                    matchup_data['home'],
                    matchup_data['away'],
                    mock_line
                )

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
                    'prediction': prediction,
                })
            except Exception as e:
                print(f"Error predicting game {game.get('game_id')}: {str(e)}")
                import traceback
                traceback.print_exc()
                # Add game without prediction
                games_with_predictions.append({
                    **game,
                    'prediction': None,
                    'error': str(e)
                })

        return jsonify({
            'success': True,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'games': games_with_predictions,
            'count': len(games_with_predictions),
            # Use RFC 3339 UTC timestamp compatible with Safari (no 6-digit micros)
            'last_updated': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# For Vercel serverless function
def handler(request):
    with app.request_context(request.environ):
        return app.full_dispatch_request()

if __name__ == '__main__':
    # For local testing
    app.run(debug=True, port=5001)
