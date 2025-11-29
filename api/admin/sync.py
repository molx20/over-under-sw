"""
Protected Admin Sync Endpoint

POST /api/admin/sync
Authorization: Bearer <SECRET_TOKEN>

Body:
{
    "sync_type": "full|teams|season_stats|game_logs|todays_games",
    "season": "2025-26"
}

Response:
{
    "success": true,
    "total_records": 450,
    "duration_seconds": 45.2,
    "teams": 30,
    "season_stats": 90,
    "game_logs": 300,
    "todays_games": 8
}
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.sync_nba_data import sync_all, sync_teams, sync_season_stats, sync_game_logs, sync_todays_games

# Secret token from environment
ADMIN_SECRET = os.getenv('ADMIN_SYNC_SECRET', 'CHANGE_ME_IN_PRODUCTION')


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle sync request"""
        try:
            # Check authentication
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.send_error_response(401, 'Missing or invalid Authorization header')
                return

            token = auth_header[7:]  # Remove 'Bearer '
            if token != ADMIN_SECRET:
                self.send_error_response(403, 'Invalid admin token')
                return

            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
            data = json.loads(body) if body else {}

            sync_type = data.get('sync_type', 'full')
            season = data.get('season', '2025-26')

            # Execute sync
            if sync_type == 'full':
                result = sync_all(season, triggered_by='manual')
            elif sync_type == 'teams':
                count, error = sync_teams(season)
                result = {'success': error is None, 'teams': count, 'total_records': count, 'error': error}
            elif sync_type == 'season_stats':
                count, error = sync_season_stats(season)
                result = {'success': error is None, 'season_stats': count, 'total_records': count, 'error': error}
            elif sync_type == 'game_logs':
                count, error = sync_game_logs(season)
                result = {'success': error is None, 'game_logs': count, 'total_records': count, 'error': error}
            elif sync_type == 'todays_games':
                count, error = sync_todays_games(season)
                result = {'success': error is None, 'todays_games': count, 'total_records': count, 'error': error}
            else:
                self.send_error_response(400, f'Invalid sync_type: {sync_type}')
                return

            self.send_json_response(result)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_response(500, str(e))

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def send_error_response(self, status_code, message):
        self.send_json_response({'success': False, 'error': message}, status_code)
