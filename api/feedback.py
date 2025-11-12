"""
Feedback submission endpoint for team ratings model

POST /api/feedback

Accepts game results and updates the model using online learning.
Persists updated model to GitHub repository.
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Add the api directory to path
sys.path.append(os.path.dirname(__file__))

from utils.team_ratings_model import update_ratings, get_model_data
from utils.github_persistence import commit_model_to_github

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """
        Handle POST /api/feedback

        Request Body (JSON):
            {
                "home": "BOS",
                "away": "LAL",
                "home_pts_final": 110,
                "away_pts_final": 95
            }

        Response 200:
            {
                "success": true,
                "message": "Model updated successfully",
                "updated_ratings": {
                    "BOS": {"off": 0.3, "def": -0.16},
                    "LAL": {"off": 0.16, "def": -0.3}
                },
                "errors": {"home": 6.5, "away": -3.2},
                "github_committed": true,
                "commit_sha": "abc123..."
            }

        Response 400: Invalid input
        Response 500: Server error
        """
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error_response(400, 'Empty request body')
                return

            body = self.rfile.read(content_length).decode('utf-8')

            # Parse JSON
            try:
                feedback_data = json.loads(body)
            except json.JSONDecodeError as e:
                self.send_error_response(400, f'Invalid JSON: {str(e)}')
                return

            # Validate required fields
            required_fields = ['home', 'away', 'home_pts_final', 'away_pts_final']
            missing_fields = [f for f in required_fields if f not in feedback_data]

            if missing_fields:
                self.send_error_response(400, f'Missing required fields: {", ".join(missing_fields)}')
                return

            # Extract fields
            home_tricode = feedback_data['home'].upper()
            away_tricode = feedback_data['away'].upper()

            try:
                home_pts_final = float(feedback_data['home_pts_final'])
                away_pts_final = float(feedback_data['away_pts_final'])
            except (ValueError, TypeError) as e:
                self.send_error_response(400, f'Invalid point values: {str(e)}')
                return

            # Validate point values
            if home_pts_final < 0 or away_pts_final < 0:
                self.send_error_response(400, 'Point values must be non-negative')
                return

            if home_pts_final > 200 or away_pts_final > 200:
                self.send_error_response(400, 'Point values seem unrealistic (>200)')
                return

            # Update model with learning
            try:
                update_result = update_ratings(
                    home_tricode,
                    away_tricode,
                    home_pts_final,
                    away_pts_final
                )
            except ValueError as e:
                self.send_error_response(404, str(e))
                return

            # Get updated model for GitHub commit (from update_result, not file)
            updated_model = update_result['updated_model']

            # Commit to GitHub
            commit_message = f"Update ratings: {home_tricode} vs {away_tricode} ({home_pts_final}-{away_pts_final})"
            github_result = commit_model_to_github(updated_model, commit_message)

            # Build response
            response = {
                'success': True,
                'message': 'Model updated successfully',
                'updated_ratings': update_result['new_ratings'],
                'old_ratings': update_result['old_ratings'],
                'errors': update_result['errors'],
                'predictions': update_result['predictions'],
                'learning_rate': update_result['learning_rate'],
                'github_committed': github_result.get('success', False)
            }

            # Add GitHub commit info if successful
            if github_result.get('success'):
                response['commit_sha'] = github_result.get('commit_sha')
                response['commit_url'] = github_result.get('commit_url')
            else:
                response['github_error'] = github_result.get('error', 'Unknown error')

            self.send_json_response(response)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_response(500, f'Server error: {str(e)}')

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def send_json_response(self, data, status_code=200):
        """Send JSON response with CORS headers"""
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
