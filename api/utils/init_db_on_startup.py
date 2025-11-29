"""
Database initialization on startup

This script ensures the NBA data database exists and is properly initialized.
Called automatically on Railway deployment.
"""

import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_nba_data_db_if_needed():
    """Initialize NBA data database if it doesn't exist"""
    try:
        # Import after ensuring path is set up
        from api.utils.db_config import get_db_path

        nba_data_db_path = get_db_path('nba_data.db')

        # Check if database exists
        if not os.path.exists(nba_data_db_path):
            logger.info(f"NBA data database not found at {nba_data_db_path}, creating...")

            # Import and run schema initialization
            from api.utils.db_schema_nba_data import init_nba_data_db
            init_nba_data_db()

            logger.info("NBA data database created successfully")
        else:
            logger.info(f"NBA data database exists at {nba_data_db_path}")

    except Exception as e:
        logger.error(f"Error initializing NBA data database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    init_nba_data_db_if_needed()
