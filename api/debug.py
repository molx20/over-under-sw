"""
Debug endpoint to test NBA API from Vercel
"""
from http.server import BaseHTTPRequestHandler
import json
import time
import sys
import os

sys.path.append(os.path.dirname(__file__))

from utils.nba_data import get_todays_games, get_team_stats, get_team_advanced_stats


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Test NBA API and return diagnostic info"""
        results = {
            'success': True,
            'tests': []
        }

        # Test 1: Get today's games
        test1 = {'name': 'get_todays_games'}
        start = time.time()
        try:
            games = get_todays_games()
            test1['duration_ms'] = int((time.time() - start) * 1000)
            test1['success'] = bool(games)
            test1['game_count'] = len(games) if games else 0
            if games and len(games) > 0:
                test1['sample_game'] = f"{games[0]['away_team_name']} @ {games[0]['home_team_name']}"
                test1['home_team_id'] = games[0]['home_team_id']
                test1['away_team_id'] = games[0]['away_team_id']
        except Exception as e:
            test1['duration_ms'] = int((time.time() - start) * 1000)
            test1['success'] = False
            test1['error'] = str(e)

        results['tests'].append(test1)

        # Test 2: Get team stats (if we got games)
        if test1.get('success') and test1.get('home_team_id'):
            test2 = {'name': 'get_team_stats'}
            start = time.time()
            try:
                stats = get_team_stats(test1['home_team_id'], season='2025-26')
                test2['duration_ms'] = int((time.time() - start) * 1000)
                test2['success'] = bool(stats)
                if stats and stats.get('overall'):
                    test2['ppg'] = stats['overall'].get('PTS', 'N/A')
            except Exception as e:
                test2['duration_ms'] = int((time.time() - start) * 1000)
                test2['success'] = False
                test2['error'] = str(e)

            results['tests'].append(test2)

            # Test 3: Get advanced stats
            test3 = {'name': 'get_team_advanced_stats'}
            start = time.time()
            try:
                adv_stats = get_team_advanced_stats(test1['home_team_id'], season='2025-26')
                test3['duration_ms'] = int((time.time() - start) * 1000)
                test3['success'] = bool(adv_stats)
                if adv_stats:
                    test3['pace'] = adv_stats.get('PACE', 'N/A')
                    test3['ortg'] = adv_stats.get('OFF_RATING', 'N/A')
            except Exception as e:
                test3['duration_ms'] = int((time.time() - start) * 1000)
                test3['success'] = False
                test3['error'] = str(e)

            results['tests'].append(test3)

        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(results, indent=2).encode())
