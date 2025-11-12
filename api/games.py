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

from utils.nba_data import get_todays_games, get_matchup_data, get_all_teams
from utils.prediction_engine import predict_game_total


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
            # Get games
            games = get_todays_games()

            if games is None:
                self.send_error_response(500, 'Failed to fetch games from NBA API')
                return

            # Debug: if no games, check what's happening
            if len(games) == 0:
                import sys
                from io import StringIO
                # Capture stdout for debugging
                old_stdout = sys.stdout
                sys.stdout = mystdout = StringIO()

                # Call again to see debug output
                from utils.nba_data import clear_cache
                clear_cache()
                games = get_todays_games()

                debug_output = mystdout.getvalue()
                sys.stdout = old_stdout

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

                    # Generate betting line (mock for now)
                    mock_line = 220.5

                    # Generate prediction
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

            # Use Eastern Time for consistency with game dates
            from datetime import timedelta
            et_offset = timedelta(hours=-5)
            et_time = datetime.now(timezone.utc) + et_offset

            response = {
                'success': True,
                'date': et_time.strftime('%Y-%m-%d'),
                'games': games_with_predictions,
                'count': len(games_with_predictions),
                'last_updated': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
            }

            # Add debug info if no games
            if len(games) == 0 and 'debug_output' in locals():
                response['debug'] = debug_output

            self.send_json_response(response)

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
                self.send_error_response(400, 'Missing game_id parameter')
                return

            # Find the game in today's games
            games = get_todays_games()

            if not games:
                self.send_error_response(404, 'No games available today')
                return

            game = next((g for g in games if str(g.get('game_id')) == str(game_id)), None)

            if not game:
                self.send_error_response(404, f'Game {game_id} not found')
                return

            home_team_id = game['home_team_id']
            away_team_id = game['away_team_id']

            # Get betting line
            betting_line_str = query_params.get('betting_line', [None])[0]
            betting_line = float(betting_line_str) if betting_line_str else None

            # Get matchup data
            matchup_data = get_matchup_data(int(home_team_id), int(away_team_id))

            if matchup_data is None:
                self.send_error_response(500, 'Failed to fetch matchup data from NBA API')
                return

            # Generate prediction
            prediction = predict_game_total(
                matchup_data['home'],
                matchup_data['away'],
                betting_line
            )

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

            self.send_json_response(response)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_response(500, str(e))

    def send_json_response(self, data, status_code=200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_error_response(self, status_code, error_message):
        """Send error response"""
        response = {
            'success': False,
            'error': error_message
        }
        self.send_json_response(response, status_code)
