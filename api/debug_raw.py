"""
Debug endpoint that calls NBA API directly without decorators
"""
from http.server import BaseHTTPRequestHandler
import json
import time
import sys
import os

sys.path.append(os.path.dirname(__file__))

# Import NBA API directly
from nba_api.stats.endpoints import teamdashboardbygeneralsplits
from utils.nba_data import get_todays_games

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Test NBA API directly without decorators"""
        results = {
            'success': True,
            'tests': []
        }

        # Get a team ID from today's games
        test0 = {'name': 'get_games_for_team_id'}
        try:
            games = get_todays_games()
            if games and len(games) > 0:
                team_id = games[0]['home_team_id']
                test0['success'] = True
                test0['team_id'] = team_id
                test0['team_name'] = games[0]['home_team_name']
            else:
                test0['success'] = False
                test0['error'] = 'No games found'
                self.send_json(results)
                return
        except Exception as e:
            test0['success'] = False
            test0['error'] = str(e)
            self.send_json(results)
            return

        results['tests'].append(test0)

        # Test 1: Call NBA API directly for team stats
        test1 = {'name': 'direct_nba_api_call'}
        test1['team_id'] = team_id
        start = time.time()
        try:
            # Direct API call without decorator
            time.sleep(0.05)  # Rate limit delay

            dashboard = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
                team_id=team_id,
                season='2025-26',
                per_mode_detailed='PerGame',
                measure_type_detailed_defense='Base'
            )

            test1['duration_ms'] = int((time.time() - start) * 1000)

            # Get data frames
            splits = dashboard.get_data_frames()[0]
            test1['success'] = True
            test1['row_count'] = len(splits)

            if len(splits) > 0:
                test1['columns'] = list(splits.columns)[:10]  # First 10 columns
                test1['first_row'] = splits.iloc[0].to_dict() if len(splits) > 0 else {}

        except Exception as e:
            import traceback
            test1['duration_ms'] = int((time.time() - start) * 1000)
            test1['success'] = False
            test1['error'] = str(e)
            test1['error_type'] = type(e).__name__
            test1['traceback'] = traceback.format_exc()

        results['tests'].append(test1)

        self.send_json(results)

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode())
