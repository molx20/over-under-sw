"""
GitHub API integration for persisting model.json to repository

This module handles committing the model file back to GitHub after updates.
Uses GitHub REST API v3 (via PyGithub library) for reliable serverless operation.

Required environment variables:
- GH_TOKEN: GitHub personal access token with 'repo' scope
- GH_REPO: Repository name (format: owner/repo, e.g., 'molx20/over-under-sw')
- GH_MODEL_PATH: Path to model file in repo (e.g., 'api/data/model.json')
"""

import os
import json
import base64
from typing import Dict, Optional
from github import Github, GithubException

def commit_model_to_github(model_data: Dict, commit_message: str = "Update team ratings model") -> Dict:
    """
    Commit the updated model.json to GitHub repository

    Args:
        model_data: The model JSON data to commit
        commit_message: Optional custom commit message

    Returns:
        Dict with commit information:
        {
            'success': bool,
            'commit_sha': str (if successful),
            'error': str (if failed)
        }

    Raises:
        ValueError: If required environment variables are missing
    """
    # Get environment variables
    gh_token = os.getenv('GH_TOKEN')
    gh_repo_name = os.getenv('GH_REPO')
    gh_model_path = os.getenv('GH_MODEL_PATH', 'api/data/model.json')

    # Validate environment variables
    if not gh_token:
        raise ValueError("GH_TOKEN environment variable is required")
    if not gh_repo_name:
        raise ValueError("GH_REPO environment variable is required (format: owner/repo)")

    try:
        # Initialize GitHub client
        g = Github(gh_token)
        repo = g.get_repo(gh_repo_name)

        # Convert model data to JSON string
        file_content = json.dumps(model_data, indent=2)

        # Try to get existing file to get its SHA (required for updating)
        try:
            existing_file = repo.get_contents(gh_model_path)
            file_sha = existing_file.sha

            # Update existing file
            result = repo.update_file(
                path=gh_model_path,
                message=commit_message,
                content=file_content,
                sha=file_sha,
                branch="main"
            )

            return {
                'success': True,
                'commit_sha': result['commit'].sha,
                'message': f'Updated {gh_model_path}',
                'commit_url': result['commit'].html_url
            }

        except GithubException as e:
            if e.status == 404:
                # File doesn't exist yet, create it
                result = repo.create_file(
                    path=gh_model_path,
                    message=commit_message,
                    content=file_content,
                    branch="main"
                )

                return {
                    'success': True,
                    'commit_sha': result['commit'].sha,
                    'message': f'Created {gh_model_path}',
                    'commit_url': result['commit'].html_url
                }
            else:
                raise

    except GithubException as e:
        return {
            'success': False,
            'error': f'GitHub API error: {e.data.get("message", str(e))}',
            'status': e.status
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }

def fetch_model_from_github() -> Optional[Dict]:
    """
    Fetch the model.json from GitHub repository (fallback if local file missing)

    Returns:
        Dict with model data if successful, None if failed
    """
    gh_token = os.getenv('GH_TOKEN')
    gh_repo_name = os.getenv('GH_REPO')
    gh_model_path = os.getenv('GH_MODEL_PATH', 'api/data/model.json')

    if not gh_token or not gh_repo_name:
        print("GitHub credentials not configured, cannot fetch from repo")
        return None

    try:
        g = Github(gh_token)
        repo = g.get_repo(gh_repo_name)

        # Get file contents
        file_content = repo.get_contents(gh_model_path)
        file_data = base64.b64decode(file_content.content).decode('utf-8')

        return json.loads(file_data)

    except GithubException as e:
        print(f"Failed to fetch model from GitHub: {e.data.get('message', str(e))}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching from GitHub: {str(e)}")
        return None

def validate_github_config() -> Dict:
    """
    Validate that GitHub environment variables are properly configured

    Returns:
        Dict with validation results:
        {
            'valid': bool,
            'errors': List[str]
        }
    """
    errors = []

    gh_token = os.getenv('GH_TOKEN')
    gh_repo_name = os.getenv('GH_REPO')
    gh_model_path = os.getenv('GH_MODEL_PATH')

    if not gh_token:
        errors.append("GH_TOKEN environment variable is missing")
    elif not gh_token.startswith('ghp_') and not gh_token.startswith('github_pat_'):
        errors.append("GH_TOKEN appears to be invalid (should start with ghp_ or github_pat_)")

    if not gh_repo_name:
        errors.append("GH_REPO environment variable is missing")
    elif '/' not in gh_repo_name:
        errors.append("GH_REPO should be in format 'owner/repo'")

    if not gh_model_path:
        errors.append("GH_MODEL_PATH environment variable is missing (defaulting to 'api/data/model.json')")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'config': {
            'token_set': bool(gh_token),
            'repo': gh_repo_name,
            'path': gh_model_path or 'api/data/model.json'
        }
    }
