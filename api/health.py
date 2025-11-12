"""
Health check endpoint for monitoring API status
"""
from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime, timezone
import sys
import os

# Add the api directory to path
sys.path.append(os.path.dirname(__file__))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET /api/health"""
        try:
            # Test basic imports
            from utils.nba_data import get_all_teams

            # Test GitHub credentials (for self-learning feature)
            gh_token_set = bool(os.getenv('GH_TOKEN'))
            gh_repo_set = bool(os.getenv('GH_REPO'))

            # Attempt to fetch teams to verify NBA API connectivity
            teams = get_all_teams()
            nba_api_working = teams is not None and len(teams) > 0

            response = {
                'success': True,
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'checks': {
                    'api_server': 'up',
                    'nba_api': 'connected' if nba_api_working else 'degraded',
                    'github_credentials': 'configured' if (gh_token_set and gh_repo_set) else 'not configured',
                },
                'version': '1.0.0',
                'environment': 'production' if os.getenv('VERCEL') else 'development',
            }

            # If NBA API is down, still return 200 but mark as degraded
            if not nba_api_working:
                response['status'] = 'degraded'
                response['message'] = 'NBA API connectivity issues detected'

            self.send_json_response(response, 200)

        except Exception as e:
            import traceback
            traceback.print_exc()

            # Return 500 if health check itself fails
            response = {
                'success': False,
                'status': 'unhealthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
            }
            self.send_json_response(response, 500)

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def send_json_response(self, data, status_code=200):
        """Send JSON response with CORS headers"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
