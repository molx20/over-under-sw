"""
SQLite Database Helper for NBA Prediction Storage

This module handles all database operations for storing:
- Pre-game predictions
- Sportsbook lines
- Actual game results
- Error metrics and learning outcomes
"""

import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Database file location
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'predictions.db')


def get_connection():
    """Get a connection to the SQLite database."""
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


def init_db():
    """Initialize the database schema if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create game_predictions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT UNIQUE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            game_date TEXT NOT NULL,

            -- Pre-game predictions (from enhanced model)
            pred_total REAL NOT NULL,
            pred_home REAL NOT NULL,
            pred_away REAL NOT NULL,

            -- Sportsbook line (manually entered)
            sportsbook_total_line REAL,

            -- Actual results (filled after game completes)
            actual_home REAL,
            actual_away REAL,
            actual_total REAL,

            -- Error metrics (computed during learning)
            model_error REAL,
            line_error REAL,
            model_abs_error REAL,
            line_abs_error REAL,
            model_beat_line INTEGER,  -- SQLite uses INTEGER for boolean (0/1)

            -- Timestamps
            prediction_created_at TEXT NOT NULL,
            line_submitted_at TEXT,
            learning_completed_at TEXT,

            -- Model snapshot (for debugging)
            model_version TEXT
        )
    ''')

    # Create model_performance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS model_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            games_predicted INTEGER,
            avg_model_error REAL,
            avg_line_error REAL,
            model_win_rate REAL,
            created_at TEXT NOT NULL
        )
    ''')

    # Create index on game_id for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_game_id ON game_predictions(game_id)
    ''')

    # Create index on game_date for analytics
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_game_date ON game_predictions(game_date)
    ''')

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

    # Run migrations for feature-enhanced predictions
    try:
        from api.utils.db_migrations import migrate_to_v3_features
        migrate_to_v3_features()
    except ImportError:
        try:
            from db_migrations import migrate_to_v3_features
            migrate_to_v3_features()
        except:
            print("Warning: Could not run migrations, db_migrations module not found")


def save_prediction(
    game_id: str,
    home_team: str,
    away_team: str,
    game_date: str,
    pred_home: float,
    pred_away: float,
    pred_total: float,
    model_version: str = "2.0",
    base_prediction: float = None,
    feature_correction: float = None,
    feature_vector: str = None,
    feature_metadata: str = None
) -> Dict:
    """
    Save a pre-game prediction to the database.

    Args:
        game_id: Unique NBA game ID (e.g., "0022500123")
        home_team: Home team tricode (e.g., "BOS")
        away_team: Away team tricode (e.g., "LAL")
        game_date: Game date in YYYY-MM-DD format
        pred_home: Predicted home team score
        pred_away: Predicted away team score
        pred_total: Predicted total points (base + feature correction)
        model_version: Model version string (default "2.0")
        base_prediction: Base prediction from complex engine (optional)
        feature_correction: Feature-based correction amount (optional)
        feature_vector: JSON string of feature vector (optional)
        feature_metadata: JSON string of feature metadata (optional)

    Returns:
        Dict with success status and saved data
    """
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    try:
        cursor.execute('''
            INSERT INTO game_predictions (
                game_id, home_team, away_team, game_date,
                pred_total, pred_home, pred_away,
                base_prediction, feature_correction,
                feature_vector, feature_metadata,
                prediction_created_at, model_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            game_id, home_team, away_team, game_date,
            pred_total, pred_home, pred_away,
            base_prediction, feature_correction,
            feature_vector, feature_metadata,
            now, model_version
        ))

        conn.commit()

        return {
            "success": True,
            "game_id": game_id,
            "prediction": {
                "home": pred_home,
                "away": pred_away,
                "total": pred_total,
                "base": base_prediction,
                "correction": feature_correction
            },
            "saved_at": now
        }

    except sqlite3.IntegrityError:
        # Game already has a prediction
        return {
            "success": False,
            "error": f"Prediction for game {game_id} already exists. Use update instead."
        }

    finally:
        conn.close()


def submit_line(game_id: str, sportsbook_total_line: float) -> Dict:
    """
    Submit the sportsbook closing total line for a game.

    Args:
        game_id: Unique NBA game ID
        sportsbook_total_line: The over/under line from sportsbooks

    Returns:
        Dict with success status
    """
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    cursor.execute('''
        UPDATE game_predictions
        SET sportsbook_total_line = ?, line_submitted_at = ?
        WHERE game_id = ?
    ''', (sportsbook_total_line, now, game_id))

    if cursor.rowcount == 0:
        conn.close()
        return {
            "success": False,
            "error": f"No prediction found for game {game_id}. Save prediction first."
        }

    conn.commit()
    conn.close()

    return {
        "success": True,
        "game_id": game_id,
        "line": sportsbook_total_line,
        "submitted_at": now
    }


def update_actual_results(
    game_id: str,
    actual_home: float,
    actual_away: float
) -> Dict:
    """
    Update the actual game results after the game finishes.

    Args:
        game_id: Unique NBA game ID
        actual_home: Actual home team final score
        actual_away: Actual away team final score

    Returns:
        Dict with success status
    """
    conn = get_connection()
    cursor = conn.cursor()

    actual_total = actual_home + actual_away

    cursor.execute('''
        UPDATE game_predictions
        SET actual_home = ?, actual_away = ?, actual_total = ?
        WHERE game_id = ?
    ''', (actual_home, actual_away, actual_total, game_id))

    if cursor.rowcount == 0:
        conn.close()
        return {
            "success": False,
            "error": f"No prediction found for game {game_id}"
        }

    conn.commit()
    conn.close()

    return {
        "success": True,
        "game_id": game_id,
        "actual_total": actual_total
    }


def update_error_metrics(game_id: str, metrics: Dict) -> Dict:
    """
    Update error metrics after learning is complete.

    Args:
        game_id: Unique NBA game ID
        metrics: Dict containing:
            - model_error: float
            - line_error: float
            - model_abs_error: float
            - line_abs_error: float
            - model_beat_line: bool

    Returns:
        Dict with success status
    """
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    cursor.execute('''
        UPDATE game_predictions
        SET
            model_error = ?,
            line_error = ?,
            model_abs_error = ?,
            line_abs_error = ?,
            model_beat_line = ?,
            learning_completed_at = ?
        WHERE game_id = ?
    ''', (
        metrics['model_error'],
        metrics['line_error'],
        metrics['model_abs_error'],
        metrics['line_abs_error'],
        1 if metrics['model_beat_line'] else 0,
        now,
        game_id
    ))

    if cursor.rowcount == 0:
        conn.close()
        return {
            "success": False,
            "error": f"No prediction found for game {game_id}"
        }

    conn.commit()
    conn.close()

    return {
        "success": True,
        "game_id": game_id,
        "learning_completed_at": now
    }


def get_prediction(game_id: str) -> Optional[Dict]:
    """
    Get prediction data for a specific game.

    Args:
        game_id: Unique NBA game ID

    Returns:
        Dict with prediction data or None if not found
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM game_predictions WHERE game_id = ?
    ''', (game_id,))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)


def get_all_predictions(limit: int = 100, offset: int = 0) -> List[Dict]:
    """
    Get all predictions, ordered by most recent first.

    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip

    Returns:
        List of prediction dictionaries
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM game_predictions
        ORDER BY prediction_created_at DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_predictions_with_learning(limit: int = 50) -> List[Dict]:
    """
    Get predictions that have completed the learning cycle.

    Args:
        limit: Maximum number of records to return

    Returns:
        List of prediction dictionaries with learning metrics
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM game_predictions
        WHERE learning_completed_at IS NOT NULL
        ORDER BY learning_completed_at DESC
        LIMIT ?
    ''', (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_model_performance_stats(days: int = 30) -> Dict:
    """
    Calculate model performance statistics for recent games.

    Args:
        days: Number of days to look back

    Returns:
        Dict with performance metrics
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get all completed predictions with learning
    cursor.execute('''
        SELECT
            COUNT(*) as total_games,
            AVG(model_abs_error) as avg_model_error,
            AVG(line_abs_error) as avg_line_error,
            SUM(CASE WHEN model_beat_line = 1 THEN 1 ELSE 0 END) as model_wins
        FROM game_predictions
        WHERE learning_completed_at IS NOT NULL
        AND datetime(learning_completed_at) >= datetime('now', '-' || ? || ' days')
    ''', (days,))

    row = cursor.fetchone()
    conn.close()

    if row is None or row['total_games'] == 0:
        return {
            "total_games": 0,
            "avg_model_error": None,
            "avg_line_error": None,
            "model_win_rate": None
        }

    total_games = row['total_games']
    model_wins = row['model_wins'] or 0

    return {
        "total_games": total_games,
        "avg_model_error": round(row['avg_model_error'], 2) if row['avg_model_error'] else None,
        "avg_line_error": round(row['avg_line_error'], 2) if row['avg_line_error'] else None,
        "model_win_rate": round((model_wins / total_games) * 100, 1) if total_games > 0 else None
    }


def save_performance_snapshot(date: str = None) -> Dict:
    """
    Save a snapshot of model performance for historical tracking.

    Args:
        date: Date string (YYYY-MM-DD). Defaults to today.

    Returns:
        Dict with saved performance data
    """
    if date is None:
        date = datetime.utcnow().strftime('%Y-%m-%d')

    stats = get_model_performance_stats(days=30)

    if stats['total_games'] == 0:
        return {
            "success": False,
            "error": "No completed predictions to snapshot"
        }

    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    cursor.execute('''
        INSERT INTO model_performance (
            date, games_predicted, avg_model_error, avg_line_error,
            model_win_rate, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        date,
        stats['total_games'],
        stats['avg_model_error'],
        stats['avg_line_error'],
        stats['model_win_rate'],
        now
    ))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "date": date,
        "stats": stats,
        "saved_at": now
    }
