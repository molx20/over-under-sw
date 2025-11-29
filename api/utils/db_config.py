"""
Database Configuration Module

Centralized database path configuration that supports:
- Local development: Uses relative paths in api/data/
- Railway production: Uses persistent volume at /data/

Environment Variables:
- DB_PATH: Base directory for database files
  * Development: Not set (defaults to api/data/)
  * Production: /data (Railway volume mount)

Usage:
    from api.utils.db_config import get_db_path

    predictions_db = get_db_path('predictions.db')
    rankings_db = get_db_path('team_rankings.db')
"""

import os


def get_db_path(db_filename: str) -> str:
    """
    Get the full path for a database file.

    Args:
        db_filename: Name of the database file (e.g., 'predictions.db')

    Returns:
        Absolute path to the database file

    Examples:
        # Development (DB_PATH not set)
        get_db_path('predictions.db')
        # -> /path/to/project/api/data/predictions.db

        # Production (DB_PATH=/data)
        get_db_path('predictions.db')
        # -> /data/predictions.db
    """
    # Get base directory from environment variable
    # Default to api/data/ for local development
    base_dir = os.environ.get('DB_PATH')

    if base_dir is None:
        # Local development: use api/data/ directory
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

    # Ensure directory exists
    os.makedirs(base_dir, exist_ok=True)

    # Return full path to database file
    return os.path.join(base_dir, db_filename)
