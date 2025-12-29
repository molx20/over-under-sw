"""
Database schema for Team Similarity Engine

Tables:
- team_similarity_scores: Pairwise similarity scores
- team_similarity_clusters: Cluster definitions
- team_cluster_assignments: Team-to-cluster mappings
- team_vs_cluster_performance: Performance stats vs each cluster
- team_feature_vectors: Normalized playstyle vectors
"""

import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), '../data/team_similarity.db')


def get_connection():
    """Get database connection with foreign keys enabled"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_schema():
    """Create all tables for Team Similarity Engine"""
    conn = get_connection()
    cursor = conn.cursor()

    # Table 1: Team Feature Vectors (20-dimensional playstyle profiles)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_feature_vectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            feature_vector TEXT NOT NULL,
            pace_norm REAL,
            three_pt_rate REAL,
            paint_scoring_rate REAL,
            ast_ratio REAL,
            def_rating_norm REAL,
            season TEXT NOT NULL,
            window_mode TEXT DEFAULT 'season',
            opponent_cluster_id INTEGER,
            games_used INTEGER,
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(team_id, season, window_mode, opponent_cluster_id)
        )
    """)

    # Migrate existing data: add new columns if missing (BEFORE creating indexes)
    try:
        cursor.execute("ALTER TABLE team_feature_vectors ADD COLUMN window_mode TEXT DEFAULT 'season'")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE team_feature_vectors ADD COLUMN opponent_cluster_id INTEGER")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE team_feature_vectors ADD COLUMN games_used INTEGER")
    except:
        pass

    # Create indexes AFTER columns exist
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_feature_team
        ON team_feature_vectors(team_id, season)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_feature_conditional
        ON team_feature_vectors(team_id, season, window_mode, opponent_cluster_id)
    """)

    # Table 2: Similarity Scores (top 5 most similar teams for each team)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_similarity_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            similar_team_id INTEGER NOT NULL,
            similarity_score REAL NOT NULL,
            rank INTEGER NOT NULL,
            season TEXT NOT NULL,
            window_mode TEXT DEFAULT 'season',
            opponent_cluster_id INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(team_id, similar_team_id, season, window_mode, opponent_cluster_id)
        )
    """)

    # Migrate existing data: add new columns if missing (BEFORE creating indexes)
    try:
        cursor.execute("ALTER TABLE team_similarity_scores ADD COLUMN window_mode TEXT DEFAULT 'season'")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE team_similarity_scores ADD COLUMN opponent_cluster_id INTEGER")
    except:
        pass

    # Create indexes AFTER columns exist
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_similarity_team
        ON team_similarity_scores(team_id, season)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_similarity_rank
        ON team_similarity_scores(team_id, rank, season)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_similarity_conditional
        ON team_similarity_scores(team_id, season, window_mode, opponent_cluster_id, rank)
    """)

    # Table 3: Cluster Definitions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_similarity_clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_id INTEGER NOT NULL,
            cluster_name TEXT NOT NULL,
            cluster_description TEXT,
            season TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cluster_id, season)
        )
    """)

    # Table 4: Team Cluster Assignments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_cluster_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            cluster_id INTEGER NOT NULL,
            distance_to_centroid REAL,
            season TEXT NOT NULL,
            secondary_cluster_id INTEGER,
            primary_fit_score REAL,
            secondary_fit_score REAL,
            confidence_label TEXT,
            confidence_score REAL,
            UNIQUE(team_id, season)
        )
    """)

    # Add new columns to existing table (safe migration)
    # SQLite will skip ALTER TABLE if column already exists (caught by try/except)
    try:
        cursor.execute("ALTER TABLE team_cluster_assignments ADD COLUMN secondary_cluster_id INTEGER")
    except:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE team_cluster_assignments ADD COLUMN primary_fit_score REAL")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE team_cluster_assignments ADD COLUMN secondary_fit_score REAL")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE team_cluster_assignments ADD COLUMN confidence_label TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE team_cluster_assignments ADD COLUMN confidence_score REAL")
    except:
        pass

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cluster_team
        ON team_cluster_assignments(team_id, season)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cluster_group
        ON team_cluster_assignments(cluster_id, season)
    """)

    # Table 5: Performance vs Cluster
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_vs_cluster_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            opponent_cluster_id INTEGER NOT NULL,
            games_played INTEGER DEFAULT 0,
            avg_pts_scored REAL,
            avg_pts_allowed REAL,
            avg_total_points REAL,
            avg_pace REAL,
            avg_paint_pts_diff REAL,
            avg_three_pt_diff REAL,
            avg_turnover_diff REAL,
            over_percentage REAL,
            under_percentage REAL,
            season TEXT NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(team_id, opponent_cluster_id, season)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cluster_perf
        ON team_vs_cluster_performance(team_id, season)
    """)

    conn.commit()
    conn.close()

    print(f"[Similarity DB] Schema initialized at {DB_PATH}")


def seed_cluster_definitions(season='2025-26'):
    """Seed the 6 playstyle clusters"""
    conn = get_connection()
    cursor = conn.cursor()

    clusters = [
        (1, "Elite Pace Pushers", "Fast-paced teams (99+ pace) with high 3PA and fastbreak scoring"),
        (2, "Paint Dominators", "Teams scoring 50%+ in the paint with elite rim pressure"),
        (3, "Three-Point Hunters", "Perimeter-heavy offenses (40%+ 3PA rate)"),
        (4, "Defensive Grinders", "Slow pace (<97), elite defense, low opponent FG%"),
        (5, "Balanced High-Assist", "High ball movement (65%+ AST ratio), balanced shot distribution"),
        (6, "ISO-Heavy", "Low assist rate (<60%), usage concentrated in star players")
    ]

    for cluster_id, name, desc in clusters:
        cursor.execute("""
            INSERT OR IGNORE INTO team_similarity_clusters
            (cluster_id, cluster_name, cluster_description, season)
            VALUES (?, ?, ?, ?)
        """, (cluster_id, name, desc, season))

    conn.commit()
    conn.close()

    print(f"[Similarity DB] Seeded {len(clusters)} cluster definitions")


if __name__ == '__main__':
    initialize_schema()
    seed_cluster_definitions()
