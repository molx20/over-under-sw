"""
Debug endpoint to check database status

GET /api/debug_db

Returns information about database state and connectivity
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.append(os.path.dirname(__file__))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Check database status"""
        try:
            from utils.db_config import get_db_path
            import sqlite3

            nba_data_db_path = get_db_path('nba_data.db')
            predictions_db_path = get_db_path('predictions.db')

            response = {
                'success': True,
                'databases': {
                    'nba_data.db': {
                        'path': nba_data_db_path,
                        'exists': os.path.exists(nba_data_db_path),
                    },
                    'predictions.db': {
                        'path': predictions_db_path,
                        'exists': os.path.exists(predictions_db_path),
                    }
                },
                'environment': {
                    'DB_PATH': os.getenv('DB_PATH', 'not set'),
                    'cwd': os.getcwd(),
                }
            }

            # Try to query nba_data.db
            if os.path.exists(nba_data_db_path):
                try:
                    conn = sqlite3.connect(nba_data_db_path)
                    cursor = conn.cursor()

                    # Check tables
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    response['databases']['nba_data.db']['tables'] = tables

                    # Count records in each table
                    counts = {}
                    for table in tables:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        counts[table] = cursor.fetchone()[0]
                    response['databases']['nba_data.db']['record_counts'] = counts

                    conn.close()
                except Exception as e:
                    response['databases']['nba_data.db']['error'] = str(e)

            # Try to import modules
            try:
                from utils import db_queries, sync_nba_data
                response['imports'] = {
                    'db_queries': 'OK',
                    'sync_nba_data': 'OK'
                }
            except Exception as e:
                response['imports'] = {'error': str(e)}

            self.send_json_response(response)

        except Exception as e:
            import traceback
            self.send_json_response({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }, 500)

    def send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
