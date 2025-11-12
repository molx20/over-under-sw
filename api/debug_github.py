"""
Debug endpoint to check GitHub configuration
"""

import os
import json
from http.server import BaseHTTPRequestHandler
from github import Github, GithubException

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Return GitHub configuration and test access"""

        # Get environment variables
        gh_token = os.getenv('GH_TOKEN', '')
        gh_repo = os.getenv('GH_REPO', '')
        gh_path = os.getenv('GH_MODEL_PATH', '')

        debug_info = {
            'env_vars': {
                'GH_TOKEN_SET': bool(gh_token),
                'GH_TOKEN_PREFIX': gh_token[:10] if gh_token else 'NOT SET',
                'GH_TOKEN_LENGTH': len(gh_token) if gh_token else 0,
                'GH_REPO': gh_repo,
                'GH_MODEL_PATH': gh_path or 'api/data/model.json'
            },
            'tests': {}
        }

        if gh_token:
            try:
                g = Github(gh_token)

                # Test 1: Get user
                try:
                    user = g.get_user()
                    debug_info['tests']['user_auth'] = {
                        'success': True,
                        'username': user.login
                    }
                except GithubException as e:
                    debug_info['tests']['user_auth'] = {
                        'success': False,
                        'error': str(e),
                        'status': e.status,
                        'data': e.data if hasattr(e, 'data') else None
                    }

                # Test 2: Get repository
                if gh_repo:
                    try:
                        repo = g.get_repo(gh_repo)
                        debug_info['tests']['repo_access'] = {
                            'success': True,
                            'full_name': repo.full_name,
                            'default_branch': repo.default_branch
                        }

                        # Test 3: Get file
                        try:
                            file_path = gh_path or 'api/data/model.json'
                            file_content = repo.get_contents(file_path)
                            debug_info['tests']['file_access'] = {
                                'success': True,
                                'path': file_path,
                                'sha': file_content.sha
                            }
                        except GithubException as e:
                            debug_info['tests']['file_access'] = {
                                'success': False,
                                'path': file_path,
                                'error': str(e),
                                'status': e.status,
                                'data': e.data if hasattr(e, 'data') else None
                            }

                    except GithubException as e:
                        debug_info['tests']['repo_access'] = {
                            'success': False,
                            'error': str(e),
                            'status': e.status,
                            'data': e.data if hasattr(e, 'data') else None
                        }

            except Exception as e:
                debug_info['tests']['github_init'] = {
                    'success': False,
                    'error': str(e)
                }

        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        self.wfile.write(json.dumps(debug_info, indent=2).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
