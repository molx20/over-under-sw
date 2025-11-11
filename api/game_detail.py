"""
API endpoint to get detailed game analysis
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os

sys.path.append(os.path.dirname(__file__))

from utils.nba_data import get_matchup_data
from utils.prediction_engine import predict_game_total

app = Flask(__name__)
CORS(app)

@app.route('/api/game_detail', methods=['GET'])
def get_game_detail():
    """
    Get detailed analysis for a specific game
    Query params:
        home_team_id: Home team ID (required)
        away_team_id: Away team ID (required)
        betting_line: Current betting line (optional)
    """
    try:
        home_team_id = request.args.get('home_team_id')
        away_team_id = request.args.get('away_team_id')
        betting_line = request.args.get('betting_line', type=float)

        if not home_team_id or not away_team_id:
            return jsonify({
                'success': False,
                'error': 'Missing team IDs'
            }), 400

        # Get comprehensive matchup data
        matchup_data = get_matchup_data(int(home_team_id), int(away_team_id))

        if matchup_data is None:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch team data from NBA API'
            }), 500

        # Generate prediction
        prediction = predict_game_total(
            matchup_data['home'],
            matchup_data['away'],
            betting_line
        )

        # Format the response
        return jsonify({
            'success': True,
            'prediction': prediction,
            'home_stats': matchup_data['home']['stats'],
            'away_stats': matchup_data['away']['stats'],
            'home_advanced': matchup_data['home']['advanced'],
            'away_advanced': matchup_data['away']['advanced'],
            'home_recent_games': matchup_data['home']['recent_games'],
            'away_recent_games': matchup_data['away']['recent_games'],
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
