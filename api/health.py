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
            # Test basic imports and database connectivity
            from utils.db_queries import get_all_teams, get_data_freshness

            # Test GitHub credentials (for self-learning feature)
            gh_token_set = bool(os.getenv('GH_TOKEN'))
            gh_repo_set = bool(os.getenv('GH_REPO'))

            # Check database connectivity
            teams = get_all_teams()
            db_working = teams is not None and len(teams) > 0

            # Check data freshness
            freshness = get_data_freshness()
            data_stale = freshness.get('is_stale', False)

            response = {
                'success': True,
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'checks': {
                    'api_server': 'up',
                    'database': 'connected' if db_working else 'degraded',
                    'data_freshness': 'stale (>12hrs old)' if data_stale else 'fresh',
                    'github_credentials': 'configured' if (gh_token_set and gh_repo_set) else 'not configured',
                },
                'data_freshness': freshness,
                'version': '2.0.0',
                'environment': 'production' if os.getenv('VERCEL') else 'development',
            }

            # If database is down or data is stale, still return 200 but mark as degraded
            if not db_working or data_stale:
                response['status'] = 'degraded'
                if not db_working:
                    response['message'] = 'Database connectivity issues detected'
                elif data_stale:
                    response['message'] = 'Data is stale (>12 hours old) - sync may be needed'

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
