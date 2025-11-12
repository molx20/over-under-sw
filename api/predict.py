"""
Team ratings prediction endpoint

GET /api/predict?home=BOS&away=LAL

Returns simple team-ratings-based prediction for a matchup.
This is a separate, lightweight model from the existing complex prediction system.
"""

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import sys
import os

# Add the api directory to path
sys.path.append(os.path.dirname(__file__))

from utils.team_ratings_model import predict, get_model_data

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """
        Handle GET /api/predict?home=XXX&away=YYY

        Query Parameters:
            home (required): Home team tricode (e.g., 'BOS')
            away (required): Away team tricode (e.g., 'LAL')

        Response 200:
            {
                "success": true,
                "home_team": "BOS",
                "away_team": "LAL",
                "home_pts": 103.5,
                "home_pts_rounded": 104,
                "away_pts": 98.2,
                "away_pts_rounded": 98,
                "predicted_total": 201.7,
                "model_version": "1.0"
            }

        Response 400: Missing or invalid parameters
        Response 404: Team tricode not found
        Response 500: Server error
        """
        try:
            # Parse query parameters
            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)

            # Get home and away team tricodes
            home_tricode = query_params.get('home', [None])[0]
            away_tricode = query_params.get('away', [None])[0]

            # Validate required parameters
            if not home_tricode:
                self.send_error_response(400, 'Missing required parameter: home')
                return

            if not away_tricode:
                self.send_error_response(400, 'Missing required parameter: away')
                return

            # Convert to uppercase to be flexible with input
            home_tricode = home_tricode.upper()
            away_tricode = away_tricode.upper()

            # Call prediction model
            try:
                prediction = predict(home_tricode, away_tricode)

                # Build response
                response = {
                    'success': True,
                    'home_team': home_tricode,
                    'away_team': away_tricode,
                    **prediction
                }

                self.send_json_response(response)

            except ValueError as e:
                # Team not found in model
                self.send_error_response(404, str(e))

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_response(500, f'Server error: {str(e)}')

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
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
        self.send_header('Cache-Control', 'public, max-age=60')  # Cache for 1 minute
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_error_response(self, status_code, error_message):
        """Send error response"""
        response = {
            'success': False,
            'error': error_message
        }
        self.send_json_response(response, status_code)
