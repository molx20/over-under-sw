"""
Flask server for NBA Over/Under predictor
Railway deployment
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the api directory to path
sys.path.append(os.path.dirname(__file__))

from api.utils.db_queries import get_todays_games, get_matchup_data, get_all_teams, get_team_stats_with_ranks
from api.utils.prediction_engine import predict_game_total
from api.utils import db
from api.utils import team_ratings_model
from api.utils import team_rankings
from api.utils import db_queries
from api.utils.performance import create_timing_middleware
from api.utils.matchup_summary_cache import get_or_generate_summary
import json
import os

# Load model parameters on startup
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'api', 'data', 'model.json')
try:
    with open(MODEL_PATH, 'r') as f:
        model_params = json.load(f)
    print(f"[server] Loaded model parameters: version {model_params.get('version', 'unknown')}")
except Exception as e:
    print(f"[server] Warning: Could not load model.json: {e}")
    model_params = {
        'parameters': {'recent_games_n': 10},
        'feature_weights': {}
    }

app = Flask(__name__, static_folder='dist', static_url_path='')
CORS(app)

# Enable performance logging middleware
create_timing_middleware(app)

# Add cache control headers to prevent browser caching issues on deployment
@app.after_request
def add_cache_headers(response):
    """
    Add cache control headers to prevent stale frontend after deployments.

    Strategy:
    - index.html: No cache (always fetch fresh)
    - JS/CSS assets: Cache for 1 year (Vite adds hashes to filenames)
    - API responses: No cache (always fresh data)
    """
    # Don't cache index.html - always fetch fresh on reload
    if request.path == '/' or request.path.endswith('.html'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

    # Cache JS/CSS assets aggressively (Vite adds content hashes to filenames)
    elif request.path.endswith(('.js', '.css', '.woff', '.woff2', '.ttf', '.eot')):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'

    # Don't cache API responses
    elif request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

    # Images can be cached for a day
    elif request.path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico')):
        response.headers['Cache-Control'] = 'public, max-age=86400'

    return response

# Initialize database on startup
db.init_db()

# Self-learning disabled - using deterministic predictions
print("[startup] Running in deterministic mode (no automated learning)")

# Force WAL mode and verify connection health on all database pools
print("[startup] Initializing database connections...")
try:
    from api.utils.connection_pool import get_db_pool

    for db_name in ['predictions', 'team_rankings']:
        pool = get_db_pool(db_name)
        with pool.get_connection() as conn:
            # Force WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            # Verify connection is healthy
            conn.execute("SELECT 1")
            print(f"[startup] ✓ {db_name} database ready (WAL mode enabled)")
except Exception as e:
    print(f"[startup] Warning: Database initialization had issues: {e}")

# In-memory prediction cache
_prediction_cache = {}
_CACHE_MAX_SIZE = 128

def get_cached_prediction(home_team_id, away_team_id, betting_line, game_id=None):
    """
    Get prediction from cache or generate new one.

    Returns:
        tuple: (prediction_dict, matchup_data_dict) or (None, None) on error
    """
    cache_key = (int(home_team_id), int(away_team_id), betting_line)

    if cache_key in _prediction_cache:
        print(f'[cache] HIT: Returning cached prediction for game {away_team_id}@{home_team_id} (line: {betting_line})')
        cached_prediction, cached_matchup_data = _prediction_cache[cache_key]
        return cached_prediction, cached_matchup_data

    print(f'[cache] MISS: Generating prediction for game {away_team_id}@{home_team_id} (line: {betting_line})')

    matchup_data = get_matchup_data(home_team_id, away_team_id)
    if matchup_data is None:
        print('[cache] ERROR: Failed to fetch matchup data')
        return None, None

    # Get team abbreviations for trend analysis
    all_teams = get_all_teams()
    home_team_info = next((t for t in all_teams if t['id'] == int(home_team_id)), None)
    away_team_info = next((t for t in all_teams if t['id'] == int(away_team_id)), None)

    prediction = predict_game_total(
        matchup_data['home'],
        matchup_data['away'],
        betting_line,
        home_team_id=int(home_team_id),
        away_team_id=int(away_team_id),
        home_team_abbr=home_team_info['abbreviation'] if home_team_info else None,
        away_team_abbr=away_team_info['abbreviation'] if away_team_info else None,
        season='2025-26',
        game_id=game_id
    )

    if len(_prediction_cache) >= _CACHE_MAX_SIZE:
        oldest_key = next(iter(_prediction_cache))
        print(f'[cache] EVICT: Removing oldest entry {oldest_key}')
        _prediction_cache.pop(oldest_key)

    # Cache both prediction and matchup_data to avoid duplicate API calls
    _prediction_cache[cache_key] = (prediction, matchup_data)
    print(f'[cache] STORE: Cached prediction and matchup data for {cache_key}')

    return prediction, matchup_data

@app.route('/')
def index():
    """Serve the React app"""
    return app.send_static_file('index.html')

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

@app.route('/api/admin/sync-status', methods=['GET'])
def admin_sync_status():
    """Check if a sync operation is currently running"""
    from api.utils.sync_lock import is_sync_in_progress, get_current_sync, get_sync_history

    return jsonify({
        'sync_in_progress': is_sync_in_progress(),
        'current_sync': get_current_sync(),
        'recent_syncs': get_sync_history(limit=5)
    })


@app.route('/api/admin/sync', methods=['POST'])
def admin_sync():
    """Admin endpoint to trigger data sync (protected by secret token)"""
    import threading
    from api.utils.sync_nba_data import sync_all

    # Check authentication
    auth_header = request.headers.get('Authorization', '')
    expected_token = os.environ.get('ADMIN_SYNC_SECRET', '')

    if not expected_token:
        return jsonify({'error': 'Admin sync not configured'}), 500

    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid Authorization header'}), 401

    provided_token = auth_header.replace('Bearer ', '').strip()

    if provided_token != expected_token:
        return jsonify({'error': 'Invalid authentication token'}), 401

    # Parse request body
    try:
        data = request.get_json() or {}
        sync_type = data.get('sync_type', 'full')
        season = data.get('season', '2025-26')
        async_mode = data.get('async', True)  # Run async by default to avoid timeout
    except Exception as e:
        return jsonify({'error': f'Invalid request body: {str(e)}'}), 400

    # Run sync in background thread if async mode
    if async_mode:
        def background_sync():
            try:
                print(f'[admin/sync] Starting background {sync_type} sync for {season}')
                result = sync_all(season=season, triggered_by='admin_api')
                print(f'[admin/sync] Background sync completed: {result}')
            except Exception as e:
                print(f'[admin/sync] Background sync failed: {e}')
                import traceback
                traceback.print_exc()

        thread = threading.Thread(target=background_sync, daemon=True)
        thread.start()

        print(f'[admin/sync] Started background sync thread for {season}')
        return jsonify({
            'success': True,
            'message': 'Sync started in background',
            'season': season,
            'sync_type': sync_type,
            'note': 'Check server logs for completion status'
        }), 202  # 202 Accepted
    else:
        # Synchronous mode (may timeout on Railway)
        try:
            print(f'[admin/sync] Starting synchronous {sync_type} sync for {season}')
            result = sync_all(season=season, triggered_by='admin_api')
            print(f'[admin/sync] Sync completed: {result}')
            return jsonify(result), 200
        except Exception as e:
            print(f'[admin/sync] Sync failed: {e}')
            return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/debug/game-logs', methods=['GET'])
def debug_game_logs():
    """Debug endpoint to inspect stored game logs and pace calculations"""
    import sqlite3

    try:
        season = request.args.get('season', '2025-26')
        limit = int(request.args.get('limit', '20'))

        conn = sqlite3.connect('api/data/nba_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query games with team names
        cursor.execute('''
            SELECT
                g.id as game_id,
                g.game_date,
                g.season,
                ht.full_name as home_team_name,
                ht.team_abbreviation as home_team_abbr,
                at.full_name as away_team_name,
                at.team_abbreviation as away_team_abbr,
                g.home_score,
                g.away_score,
                g.actual_total_points,
                g.game_pace,
                g.status
            FROM games g
            JOIN nba_teams ht ON g.home_team_id = ht.team_id
            JOIN nba_teams at ON g.away_team_id = at.team_id
            WHERE g.season = ?
            ORDER BY g.game_date DESC
            LIMIT ?
        ''', (season, limit))

        games = cursor.fetchall()

        # For each game, get team stats from team_game_logs
        results = []
        for game in games:
            game_id = game['game_id']

            # Get team logs for this game
            cursor.execute('''
                SELECT
                    tgl.team_id,
                    t.full_name as team_name,
                    t.team_abbreviation,
                    tgl.is_home,
                    tgl.team_pts as points,
                    tgl.assists,
                    tgl.turnovers,
                    tgl.fga,
                    tgl.fta,
                    tgl.offensive_rebounds as orb,
                    tgl.pace,
                    tgl.steals,
                    tgl.blocks,
                    tgl.fast_break_points,
                    tgl.points_in_paint,
                    tgl.points_off_turnovers
                FROM team_game_logs tgl
                JOIN nba_teams t ON tgl.team_id = t.team_id
                WHERE tgl.game_id = ?
                ORDER BY tgl.is_home DESC
            ''', (game_id,))

            team_stats = [dict(row) for row in cursor.fetchall()]

            results.append({
                'game_id': game['game_id'],
                'game_date': game['game_date'],
                'season': game['season'],
                'home_team': {
                    'name': game['home_team_name'],
                    'abbreviation': game['home_team_abbr']
                },
                'away_team': {
                    'name': game['away_team_name'],
                    'abbreviation': game['away_team_abbr']
                },
                'home_score': game['home_score'],
                'away_score': game['away_score'],
                'actual_total_points': game['actual_total_points'],
                'game_pace': game['game_pace'],
                'status': game['status'],
                'team_stats': team_stats
            })

        conn.close()

        return jsonify({
            'success': True,
            'season': season,
            'count': len(results),
            'games': results
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/games')
def get_games():
    """Get all games for the most relevant date (deterministic, DB-first)"""
    from api.utils.performance import log_slow_operation
    import sqlite3
    import os

    try:
        # Get optional date parameter from query string or localStorage
        requested_date = request.args.get('date')

        with log_slow_operation("Fetch games (smart date selection)", threshold_ms=1000):
            # Define Mountain Time with proper DST handling
            # America/Denver automatically switches between MST (UTC-8) and MDT (UTC-7)
            mt_tz = ZoneInfo("America/Denver")
            mt_now = datetime.now(mt_tz)
            today_mt = mt_now.strftime('%Y-%m-%d')

            # Connect to database
            db_path = os.path.join(os.path.dirname(__file__), 'api/data/nba_data.db')
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            selected_date = None
            date_selection_reason = None

            # Determine current NBA season (use 2025-26 for now - could be dynamic later)
            current_season = '2025-26'

            # STEP 1: If user explicitly requested a date, try to use it
            if requested_date:
                cursor.execute('''
                    SELECT COUNT(*) as count FROM todays_games
                    WHERE game_date = ? AND season = ?
                ''', (requested_date, current_season))
                row = cursor.fetchone()
                if row and row['count'] > 0:
                    selected_date = requested_date
                    date_selection_reason = f"user_requested (found {row['count']} games)"
                    print(f'[games] Using user-requested date: {requested_date}')

            # STEP 2: Check if today (MT) has games
            if not selected_date:
                cursor.execute('''
                    SELECT COUNT(*) as count FROM todays_games
                    WHERE game_date = ? AND season = ?
                ''', (today_mt, current_season))
                row = cursor.fetchone()
                if row and row['count'] > 0:
                    selected_date = today_mt
                    date_selection_reason = f"today_mt_has_games ({row['count']} games)"
                    print(f'[games] Today (MT) has {row["count"]} games, using today')

            # STEP 3: Find the most recent date that has games
            if not selected_date:
                cursor.execute('''
                    SELECT game_date, COUNT(*) as count
                    FROM todays_games
                    WHERE season = ?
                    GROUP BY game_date
                    ORDER BY game_date DESC
                    LIMIT 1
                ''', (current_season,))
                row = cursor.fetchone()
                if row:
                    selected_date = row['game_date']
                    date_selection_reason = f"latest_available_date ({row['count']} games)"
                    print(f'[games] No games today, showing latest slate: {selected_date} ({row["count"]} games)')
                else:
                    # STEP 4: Absolute fallback - no games in DB at all
                    selected_date = today_mt
                    date_selection_reason = "fallback_today_mt (empty_db)"
                    print(f'[games] WARNING: No games found in database, using today as fallback')

            # Fetch games for the selected date
            cursor.execute('''
                SELECT * FROM todays_games
                WHERE game_date = ? AND season = ?
                ORDER BY game_time_utc
            ''', (selected_date, current_season))

            rows = cursor.fetchall()
            conn.close()

            print(f'[games] Selected date: {selected_date}, reason: {date_selection_reason}, games: {len(rows)}')

            # Convert to format expected by frontend
            games = []
            for row in rows:
                # Extract game_type safely (column may not exist in old data)
                try:
                    game_type = row['game_type'] if row['game_type'] else 'Unknown'
                except (KeyError, IndexError):
                    game_type = 'Unknown'

                games.append({
                    'game_id': row['game_id'],
                    'game_date': row['game_date'],
                    'game_status': row['game_status_text'],
                    'home_team_id': row['home_team_id'],
                    'home_team_name': row['home_team_name'],
                    'home_team_score': row['home_team_score'] or 0,
                    'away_team_id': row['away_team_id'],
                    'away_team_name': row['away_team_name'],
                    'away_team_score': row['away_team_score'] or 0,
                    'game_type': game_type,
                })

            print(f'[games] Loaded {len(games)} games from database for {selected_date}')

            # Apply game filtering if enabled (Regular Season + NBA Cup only)
            filter_mode = os.environ.get('GAME_FILTER_MODE', 'DISABLED')
            if filter_mode == 'REGULAR_PLUS_ALL_CUP':
                from api.utils.game_classifier import filter_eligible_games

                unfiltered_count = len(games)
                filter_result = filter_eligible_games(games)
                games = filter_result['filtered_games']
                stats = filter_result['stats']

                # Comprehensive logging
                print(f'[games] FILTER ENABLED: {filter_mode}')
                print(f'[games]   Unfiltered: {stats["unfiltered_count"]}')
                print(f'[games]   Filtered: {stats["filtered_count"]}')
                print(f'[games]   Regular Season: {stats["regular_season_count"]}')
                print(f'[games]   NBA Cup: {stats["nba_cup_count"]}')
                print(f'[games]   Excluded: {stats["excluded_count"]}')
                if stats['excluded_types']:
                    for game_type, count in stats['excluded_types'].items():
                        print(f'[games]     - {game_type}: {count}')

                # Log date range of filtered games
                if games:
                    dates = [g['game_date'] for g in games]
                    print(f'[games]   Date range: {min(dates)} to {max(dates)}')
            else:
                print(f'[games] FILTER DISABLED (mode: {filter_mode})')

        games_with_predictions = []
        for game in games:
            games_with_predictions.append({
                'game_id': game['game_id'],
                'home_team': {
                    'id': game['home_team_id'],
                    'name': game['home_team_name'],
                    'abbreviation': game['home_team_name'],
                    'score': game['home_team_score'],
                },
                'away_team': {
                    'id': game['away_team_id'],
                    'name': game['away_team_name'],
                    'abbreviation': game['away_team_name'],
                    'score': game['away_team_score'],
                },
                'game_time': game['game_status'],
                'game_status': game['game_status'],
                'prediction': None,
            })

        response = {
            'success': True,
            'date': selected_date,
            'date_selection_reason': date_selection_reason,
            'today_mt': today_mt,
            'games': games_with_predictions,
            'count': len(games_with_predictions),
            'last_updated': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        }

        # Add caching headers for faster subsequent loads
        resp = jsonify(response)
        resp.cache_control.max_age = 30  # Cache for 30 seconds in browser
        resp.cache_control.public = True
        return resp

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/game_detail')
def game_detail():
    """Get detailed game information"""
    try:
        game_id = request.args.get('game_id')

        if not game_id:
            print('[game_detail] ERROR: Missing game_id parameter')
            return jsonify({
                'success': False,
                'error': 'Missing game_id parameter'
            }), 400

        print(f'[game_detail] Fetching detail for game {game_id}')

        games = get_todays_games()

        if not games:
            print('[game_detail] ERROR: No games available from NBA API')
            return jsonify({
                'success': False,
                'error': 'No games available today'
            }), 404

        game = next((g for g in games if str(g.get('game_id')) == str(game_id)), None)

        if not game:
            print(f'[game_detail] ERROR: Game {game_id} not found in today\'s games')
            return jsonify({
                'success': False,
                'error': f'Game {game_id} not found'
            }), 404

        print(f'[game_detail] Found game: {game.get("away_team_name")} @ {game.get("home_team_name")}')

        home_team_id = game['home_team_id']
        away_team_id = game['away_team_id']

        betting_line_str = request.args.get('betting_line')
        betting_line = float(betting_line_str) if betting_line_str else None

        print(f'[game_detail] Fetching prediction for teams {home_team_id} vs {away_team_id} (betting_line: {betting_line})')
        prediction, matchup_data = get_cached_prediction(int(home_team_id), int(away_team_id), betting_line, game_id=game_id)

        if prediction is None or matchup_data is None:
            print('[game_detail] ERROR: Failed to generate prediction or fetch matchup data')
            return jsonify({
                'success': False,
                'error': 'The NBA API is currently slow or unavailable. Please try again in a moment.'
            }), 500

        print(f'[game_detail] Prediction ready: {prediction.get("recommendation")}')

        all_teams = get_all_teams()
        home_team_info = next((t for t in all_teams if t['id'] == int(home_team_id)), {})
        away_team_info = next((t for t in all_teams if t['id'] == int(away_team_id)), {})

        home_overall = matchup_data['home']['stats'].get('overall', {}) if matchup_data['home'].get('stats') else {}
        away_overall = matchup_data['away']['stats'].get('overall', {}) if matchup_data['away'].get('stats') else {}
        home_adv = matchup_data['home'].get('advanced') or {}
        away_adv = matchup_data['away'].get('advanced') or {}
        home_opp = matchup_data['home'].get('opponent') or {}
        away_opp = matchup_data['away'].get('opponent') or {}

        # Generate or retrieve cached matchup summary (cache-first logic)
        print(f'[game_detail] Generating matchup summary for game {game_id}')
        matchup_summary = get_or_generate_summary(
            game_id=game_id,
            prediction=prediction,
            matchup_data=matchup_data,
            home_team=home_team_info,
            away_team=away_team_info
        )

        # Get recent games with ALL fields needed for War Room
        home_recent_games_full = matchup_data['home'].get('recent_games', [])[:10]
        away_recent_games_full = matchup_data['away'].get('recent_games', [])[:10]

        # Calculate advanced stats from game logs for War Room indicators
        def calculate_advanced_stats_from_games(all_games):
            """Calculate paint pts, assist%, and turnover% from game logs"""
            if not all_games or len(all_games) == 0:
                return {
                    'paint_pts_per_game': 0,
                    'ast_pct': 0,
                    'tov_pct': 0
                }

            # Use all available games for season averages
            paint_pts = [g.get('PTS_PAINT', 0) or 0 for g in all_games if g.get('PTS_PAINT')]
            assists = [g.get('AST', 0) or 0 for g in all_games if g.get('AST')]
            turnovers = [g.get('TOV', 0) or 0 for g in all_games if g.get('TOV')]
            fg_made = [g.get('FGM', 0) or 0 for g in all_games if g.get('FGM')]

            avg_paint = sum(paint_pts) / len(paint_pts) if paint_pts else 0
            avg_ast = sum(assists) / len(assists) if assists else 0
            avg_tov = sum(turnovers) / len(turnovers) if turnovers else 0
            avg_fgm = sum(fg_made) / len(fg_made) if fg_made else 0

            # Simplified percentage calculations (actual formula is more complex)
            ast_pct = (avg_ast / (avg_fgm + 0.0001)) * 100  # Avoid division by zero
            tov_pct = (avg_tov / (avg_fgm + avg_tov + 0.0001)) * 100

            return {
                'paint_pts_per_game': round(avg_paint, 1),
                'ast_pct': round(ast_pct, 1),
                'tov_pct': round(tov_pct, 1)
            }

        home_advanced = calculate_advanced_stats_from_games(matchup_data['home'].get('recent_games', []))
        away_advanced = calculate_advanced_stats_from_games(matchup_data['away'].get('recent_games', []))

        # Calculate scoring environment (deterministic classification)
        from api.utils.scoring_environment import calculate_scoring_environment
        scoring_environment = calculate_scoring_environment(
            home_pace=home_adv.get('PACE', 100),
            away_pace=away_adv.get('PACE', 100),
            home_ortg=home_adv.get('OFF_RATING', 105),
            away_ortg=away_adv.get('OFF_RATING', 105),
            home_3p_pct=home_overall.get('FG3_PCT', 0) * 100 if home_overall.get('FG3_PCT') else None,
            away_3p_pct=away_overall.get('FG3_PCT', 0) * 100 if away_overall.get('FG3_PCT') else None
        )

        response = {
            'success': True,
            'home_team': {
                'id': home_team_id,
                'name': home_team_info.get('full_name', 'Home Team'),
                'abbreviation': home_team_info.get('abbreviation', 'HOM'),
            },
            'away_team': {
                'id': away_team_id,
                'name': away_team_info.get('full_name', 'Away Team'),
                'abbreviation': away_team_info.get('abbreviation', 'AWY'),
            },
            'prediction': prediction,
            'matchup_summary': matchup_summary,
            'scoring_environment': scoring_environment,
            'home_stats': {
                # Use field names that match frontend expectations
                'ppg': round(home_overall.get('PTS', 0), 1),
                'fg_pct': round(home_overall.get('FG_PCT', 0) * 100, 1),
                'fg3_pct': round(home_overall.get('FG3_PCT', 0) * 100, 1),
                'ft_pct': round(home_overall.get('FT_PCT', 0) * 100, 1),
                'opp_ppg': round(home_opp.get('OPP_PTS', 0), 1),
                'opp_fg3_pct': round(home_opp.get('OPP_FG3_PCT', 0) * 100, 1) if home_opp.get('OPP_FG3_PCT') else 0,
                'opp_paint_pts_per_game': home_advanced.get('paint_pts_per_game', 0),  # From game logs
                'wins': home_overall.get('W', 0),
                'losses': home_overall.get('L', 0),
                'off_rating': round(home_adv.get('OFF_RATING', 0), 1),  # Changed from 'ortg'
                'def_rating': round(home_adv.get('DEF_RATING', 0), 1),  # Changed from 'drtg'
                'pace': round(home_adv.get('PACE', 0), 1),
                'net_rtg': round(home_adv.get('NET_RATING', 0), 1),
                'ast': round(home_overall.get('AST', 0), 1),
                'tov': round(home_overall.get('TOV', 0), 1),
                'fga': round(home_overall.get('FGA', 0), 1),
                'fta': round(home_overall.get('FTA', 0), 1),
                'fg3a': round(home_overall.get('FG3A', 0), 1),
                # Additional fields for MatchupIndicators
                'fg3a_per_game': round(home_overall.get('FG3A', 0), 1),
                'fta_per_game': round(home_overall.get('FTA', 0), 1),
                'paint_pts_per_game': home_advanced.get('paint_pts_per_game', 0),
                'ast_pct': home_advanced.get('ast_pct', 0),
                'tov_pct': home_advanced.get('tov_pct', 0),
            },
            'away_stats': {
                # Use field names that match frontend expectations
                'ppg': round(away_overall.get('PTS', 0), 1),
                'fg_pct': round(away_overall.get('FG_PCT', 0) * 100, 1),
                'fg3_pct': round(away_overall.get('FG3_PCT', 0) * 100, 1),
                'ft_pct': round(away_overall.get('FT_PCT', 0) * 100, 1),
                'opp_ppg': round(away_opp.get('OPP_PTS', 0), 1),
                'opp_fg3_pct': round(away_opp.get('OPP_FG3_PCT', 0) * 100, 1) if away_opp.get('OPP_FG3_PCT') else 0,
                'opp_paint_pts_per_game': away_advanced.get('paint_pts_per_game', 0),  # From game logs
                'wins': away_overall.get('W', 0),
                'losses': away_overall.get('L', 0),
                'off_rating': round(away_adv.get('OFF_RATING', 0), 1),  # Changed from 'ortg'
                'def_rating': round(away_adv.get('DEF_RATING', 0), 1),  # Changed from 'drtg'
                'pace': round(away_adv.get('PACE', 0), 1),
                'net_rtg': round(away_adv.get('NET_RATING', 0), 1),
                'ast': round(away_overall.get('AST', 0), 1),
                'tov': round(away_overall.get('TOV', 0), 1),
                'fga': round(away_overall.get('FGA', 0), 1),
                'fta': round(away_overall.get('FTA', 0), 1),
                'fg3a': round(away_overall.get('FG3A', 0), 1),
                # Additional fields for MatchupIndicators
                'fg3a_per_game': round(away_overall.get('FG3A', 0), 1),
                'fta_per_game': round(away_overall.get('FTA', 0), 1),
                'paint_pts_per_game': away_advanced.get('paint_pts_per_game', 0),
                'ast_pct': away_advanced.get('ast_pct', 0),
                'tov_pct': away_advanced.get('tov_pct', 0),
            },
            'home_recent_games': [
                {
                    'matchup': game.get('MATCHUP', ''),
                    'team_pts': game.get('PTS', 0),
                    'opp_pts': game.get('OPP_PTS', 0),
                    'result': game.get('WL', ''),
                    'off_rating': game.get('OFF_RATING', 0),
                    'def_rating': game.get('DEF_RATING', 0),
                    'pace': game.get('PACE', 0),
                    'fg3_pct': game.get('FG3_PCT', 0) * 100 if game.get('FG3_PCT') else 0,
                    'game_date': game.get('GAME_DATE', ''),
                }
                for game in home_recent_games_full
            ],
            'away_recent_games': [
                {
                    'matchup': game.get('MATCHUP', ''),
                    'team_pts': game.get('PTS', 0),
                    'opp_pts': game.get('OPP_PTS', 0),
                    'result': game.get('WL', ''),
                    'off_rating': game.get('OFF_RATING', 0),
                    'def_rating': game.get('DEF_RATING', 0),
                    'pace': game.get('PACE', 0),
                    'fg3_pct': game.get('FG3_PCT', 0) * 100 if game.get('FG3_PCT') else 0,
                    'game_date': game.get('GAME_DATE', ''),
                }
                for game in away_recent_games_full
            ],
        }

        return jsonify(response)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/team-stats-with-ranks')
def team_stats_with_ranks():
    """
    Get team statistics with league rankings

    Query params:
        - team_id: NBA team ID (required)
        - season: Season string, defaults to '2025-26'

    Returns:
        {
            'success': True,
            'team_id': 1610612747,
            'team_abbreviation': 'LAL',
            'season': '2025-26',
            'stats': {
                'ppg': {'value': 111.7, 'rank': 18},
                'opp_ppg': {'value': 116.3, 'rank': 25},
                'fg_pct': {'value': 47.3, 'rank': 12},
                'three_pct': {'value': 35.9, 'rank': 9},
                'ft_pct': {'value': 83.3, 'rank': 4},
                'off_rtg': {'value': 113.9, 'rank': 15},
                'def_rtg': {'value': 118.5, 'rank': 27},
                'net_rtg': {'value': -4.6, 'rank': 24},
                'pace': {'value': 96.7, 'rank': 20}
            }
        }
    """
    try:
        team_id = request.args.get('team_id')
        season = request.args.get('season', '2025-26')

        if not team_id:
            return jsonify({
                'success': False,
                'error': 'Missing team_id parameter'
            }), 400

        print(f'[team_stats_with_ranks] Fetching stats with ranks for team {team_id}, season {season}')

        # Get team stats with rankings
        team_data = team_rankings.get_team_stats_with_ranks(int(team_id), season)

        if not team_data:
            return jsonify({
                'success': False,
                'error': f'Stats not found for team {team_id}'
            }), 404

        return jsonify({
            'success': True,
            **team_data
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/team-stats-comparison')
def team_stats_comparison():
    """
    Get team statistics with both season totals and last-N comparison

    Query params:
        - team_id: NBA team ID (required)
        - season: Season string, defaults to '2025-26'
        - n: Number of recent games to compare (default 5)

    Returns:
        {
            'success': True,
            'team_id': 1610612747,
            'team_abbreviation': 'LAL',
            'season': '2025-26',
            'season_stats': {
                'ppg': {'value': 111.7, 'rank': 18},
                'opp_ppg': {'value': 116.3, 'rank': 25},
                ...
            },
            'last_n_stats': {
                'games_count': 5,
                'data_quality': 'excellent',
                'stats': {
                    'ppg': {'value': 114.9, 'delta': 3.2},
                    'opp_ppg': {'value': 114.6, 'delta': -1.7},
                    ...
                }
            }
        }
    """
    try:
        team_id = request.args.get('team_id')
        season = request.args.get('season', '2025-26')
        n = int(request.args.get('n', 5))

        if not team_id:
            return jsonify({
                'success': False,
                'error': 'Missing team_id parameter'
            }), 400

        team_id = int(team_id)

        print(f'[team_stats_comparison] Fetching comparison for team {team_id}, last {n} games')

        # Get season stats with rankings
        season_data = team_rankings.get_team_stats_with_ranks(team_id, season)

        if not season_data:
            return jsonify({
                'success': False,
                'error': f'Season stats not found for team {team_id}'
            }), 404

        # Get last-N stats comparison
        last_n_data = db_queries.get_team_last_n_stats_comparison(team_id, n, season)

        if not last_n_data:
            # Team exists but has no game logs yet (e.g., season start)
            last_n_data = {
                'last_n_games_count': 0,
                'data_quality': 'none',
                'stats': {}
            }

        # Build response
        response = {
            'success': True,
            'team_id': team_id,
            'team_abbreviation': season_data['team_abbreviation'],
            'season': season,
            'season_stats': season_data['stats'],
            'last_n_stats': {
                'games_count': last_n_data['last_n_games_count'],
                'data_quality': last_n_data['data_quality'],
                'stats': {
                    stat_key: {
                        'value': stat_data['last_n_value'],
                        'delta': stat_data['delta']
                    }
                    for stat_key, stat_data in last_n_data.get('stats', {}).items()
                }
            }
        }

        return jsonify(response)

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid parameter: {str(e)}'
        }), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/team-scoring-splits', methods=['GET'])
def team_scoring_splits():
    """
    Get defense-adjusted home/away scoring splits for a team.

    Query params:
        - team_id: NBA team ID (required)
        - season: Season string, defaults to '2025-26'

    Returns:
        {
            'success': True,
            'data': {
                'team_id': 1610612738,
                'team_abbreviation': 'BOS',
                'full_name': 'Boston Celtics',
                'season': '2025-26',
                'season_avg_ppg': 117.5,
                'splits': {
                    'elite': {
                        'home_ppg': 115.2,
                        'home_games': 8,
                        'away_ppg': 112.3,
                        'away_games': 7
                    },
                    'average': { ... },
                    'bad': { ... }
                },
                'identity_tags': [
                    'Home Flat-Track Bullies',
                    'Road Shrinkers vs Good Defense'
                ]
            }
        }
    """
    try:
        team_id = request.args.get('team_id', type=int)
        season = request.args.get('season', '2025-26')

        if not team_id:
            return jsonify({
                'success': False,
                'error': 'team_id parameter is required'
            }), 400

        print(f'[team_scoring_splits] Fetching scoring splits for team {team_id}, season {season}')

        from api.utils.scoring_splits import get_team_scoring_splits
        from api.utils.identity_tags import generate_identity_tags

        # Get splits data
        splits_data = get_team_scoring_splits(team_id, season)

        if splits_data is None:
            return jsonify({
                'success': False,
                'error': f'Team {team_id} not found or no data available'
            }), 404

        # Generate identity tags
        tags = generate_identity_tags(splits_data)
        splits_data['identity_tags'] = tags

        print(f'[team_scoring_splits] Generated {len(tags)} tags for {splits_data.get("team_abbreviation")}')

        return jsonify({
            'success': True,
            'data': splits_data
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/game-scoring-splits', methods=['GET'])
def game_scoring_splits():
    """
    Get defense-adjusted scoring splits for both teams in a game.

    Query params:
        - game_id: NBA game ID (required)
        - season: Season string, defaults to '2025-26'

    Returns:
        {
            'success': True,
            'data': {
                'game_id': '0022500234',
                'game_date': '2025-11-30',
                'home_team': {
                    'team_id': 1610612738,
                    'team_abbreviation': 'BOS',
                    'full_name': 'Boston Celtics',
                    'season_avg_ppg': 117.5,
                    'splits': { ... },
                    'identity_tags': [...]
                },
                'away_team': {
                    'team_id': 1610612747,
                    'team_abbreviation': 'LAL',
                    'full_name': 'Los Angeles Lakers',
                    'season_avg_ppg': 114.2,
                    'splits': { ... },
                    'identity_tags': [...]
                }
            }
        }
    """
    try:
        game_id = request.args.get('game_id')
        season = request.args.get('season', '2025-26')

        if not game_id:
            return jsonify({
                'success': False,
                'error': 'game_id parameter is required'
            }), 400

        print(f'[game_scoring_splits] Fetching scoring splits for game {game_id}')

        from api.utils.scoring_splits import get_team_scoring_splits
        from api.utils.pace_splits import get_team_pace_splits
        from api.utils.pace_projection import calculate_projected_pace
        from api.utils.identity_tags import generate_identity_tags
        from api.utils.db_queries import get_team_stats_with_ranks

        # Find the game to get team IDs
        games = get_todays_games(season)
        game = next((g for g in games if g['game_id'] == game_id), None)

        if not game:
            return jsonify({
                'success': False,
                'error': f'Game {game_id} not found'
            }), 404

        print(f'[game_scoring_splits] Found game: {game.get("away_team_name")} @ {game.get("home_team_name")}')

        # Get defense splits for both teams
        home_splits = get_team_scoring_splits(game['home_team_id'], season)
        away_splits = get_team_scoring_splits(game['away_team_id'], season)

        if not home_splits or not away_splits:
            return jsonify({
                'success': False,
                'error': 'Team data not found for one or both teams'
            }), 404

        # Get pace splits for both teams
        home_pace_splits = get_team_pace_splits(game['home_team_id'], season)
        away_pace_splits = get_team_pace_splits(game['away_team_id'], season)

        # Add pace splits to the main data structures
        if home_pace_splits:
            home_splits['pace_splits'] = home_pace_splits['pace_splits']
        if away_pace_splits:
            away_splits['pace_splits'] = away_pace_splits['pace_splits']

        # Calculate projected game pace (factors in last 5 games + season average)
        projected_pace = calculate_projected_pace(game['home_team_id'], game['away_team_id'], season)
        home_splits['projected_pace'] = projected_pace
        away_splits['projected_pace'] = projected_pace

        print(f'[game_scoring_splits] Projected pace: {projected_pace:.1f}')

        # Get defensive ranks for both teams
        home_stats = get_team_stats_with_ranks(game['home_team_id'], season)
        away_stats = get_team_stats_with_ranks(game['away_team_id'], season)

        # Add opponent's defensive rank to each team's data
        if home_stats:
            home_splits['opponent_def_rank'] = away_stats['stats'].get('def_rtg', {}).get('rank') if away_stats else None

        if away_stats:
            away_splits['opponent_def_rank'] = home_stats['stats'].get('def_rtg', {}).get('rank') if home_stats else None

        # Generate identity tags for both teams
        home_splits['identity_tags'] = generate_identity_tags(home_splits)
        away_splits['identity_tags'] = generate_identity_tags(away_splits)

        print(f'[game_scoring_splits] Home: {len(home_splits["identity_tags"])} tags, Away: {len(away_splits["identity_tags"])} tags')
        print(f'[game_scoring_splits] Home opponent def rank: {home_splits.get("opponent_def_rank")}, Away opponent def rank: {away_splits.get("opponent_def_rank")}')

        return jsonify({
            'success': True,
            'data': {
                'game_id': game_id,
                'game_date': game.get('game_date'),
                'home_team': home_splits,
                'away_team': away_splits
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/game-three-pt-scoring-splits', methods=['GET'])
def game_three_pt_scoring_splits():
    """
    Get 3PT defense-adjusted scoring splits for both teams in a game.

    Query params:
        - game_id: NBA game ID (required)
        - season: Season string, defaults to '2025-26'

    Returns:
        {
            'success': True,
            'data': {
                'game_id': '0022500234',
                'game_date': '2025-11-30',
                'home_team': {
                    'team_id': 1610612738,
                    'team_abbreviation': 'BOS',
                    'full_name': 'Boston Celtics',
                    'season_avg_three_pt_ppg': 42.5,
                    'splits': {
                        'elite': {
                            'home_three_pt_ppg': 40.2,
                            'home_games': 8,
                            'away_three_pt_ppg': 38.3,
                            'away_games': 7
                        },
                        'average': { ... },
                        'bad': { ... }
                    }
                },
                'away_team': { ... }
            }
        }
    """
    try:
        game_id = request.args.get('game_id')
        season = request.args.get('season', '2025-26')

        if not game_id:
            return jsonify({
                'success': False,
                'error': 'game_id parameter is required'
            }), 400

        print(f'[game_three_pt_scoring_splits] Fetching 3PT scoring splits for game {game_id}')

        from api.utils.three_pt_scoring_splits import get_team_three_pt_scoring_splits
        from api.utils.db_queries import get_team_stats_with_ranks

        # Find the game to get team IDs
        games = get_todays_games(season)
        game = next((g for g in games if g['game_id'] == game_id), None)

        if not game:
            return jsonify({
                'success': False,
                'error': f'Game {game_id} not found'
            }), 404

        print(f'[game_three_pt_scoring_splits] Found game: {game.get("away_team_name")} @ {game.get("home_team_name")}')

        # Get 3PT defense splits for both teams
        home_splits = get_team_three_pt_scoring_splits(game['home_team_id'], season)
        away_splits = get_team_three_pt_scoring_splits(game['away_team_id'], season)

        if not home_splits or not away_splits:
            return jsonify({
                'success': False,
                'error': 'Team data not found for one or both teams'
            }), 404

        # Get 3PT defensive ranks for both teams
        home_stats = get_team_stats_with_ranks(game['home_team_id'], season)
        away_stats = get_team_stats_with_ranks(game['away_team_id'], season)

        # Add opponent's 3PT defensive rank to each team's data
        if home_stats:
            home_splits['opponent_3pt_def_rank'] = away_stats['stats'].get('opp_fg3_pct_rank', {}).get('rank') if away_stats else None

        if away_stats:
            away_splits['opponent_3pt_def_rank'] = home_stats['stats'].get('opp_fg3_pct_rank', {}).get('rank') if home_stats else None

        print(f'[game_three_pt_scoring_splits] Home opponent 3PT def rank: {home_splits.get("opponent_3pt_def_rank")}, Away opponent 3PT def rank: {away_splits.get("opponent_3pt_def_rank")}')

        return jsonify({
            'success': True,
            'data': {
                'game_id': game_id,
                'game_date': game.get('game_date'),
                'home_team': home_splits,
                'away_team': away_splits
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/game-three-pt-scoring-vs-pace', methods=['GET'])
def game_three_pt_scoring_vs_pace():
    """
    Get pace-adjusted 3PT scoring splits for both teams in a game.

    Query params:
        - game_id: NBA game ID (required)
        - season: Season string, defaults to '2025-26'

    Returns:
        {
            'success': True,
            'data': {
                'game_id': '0022500234',
                'game_date': '2025-11-30',
                'projected_pace': 101.5,
                'home_team': {
                    'team_id': 1610612738,
                    'team_abbreviation': 'BOS',
                    'full_name': 'Boston Celtics',
                    'season_avg_three_pt_ppg': 42.5,
                    'projected_pace': 101.5,
                    'splits': {
                        'slow': {
                            'home_three_pt_ppg': 39.2,
                            'home_games': 5,
                            'away_three_pt_ppg': 38.3,
                            'away_games': 6
                        },
                        'normal': { ... },
                        'fast': { ... }
                    }
                },
                'away_team': { ... }
            }
        }
    """
    try:
        game_id = request.args.get('game_id')
        season = request.args.get('season', '2025-26')

        if not game_id:
            return jsonify({
                'success': False,
                'error': 'game_id parameter is required'
            }), 400

        print(f'[game_three_pt_scoring_vs_pace] Fetching 3PT scoring vs pace for game {game_id}')

        from api.utils.three_pt_scoring_vs_pace import get_team_three_pt_scoring_vs_pace
        from api.utils.pace_projection import calculate_projected_pace

        # Find the game to get team IDs
        games = get_todays_games(season)
        game = next((g for g in games if g['game_id'] == game_id), None)

        if not game:
            return jsonify({
                'success': False,
                'error': f'Game {game_id} not found'
            }), 404

        print(f'[game_three_pt_scoring_vs_pace] Found game: {game.get("away_team_name")} @ {game.get("home_team_name")}')

        # Get 3PT pace splits for both teams
        home_splits = get_team_three_pt_scoring_vs_pace(game['home_team_id'], season)
        away_splits = get_team_three_pt_scoring_vs_pace(game['away_team_id'], season)

        if not home_splits or not away_splits:
            return jsonify({
                'success': False,
                'error': 'Team data not found for one or both teams'
            }), 404

        # Calculate projected pace for the game
        try:
            projected_pace = calculate_projected_pace(game['home_team_id'], game['away_team_id'], season)
            print(f'[game_three_pt_scoring_vs_pace] Projected pace: {projected_pace:.1f}')
        except Exception as e:
            print(f'[game_three_pt_scoring_vs_pace] Error calculating projected pace: {e}')
            projected_pace = None

        # Add projected pace to each team's data
        home_splits['projected_pace'] = projected_pace
        away_splits['projected_pace'] = projected_pace

        return jsonify({
            'success': True,
            'data': {
                'game_id': game_id,
                'game_date': game.get('game_date'),
                'projected_pace': projected_pace,
                'home_team': home_splits,
                'away_team': away_splits
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/game-turnover-vs-defense-pressure', methods=['GET'])
def game_turnover_vs_defense_pressure():
    """
    Get turnover splits by opponent defensive pressure tier for both teams in a game.

    Query params:
        - game_id: NBA game ID (required)
        - season: Season string, defaults to '2025-26'

    Returns:
        {
            'success': True,
            'data': {
                'game_id': '0022500234',
                'game_date': '2025-11-30',
                'home_team': {
                    'team_id': 1610612738,
                    'team_abbreviation': 'BOS',
                    'full_name': 'Boston Celtics',
                    'season_avg_turnovers': 12.5,
                    'opponent_turnover_pressure_tier': 'elite',
                    'splits': {
                        'elite': {
                            'home_turnovers': 13.2,
                            'home_games': 8,
                            'away_turnovers': 14.1,
                            'away_games': 7
                        },
                        'average': { ... },
                        'low': { ... }
                    }
                },
                'away_team': { ... }
            }
        }
    """
    try:
        game_id = request.args.get('game_id')
        season = request.args.get('season', '2025-26')

        if not game_id:
            return jsonify({
                'success': False,
                'error': 'game_id parameter is required'
            }), 400

        print(f'[game_turnover_vs_defense_pressure] Fetching turnover vs defense pressure for game {game_id}')

        from api.utils.turnover_vs_defense_pressure import get_team_turnover_vs_defense_pressure
        from api.utils.turnover_pressure_tiers import get_turnover_pressure_tier

        # Find the game to get team IDs
        games = get_todays_games(season)
        game = next((g for g in games if g['game_id'] == game_id), None)

        if not game:
            return jsonify({
                'success': False,
                'error': f'Game {game_id} not found'
            }), 404

        print(f'[game_turnover_vs_defense_pressure] Found game: {game.get("away_team_name")} @ {game.get("home_team_name")}')

        # Get turnover pressure splits for both teams
        home_splits = get_team_turnover_vs_defense_pressure(game['home_team_id'], season)
        away_splits = get_team_turnover_vs_defense_pressure(game['away_team_id'], season)

        if not home_splits or not away_splits:
            return jsonify({
                'success': False,
                'error': 'Team data not found for one or both teams'
            }), 404

        # Get opponent turnover pressure tier for each team
        # Home team faces away team's defensive pressure
        away_team_stats = get_team_stats_with_ranks(game['away_team_id'], season)
        away_opp_tov_rank = away_team_stats['stats']['opp_tov']['rank'] if away_team_stats and 'opp_tov' in away_team_stats['stats'] else None
        away_def_rtg_rank = away_team_stats['stats']['def_rtg']['rank'] if away_team_stats and 'def_rtg' in away_team_stats['stats'] else None
        home_opponent_tier = get_turnover_pressure_tier(away_opp_tov_rank)

        # Away team faces home team's defensive pressure
        home_team_stats = get_team_stats_with_ranks(game['home_team_id'], season)
        home_opp_tov_rank = home_team_stats['stats']['opp_tov']['rank'] if home_team_stats and 'opp_tov' in home_team_stats['stats'] else None
        home_def_rtg_rank = home_team_stats['stats']['def_rtg']['rank'] if home_team_stats and 'def_rtg' in home_team_stats['stats'] else None
        away_opponent_tier = get_turnover_pressure_tier(home_opp_tov_rank)

        # Add opponent tier and stats to each team's data
        home_splits['opponent_turnover_pressure_tier'] = home_opponent_tier
        home_splits['opponent_opp_tov_rank'] = away_opp_tov_rank
        home_splits['opponent_def_rtg_rank'] = away_def_rtg_rank

        away_splits['opponent_turnover_pressure_tier'] = away_opponent_tier
        away_splits['opponent_opp_tov_rank'] = home_opp_tov_rank
        away_splits['opponent_def_rtg_rank'] = home_def_rtg_rank

        print(f'[game_turnover_vs_defense_pressure] Home faces {home_opponent_tier} pressure, Away faces {away_opponent_tier} pressure')

        return jsonify({
            'success': True,
            'data': {
                'game_id': game_id,
                'game_date': game.get('game_date'),
                'home_team': home_splits,
                'away_team': away_splits
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/game-turnover-vs-pace', methods=['GET'])
def game_turnover_vs_pace():
    """
    Get turnover splits by game pace tier for both teams in a game.

    Query params:
        - game_id: NBA game ID (required)
        - season: Season string, defaults to '2025-26'

    Returns:
        {
            'success': True,
            'data': {
                'game_id': '0022500234',
                'game_date': '2025-11-30',
                'projected_pace': 101.5,
                'home_team': {
                    'team_id': 1610612738,
                    'team_abbreviation': 'BOS',
                    'full_name': 'Boston Celtics',
                    'season_avg_turnovers': 12.5,
                    'projected_pace': 101.5,
                    'splits': {
                        'slow': {
                            'home_turnovers': 11.8,
                            'home_games': 6,
                            'away_turnovers': 12.3,
                            'away_games': 5
                        },
                        'normal': { ... },
                        'fast': { ... }
                    }
                },
                'away_team': { ... }
            }
        }
    """
    try:
        game_id = request.args.get('game_id')
        season = request.args.get('season', '2025-26')

        if not game_id:
            return jsonify({
                'success': False,
                'error': 'game_id parameter is required'
            }), 400

        print(f'[game_turnover_vs_pace] Fetching turnover vs pace for game {game_id}')

        from api.utils.turnover_vs_pace import get_team_turnover_vs_pace
        from api.utils.pace_projection import calculate_projected_pace

        # Find the game to get team IDs
        games = get_todays_games(season)
        game = next((g for g in games if g['game_id'] == game_id), None)

        if not game:
            return jsonify({
                'success': False,
                'error': f'Game {game_id} not found'
            }), 404

        print(f'[game_turnover_vs_pace] Found game: {game.get("away_team_name")} @ {game.get("home_team_name")}')

        # Get turnover pace splits for both teams
        home_splits = get_team_turnover_vs_pace(game['home_team_id'], season)
        away_splits = get_team_turnover_vs_pace(game['away_team_id'], season)

        if not home_splits or not away_splits:
            return jsonify({
                'success': False,
                'error': 'Team data not found for one or both teams'
            }), 404

        # Calculate projected pace for the game
        try:
            projected_pace = calculate_projected_pace(game['home_team_id'], game['away_team_id'], season)
            print(f'[game_turnover_vs_pace] Projected pace: {projected_pace:.1f}')
        except Exception as e:
            print(f'[game_turnover_vs_pace] Error calculating projected pace: {e}')
            projected_pace = None

        # Add projected pace to each team's data
        home_splits['projected_pace'] = projected_pace
        away_splits['projected_pace'] = projected_pace

        return jsonify({
            'success': True,
            'data': {
                'game_id': game_id,
                'game_date': game.get('game_date'),
                'projected_pace': projected_pace,
                'home_team': home_splits,
                'away_team': away_splits
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/predict', methods=['POST'])
def predict():
    """Make a prediction for a game"""
    try:
        data = request.get_json()
        home_team_id = data.get('home_team_id')
        away_team_id = data.get('away_team_id')
        betting_line = data.get('betting_line')

        if not home_team_id or not away_team_id:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400

        prediction = get_cached_prediction(int(home_team_id), int(away_team_id), betting_line)

        if prediction is None:
            return jsonify({
                'success': False,
                'error': 'Failed to generate prediction'
            }), 500

        return jsonify({
            'success': True,
            'prediction': prediction
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback"""
    try:
        data = request.get_json()
        print(f'[feedback] Received: {data}')

        return jsonify({
            'success': True,
            'message': 'Feedback received'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== TEAM SIMILARITY ENDPOINTS ==========

@app.route('/api/teams/<int:team_id>/similarity', methods=['GET'])
def get_team_similarity(team_id):
    """
    Get top N most similar teams for a given team

    Query params:
        - season: NBA season (default: '2025-26')
        - limit: Number of similar teams to return (default: 5)

    Returns:
        {
            'success': True,
            'team_id': 1610612753,
            'season': '2025-26',
            'similar_teams': [
                {'team_id': ..., 'team_name': ..., 'similarity_score': 85.1, 'rank': 1},
                ...
            ]
        }
    """
    try:
        from api.utils.team_similarity import get_team_similarity_ranking

        season = request.args.get('season', '2025-26')
        limit = int(request.args.get('limit', 5))

        similar_teams = get_team_similarity_ranking(team_id, season, limit)

        return jsonify({
            'success': True,
            'team_id': team_id,
            'season': season,
            'similar_teams': similar_teams
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/teams/<int:team_id>/cluster', methods=['GET'])
def get_team_cluster(team_id):
    """
    Get cluster assignment for a given team

    Query params:
        - season: NBA season (default: '2025-26')

    Returns:
        {
            'success': True,
            'team_id': 1610612753,
            'cluster': {
                'cluster_id': 1,
                'cluster_name': 'Elite Pace Pushers',
                'cluster_description': '...',
                'distance_to_centroid': 0.123
            }
        }
    """
    try:
        from api.utils.db_schema_similarity import get_connection

        season = request.args.get('season', '2025-26')

        conn = get_connection()
        cursor = conn.cursor()

        # Get team's cluster assignment
        cursor.execute("""
            SELECT tca.cluster_id, tca.distance_to_centroid,
                   tsc.cluster_name, tsc.cluster_description
            FROM team_cluster_assignments tca
            JOIN team_similarity_clusters tsc
                ON tca.cluster_id = tsc.cluster_id AND tca.season = tsc.season
            WHERE tca.team_id = ? AND tca.season = ?
        """, (team_id, season))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({
                'success': False,
                'error': 'No cluster assignment found for team'
            }), 404

        return jsonify({
            'success': True,
            'team_id': team_id,
            'season': season,
            'cluster': {
                'cluster_id': row[0],
                'distance_to_centroid': row[1],
                'cluster_name': row[2],
                'cluster_description': row[3]
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/clusters', methods=['GET'])
def get_all_clusters():
    """
    Get all cluster definitions

    Query params:
        - season: NBA season (default: '2025-26')

    Returns:
        {
            'success': True,
            'season': '2025-26',
            'clusters': [
                {
                    'cluster_id': 1,
                    'cluster_name': 'Elite Pace Pushers',
                    'cluster_description': '...',
                    'team_count': 3
                },
                ...
            ]
        }
    """
    try:
        from api.utils.db_schema_similarity import get_connection

        season = request.args.get('season', '2025-26')

        conn = get_connection()
        cursor = conn.cursor()

        # Get all clusters with team counts
        cursor.execute("""
            SELECT tsc.cluster_id, tsc.cluster_name, tsc.cluster_description,
                   COUNT(tca.team_id) as team_count
            FROM team_similarity_clusters tsc
            LEFT JOIN team_cluster_assignments tca
                ON tsc.cluster_id = tca.cluster_id AND tsc.season = tca.season
            WHERE tsc.season = ?
            GROUP BY tsc.cluster_id, tsc.cluster_name, tsc.cluster_description
            ORDER BY tsc.cluster_id
        """, (season,))

        rows = cursor.fetchall()
        conn.close()

        clusters = []
        for row in rows:
            clusters.append({
                'cluster_id': row[0],
                'cluster_name': row[1],
                'cluster_description': row[2],
                'team_count': row[3]
            })

        return jsonify({
            'success': True,
            'season': season,
            'clusters': clusters
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/refresh-similarity', methods=['POST'])
def refresh_similarity():
    """
    Refresh all similarity data (admin endpoint)

    Request body:
        {
            'season': '2025-26'  # optional
        }

    Returns:
        {
            'success': True,
            'teams_processed': 30,
            'clusters_assigned': 30,
            'time_seconds': 0.05
        }
    """
    try:
        from api.utils.team_similarity import refresh_similarity_engine

        data = request.get_json() or {}
        season = data.get('season', '2025-26')

        print(f"[Similarity API] Refreshing similarity data for {season}...")

        result = refresh_similarity_engine(season)

        print(f"[Similarity API] Refresh complete: {result}")

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== SELF-LEARNING PREDICTION ENDPOINTS ==========

@app.route('/api/save-prediction', methods=['POST'])
def save_prediction():
    """
    Save a pre-game prediction for later comparison with sportsbook line and actual results

    Request body:
    {
        "game_id": "0022500123",
        "home_team": "BOS",
        "away_team": "LAL"
    }
    """
    from api.utils.performance import log_slow_operation

    try:
        data = request.get_json()

        # Validate required fields
        game_id = data.get('game_id')
        home_team = data.get('home_team')
        away_team = data.get('away_team')

        if not all([game_id, home_team, away_team]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: game_id, home_team, away_team'
            }), 400

        print(f'[save-prediction] Generating prediction for {away_team} @ {home_team} (game {game_id})')

        # Get team IDs for the complex prediction engine
        all_teams = get_all_teams()
        home_team_data = next((t for t in all_teams if t['abbreviation'] == home_team), None)
        away_team_data = next((t for t in all_teams if t['abbreviation'] == away_team), None)

        if not home_team_data or not away_team_data:
            return jsonify({
                'success': False,
                'error': f'Team not found: {home_team if not home_team_data else away_team}'
            }), 400

        home_team_id = home_team_data['id']
        away_team_id = away_team_data['id']

        # Use the COMPLEX prediction engine (same as dashboard)
        try:
            with log_slow_operation("Fetch matchup data from NBA API", threshold_ms=3000):
                matchup_data = get_matchup_data(home_team_id, away_team_id)
                if matchup_data is None:
                    error_details = """
NBA API Failed to Return Data

Possible causes:
1. NBA API is currently slow or down (check stats.nba.com)
2. Rate limiting after multiple requests
3. Network connectivity issues
4. Invalid team IDs

What to try:
• Wait 30-60 seconds and try again
• Check if the NBA API is operational at https://stats.nba.com
• Try a different game
• Check Railway logs for detailed error messages
                    """
                    print(f'[save-prediction] NBA API failure for teams {home_team} vs {away_team}')
                    return jsonify({
                        'success': False,
                        'error': 'NBA API is currently unavailable',
                        'details': error_details.strip(),
                        'retry': True
                    }), 503  # Service Unavailable

            with log_slow_operation("Generate base prediction", threshold_ms=500):
                # Get BASE prediction using the complex engine
                prediction = predict_game_total(
                    matchup_data['home'],
                    matchup_data['away'],
                    betting_line=None  # No line yet
                )

                base_home = prediction['breakdown']['home_projected']
                base_away = prediction['breakdown']['away_projected']
                base_total = prediction['predicted_total']

                print(f'[save-prediction] Base prediction: {base_total} ({base_home} - {base_away})')

        except KeyError as e:
            print(f'[save-prediction] Data structure error: {str(e)}')
            return jsonify({
                'success': False,
                'error': f'Incomplete data from NBA API (missing {str(e)})',
                'retry': True
            }), 500
        except Exception as e:
            print(f'[save-prediction] Unexpected error: {str(e)}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Prediction failed: {str(e)}',
                'retry': False
            }), 500

        # Extract game date from game_id or use current date
        game_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        # Build feature vector for analytics (no learning applied)
        feature_correction = 0.0  # Always 0 in deterministic mode
        feature_vector_dict = None
        feature_metadata = None

        try:
            from api.utils.feature_builder import build_feature_vector
            import json

            with log_slow_operation("Build feature vector (rankings + recent games)", threshold_ms=2000):
                print(f'[save-prediction] Building feature vector for analytics...')
                feature_data = build_feature_vector(
                    home_team=home_team,
                    away_team=away_team,
                    game_id=game_id,
                    as_of_date=game_date,
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    n_recent_games=model_params.get('parameters', {}).get('recent_games_n', 10),
                    season='2025-26'
                )

            # Store feature data for analytics only (no weights applied)
            feature_vector_dict = json.dumps(feature_data['features'])
            feature_metadata = json.dumps(feature_data['metadata'])
            print(f'[save-prediction] Feature vector saved for analytics (no correction applied)')

        except Exception as e:
            print(f'[save-prediction] Warning: Could not compute features: {e}')
            print('[save-prediction] Continuing with base prediction')
            # Continue with base prediction

        # Use base total directly (no learned feature correction)
        intermediate_total = base_total

        # Apply deterministic opponent-profile adjustment (NEW LAYER)
        try:
            from api.utils.opponent_profile_adjustment import compute_opponent_profile_adjustment

            print('[save-prediction] Computing opponent-profile adjustment...')
            opp_adjustment_result = compute_opponent_profile_adjustment(
                home_tricode=home_team,
                away_tricode=away_team,
                as_of_date=game_date,
                base_total=base_total,
                base_home=base_home,
                base_away=base_away
            )

            opponent_adjustment = opp_adjustment_result['adjustment']
            print(f'[save-prediction] Opponent-profile adjustment: {opponent_adjustment:+.2f}')

            # Final prediction = base + learned_features + deterministic_opponent_adjustment
            pred_total = intermediate_total + opponent_adjustment
            pred_home = opp_adjustment_result['adjusted_home']
            pred_away = opp_adjustment_result['adjusted_away']

        except Exception as e:
            print(f'[save-prediction] Warning: Could not compute opponent adjustment: {e}')
            print('[save-prediction] Falling back to intermediate prediction (base + features)')
            # Fallback: use intermediate total without opponent adjustment
            opponent_adjustment = 0.0
            opp_adjustment_result = None
            pred_total = intermediate_total

            # Split intermediate total into team scores
            base_ratio = base_home / (base_home + base_away) if (base_home + base_away) > 0 else 0.5
            pred_home = pred_total * base_ratio
            pred_away = pred_total * (1 - base_ratio)

        print(f'[save-prediction] Final prediction: {pred_total:.1f} ({pred_home:.1f} - {pred_away:.1f})')
        print(f'[save-prediction] Breakdown: base={base_total:.1f}, feature_corr={feature_correction:+.1f}, opp_adj={opponent_adjustment:+.1f}')

        # Save to database with feature data
        result = db.save_prediction(
            game_id=game_id,
            home_team=home_team,
            away_team=away_team,
            game_date=game_date,
            pred_home=pred_home,
            pred_away=pred_away,
            pred_total=pred_total,
            model_version='3.0',
            base_prediction=base_total,
            feature_correction=feature_correction,
            feature_vector=feature_vector_dict,
            feature_metadata=feature_metadata
        )

        if not result['success']:
            return jsonify(result), 400

        print(f'[save-prediction] ✓ Saved prediction: {pred_total} total')

        # Build detailed response with all prediction layers
        result['prediction'] = {
            'base': {
                'total': base_total,
                'home': base_home,
                'away': base_away
            },
            'with_learned_features': {
                'total': base_total + feature_correction,
                'correction': feature_correction
            },
            'with_opponent_profile': {
                'total': pred_total,
                'home': pred_home,
                'away': pred_away,
                'adjustment': opponent_adjustment,
                'explanation': opp_adjustment_result['explanation'] if opp_adjustment_result else 'No adjustment applied'
            },
            'layers_breakdown': {
                'base': base_total,
                'feature_correction': feature_correction,
                'opponent_adjustment': opponent_adjustment,
                'final': pred_total
            },
            'recommendation': prediction.get('recommendation', '')
        }

        # Add opponent details if available
        if opp_adjustment_result:
            result['prediction']['opponent_details'] = opp_adjustment_result['details']

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/submit-line', methods=['POST'])
def submit_line():
    """
    Submit the sportsbook closing total line for a game

    Request body:
    {
        "game_id": "0022500123",
        "sportsbook_total_line": 218.5
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        game_id = data.get('game_id')
        sportsbook_total_line = data.get('sportsbook_total_line')

        if not game_id or sportsbook_total_line is None:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: game_id, sportsbook_total_line'
            }), 400

        # Validate line is a number
        try:
            sportsbook_total_line = float(sportsbook_total_line)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'sportsbook_total_line must be a number'
            }), 400

        print(f'[submit-line] Submitting line {sportsbook_total_line} for game {game_id}')

        # Save to database
        result = db.submit_line(game_id, sportsbook_total_line)

        if not result['success']:
            return jsonify(result), 404

        print(f'[submit-line] ✓ Line submitted successfully')

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Learning endpoint removed - system is now deterministic


@app.route('/api/prediction-history', methods=['GET'])
def prediction_history():
    """
    Get prediction history with optional filters

    Query params:
        - limit: Number of records (default 50)
        - with_learning: Only show predictions with completed learning (default false)
    """
    try:
        limit = int(request.args.get('limit', 50))
        with_learning = request.args.get('with_learning', 'false').lower() == 'true'

        if with_learning:
            predictions = db.get_predictions_with_learning(limit=limit)
        else:
            predictions = db.get_all_predictions(limit=limit)

        # Calculate performance stats
        stats = db.get_model_performance_stats(days=30)

        return jsonify({
            'success': True,
            'predictions': predictions,
            'stats': stats,
            'count': len(predictions)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Automated learning endpoints removed - system is now deterministic


# ============================================================================
# GAME REVIEW ENDPOINTS (OpenAI Vision-powered post-game analysis)
# ============================================================================

@app.route('/api/games/<game_id>/result-screenshot', methods=['POST'])
def upload_result_screenshot(game_id):
    """
    Upload a screenshot of the final box score and generate AI review.

    Workflow:
    1. Receive screenshot file upload
    2. Extract scores using OpenAI Vision API
    3. Calculate prediction errors
    4. Generate AI coaching review
    5. Store in game_reviews database

    Returns:
        {
            success: true,
            review: {
                game_id, actual_scores, predicted_scores, errors,
                ai_review (what_happened, why_we_missed, key_factors, model_advice)
            }
        }
    """
    try:
        from werkzeug.utils import secure_filename
        from api.utils.openai_client import extract_scores_from_screenshot, generate_game_review
        from api.utils.db_schema_game_reviews import get_connection as get_reviews_db
        from api.utils.style_stats_builder import build_expected_style_stats, build_actual_style_stats
        import tempfile

        # Validate file upload
        if 'screenshot' not in request.files:
            return jsonify({'success': False, 'error': 'No screenshot file provided'}), 400

        file = request.files['screenshot']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename'}), 400

        # Get basic game data from request
        form_data = request.form
        home_team = form_data.get('home_team')
        away_team = form_data.get('away_team')
        game_date = form_data.get('game_date')

        # Get betting line from form (CRITICAL: this determines which prediction to use)
        sportsbook_line_str = form_data.get('sportsbook_line')
        sportsbook_line = float(sportsbook_line_str) if sportsbook_line_str else None

        if not all([home_team, away_team, game_date]):
            return jsonify({'success': False, 'error': 'Missing required fields: home_team, away_team, game_date'}), 400

        # Get predicted values from form as FALLBACK (in case backend prediction fetch fails)
        # These are the values the UI showed, so they're the "truth" if we can't fetch fresh
        predicted_home_fallback = float(form_data.get('predicted_home')) if form_data.get('predicted_home') else None
        predicted_away_fallback = float(form_data.get('predicted_away')) if form_data.get('predicted_away') else None
        predicted_total_fallback = float(form_data.get('predicted_total')) if form_data.get('predicted_total') else None

        # These will be set from get_cached_prediction if available, otherwise use fallback
        predicted_home = predicted_home_fallback
        predicted_away = predicted_away_fallback
        predicted_total = predicted_total_fallback

        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1])
        temp_path = temp_file.name
        file.save(temp_path)
        temp_file.close()

        try:
            # Debug: Check if API key is available
            api_key_available = bool(os.environ.get('OPENAI_API_KEY'))
            print(f"[Review] OpenAI API Key available: {api_key_available}")

            # Extract scores using OpenAI Vision
            print(f"[Review] Extracting scores from screenshot for game {game_id}")
            vision_result = extract_scores_from_screenshot(
                temp_path,
                home_team,
                away_team,
                model="gpt-4.1-mini"  # Use mini for cost efficiency
            )

            actual_home = vision_result['home_score']
            actual_away = vision_result['away_score']
            actual_total = vision_result['total']
            vision_confidence = vision_result.get('confidence', 'medium')

            print(f"[Review] Scores extracted: {home_team} {actual_home}, {away_team} {actual_away} (confidence: {vision_confidence})")

            # We'll calculate errors AFTER we get the prediction (below)

            # Fetch comprehensive data for AI Model Coach v2
            from api.utils.db_queries import get_team_by_abbreviation, get_game_box_score

            home_box_score = None
            away_box_score = None
            predicted_pace = None
            prediction_breakdown = None
            matchup_data = None
            team_season_stats = None
            last_5_trends = None
            similarity_data = None
            # Note: sportsbook_line is already set from form_data above (line 1879)

            # Try to get team IDs and comprehensive data
            try:
                home_team_data = get_team_by_abbreviation(home_team)
                away_team_data = get_team_by_abbreviation(away_team)

                if home_team_data and away_team_data:
                    home_team_id = home_team_data['id']
                    away_team_id = away_team_data['id']

                    # Get box scores
                    home_box_score = get_game_box_score(game_id, home_team_id)
                    away_box_score = get_game_box_score(game_id, away_team_id)

                    if home_box_score:
                        print(f"[Review] Fetched home box score: pace={home_box_score.get('pace')}, 3PA={home_box_score.get('fg3a')}")
                    if away_box_score:
                        print(f"[Review] Fetched away box score: pace={away_box_score.get('pace')}, 3PA={away_box_score.get('fg3a')}")

                    # === CRITICAL: Get prediction using SAME source as UI ===
                    # Try to fetch fresh prediction, but use fallback if it fails
                    if not sportsbook_line:
                        print(f"[Review] WARNING: No sportsbook line provided, using fallback from form")
                        print(f"[Review] Using FALLBACK values from form: {predicted_total_fallback:.1f if predicted_total_fallback else 'N/A'}")
                    else:
                        print(f"[Review] Fetching prediction with line={sportsbook_line}")
                        prediction, matchup_data = get_cached_prediction(
                            home_team_id,
                            away_team_id,
                            sportsbook_line,  # Use the EXACT betting line from the UI
                            game_id=game_id
                        )

                        if prediction:
                            # OVERRIDE fallback values with fresh prediction from backend
                            prediction_breakdown = prediction
                            predicted_total = prediction.get('predicted_total')
                            predicted_home = prediction.get('breakdown', {}).get('home_projected')
                            predicted_away = prediction.get('breakdown', {}).get('away_projected')
                            predicted_pace = prediction.get('factors', {}).get('game_pace')

                            print(f"[Review] ✓ Got prediction from BACKEND (overriding fallback):")
                            print(f"  - Betting Line: {sportsbook_line}")
                            print(f"  - Predicted Total: {predicted_total:.1f if predicted_total else 'N/A'} ({predicted_home:.1f if predicted_home else 'N/A'} + {predicted_away:.1f if predicted_away else 'N/A'})")
                            print(f"  - Model Pick: {prediction.get('recommendation', 'N/A')}")
                            print(f"  - Predicted Pace: {predicted_pace}")
                            print(f"  - Has Matchup DNA: {bool(matchup_data)}")
                        else:
                            print(f"[Review] WARNING: get_cached_prediction returned None, using FALLBACK from form")
                            print(f"[Review] FALLBACK values: {predicted_total:.1f if predicted_total else 'N/A'} ({predicted_home:.1f if predicted_home else 'N/A'} + {predicted_away:.1f if predicted_away else 'N/A'})")

                    # Get team season stats
                    try:
                        home_stats = get_team_stats_with_ranks(home_team_id, '2025-26')
                        away_stats = get_team_stats_with_ranks(away_team_id, '2025-26')

                        team_season_stats = {
                            'home': home_stats,
                            'away': away_stats
                        }
                        print(f"[Review] Fetched team season stats")
                    except Exception as e:
                        print(f"[Review] Could not fetch team season stats: {e}")

                    # Get last-5 trends from prediction object
                    if prediction:
                        last_5_trends = {
                            'home': prediction.get('home_last5_trends'),
                            'away': prediction.get('away_last5_trends')
                        }
                        print(f"[Review] Got last-5 trends from prediction")

                    # Get similarity/cluster data from prediction object
                    if prediction and 'similarity' in prediction:
                        similarity_data = prediction.get('similarity')
                        if similarity_data and similarity_data.get('matchup_type'):
                            print(f"[Review] Got similarity data from prediction:")
                            print(f"  - Matchup Type: {similarity_data.get('matchup_type')}")
                            print(f"  - Home Cluster: {similarity_data.get('home_cluster', {}).get('name', 'N/A')}")
                            print(f"  - Away Cluster: {similarity_data.get('away_cluster', {}).get('name', 'N/A')}")
                            # Wrap in 'has_data' format expected by openai_client
                            similarity_data['has_data'] = True
                        else:
                            print(f"[Review] Similarity data present but incomplete")
                            similarity_data = None
                    else:
                        print(f"[Review] No similarity data in prediction")

            except Exception as e:
                print(f"[Review] Could not fetch comprehensive data: {e}")
                import traceback
                traceback.print_exc()
                # Continue with whatever data we have

            # Calculate errors (now that we have predicted values from get_cached_prediction)
            # Also verify actual values are not None (vision extraction might fail)
            if (predicted_home is not None and predicted_away is not None and predicted_total is not None and
                actual_home is not None and actual_away is not None and actual_total is not None):
                error_home = actual_home - predicted_home
                error_away = actual_away - predicted_away
                error_total = actual_total - predicted_total
                abs_error_total = abs(error_total)
                print(f"[Review] Calculated errors: home={error_home:+.1f}, away={error_away:+.1f}, total={error_total:+.1f}")
            else:
                print(f"[Review] WARNING: Could not calculate errors - predicted or actual values are None")
                print(f"[Review]   predicted: home={predicted_home}, away={predicted_away}, total={predicted_total}")
                print(f"[Review]   actual: home={actual_home}, away={actual_away}, total={actual_total}")
                error_home = 0
                error_away = 0
                error_total = 0
                abs_error_total = 0

            # Compute expected vs actual stats for AI Coach
            from api.utils.expected_vs_actual_stats import compute_all_expected_vs_actual

            expected_vs_actual = compute_all_expected_vs_actual(
                team_season_stats=team_season_stats,
                home_box_score=home_box_score,
                away_box_score=away_box_score,
                predicted_pace=predicted_pace
            )

            # Build detailed style stats for AI Model Coach
            expected_style_stats = None
            actual_style_stats = None
            expected_style_stats_json = None
            actual_style_stats_json = None

            try:
                # Build expected stats (what we predicted teams would do)
                if home_team_data and away_team_data:
                    expected_style_stats = build_expected_style_stats(
                        home_team_id,
                        away_team_id,
                        predicted_pace,
                        season='2025-26'
                    )
                    print(f"[StyleStats] Built expected stats for both teams")

                # Build actual stats (what teams actually did in the game)
                if home_team_data and away_team_data and home_box_score and away_box_score:
                    actual_style_stats = build_actual_style_stats(
                        game_id,
                        home_team_id,
                        away_team_id
                    )
                    print(f"[StyleStats] Built actual stats for both teams")

                # Convert to JSON for database storage
                if expected_style_stats:
                    expected_style_stats_json = json.dumps(expected_style_stats)
                if actual_style_stats:
                    actual_style_stats_json = json.dumps(actual_style_stats)

            except Exception as e:
                print(f"[StyleStats] Error building style stats: {e}")
                import traceback
                traceback.print_exc()

            # === COMPREHENSIVE LOGGING: Verify prediction/AI Coach sync ===
            print(f"\n{'='*80}")
            print(f"[AI COACH] Starting post-game analysis for game {game_id}")
            print(f"[AI COACH] PREDICTION SOURCE VERIFICATION:")
            print(f"  Sportsbook Line: {sportsbook_line}")
            print(f"  Predicted Total: {f'{predicted_total:.1f}' if predicted_total is not None else 'N/A'} ({f'{predicted_home:.1f}' if predicted_home is not None else 'N/A'} + {f'{predicted_away:.1f}' if predicted_away is not None else 'N/A'})")
            print(f"  Model Pick: {prediction_breakdown.get('recommendation', 'N/A') if prediction_breakdown else 'N/A'}")
            print(f"  Predicted Pace: {f'{predicted_pace:.1f}' if predicted_pace is not None else 'N/A'}")
            print(f"[AI COACH] ACTUAL RESULTS:")
            print(f"  Actual Total: {actual_total} ({actual_home} + {actual_away})")
            print(f"  Error: {f'{error_total:+.1f}' if error_total is not None else 'N/A'} points")
            print(f"[AI COACH] DATA AVAILABILITY:")
            print(f"  Has Prediction Breakdown: {bool(prediction_breakdown)}")
            print(f"  Has Team Season Stats: {bool(team_season_stats)}")
            print(f"  Has Last-5 Trends: {bool(last_5_trends)}")
            print(f"  Has Box Score Stats: {bool(home_box_score and away_box_score)}")
            print(f"  Has Expected vs Actual Stats: {bool(expected_vs_actual)}")
            print(f"  Has Similarity Data: {bool(similarity_data)}")
            print(f"{'='*80}\n")

            # Final verification before calling AI Coach
            print(f"[Review] Calling generate_game_review with:")
            print(f"  game_id={game_id}")
            print(f"  predicted_total={predicted_total}, predicted_home={predicted_home}, predicted_away={predicted_away}")
            print(f"  actual_total={actual_total}, actual_home={actual_home}, actual_away={actual_away}")
            print(f"  sportsbook_line={sportsbook_line}")

            ai_review = generate_game_review(
                game_id,
                home_team,
                away_team,
                predicted_total,
                actual_total,
                predicted_home,
                actual_home,
                predicted_away,
                actual_away,
                predicted_pace=predicted_pace,
                home_box_score=home_box_score,
                away_box_score=away_box_score,
                prediction_breakdown=prediction_breakdown,
                matchup_data=matchup_data,  # Add Matchup DNA for team identities
                team_season_stats=team_season_stats,  # Used for Advanced Splits context
                last_5_trends=last_5_trends,
                sportsbook_line=sportsbook_line,
                expected_vs_actual=expected_vs_actual,
                similarity_data=similarity_data,  # Add similarity/cluster analysis
                expected_style_stats=expected_style_stats,  # Add detailed expected stats
                actual_style_stats=actual_style_stats,  # Add detailed actual stats
                model="gpt-4.1-mini"
            )

            # Store in database
            with get_reviews_db() as conn:
                cursor = conn.cursor()
                now = datetime.now(timezone.utc).isoformat()

                cursor.execute('''
                    INSERT OR REPLACE INTO game_reviews (
                        game_id, home_team, away_team, game_date,
                        actual_home_score, actual_away_score, actual_total,
                        predicted_home_score, predicted_away_score, predicted_total,
                        sportsbook_line,
                        vision_confidence, vision_model, vision_raw_response,
                        error_home, error_away, error_total, abs_error_total,
                        ai_review_json, ai_review_model,
                        expected_style_stats_json, actual_style_stats_json,
                        screenshot_filename, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    game_id, home_team, away_team, game_date,
                    actual_home, actual_away, actual_total,
                    predicted_home, predicted_away, predicted_total,
                    sportsbook_line,  # Store the betting line
                    vision_confidence, vision_result.get('model', 'gpt-4.1-mini'),
                    vision_result.get('raw_response', ''),
                    error_home, error_away, error_total, abs_error_total,
                    json.dumps(ai_review), ai_review.get('model', 'gpt-4.1-mini'),
                    expected_style_stats_json, actual_style_stats_json,
                    filename, now, now
                ))
                conn.commit()

            print(f"[Review] Review saved to database for game {game_id}")

            return jsonify({
                'success': True,
                'review': {
                    'game_id': game_id,
                    'home_team': home_team,
                    'away_team': away_team,
                    'actual_home': actual_home,
                    'actual_away': actual_away,
                    'actual_total': actual_total,
                    'predicted_home': predicted_home,
                    'predicted_away': predicted_away,
                    'predicted_total': predicted_total,
                    'error_home': round(error_home, 1),
                    'error_away': round(error_away, 1),
                    'error_total': round(error_total, 1),
                    'vision_confidence': vision_confidence,
                    'ai_review': ai_review
                }
            })

        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        from api.utils.openai_client import OpenAIKeyMissingError
        import traceback
        traceback.print_exc()

        # Special handling for missing OpenAI API key
        if isinstance(e, OpenAIKeyMissingError):
            return jsonify({
                'success': False,
                'code': 'OPENAI_KEY_MISSING',
                'error': 'The AI key is not set on the server.'
            }), 500

        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/games/<game_id>/similar-opponent-boxscores')
def get_similar_opponent_boxscores(game_id):
    """
    Get box scores from games where each team played opponents similar to their current matchup.

    Returns both perspectives:
    - Home team vs teams similar to away team
    - Away team vs teams similar to home team

    Returns:
        {
            success: true,
            game_id: str,
            home_team: {...},  # Box scores for home team vs similar-away-type teams
            away_team: {...}   # Box scores for away team vs similar-home-type teams
        }
    """
    try:
        from api.utils.similar_opponent_boxscores import get_similar_opponent_boxscores as get_boxscores
        import sqlite3
        import os

        # Get game info
        db_path = os.path.join(os.path.dirname(__file__), 'api/data/nba_data.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT game_id, home_team_id, away_team_id, season
            FROM todays_games
            WHERE game_id = ?
        """, (game_id,))

        game = cursor.fetchone()
        conn.close()

        if not game:
            return jsonify({
                'success': False,
                'error': 'Game not found'
            }), 404

        home_team_id = game['home_team_id']
        away_team_id = game['away_team_id']
        season = game['season']

        # Get home team's performance vs teams similar to away team
        home_data = get_boxscores(
            subject_team_id=home_team_id,
            archetype_team_id=away_team_id,
            season=season,
            top_n_similar=3
        )

        # Get away team's performance vs teams similar to home team
        away_data = get_boxscores(
            subject_team_id=away_team_id,
            archetype_team_id=home_team_id,
            season=season,
            top_n_similar=3
        )

        # Format response
        response = {
            'success': True,
            'game_id': game_id,
            'home_team': {
                'team_id': home_data['subject_team_id'],
                'team_name': home_data['subject_team_name'],
                'team_abbr': home_data['subject_team_abbr'],
                'vs_similar_to': home_data['archetype_team_name'],
                'cluster_label': home_data['cluster_name'],
                'cluster_description': home_data['cluster_description'],
                'similar_teams': home_data['similar_teams'],
                'sample': home_data['sample'],
                'season_avg': home_data.get('season_avg', {})
            },
            'away_team': {
                'team_id': away_data['subject_team_id'],
                'team_name': away_data['subject_team_name'],
                'team_abbr': away_data['subject_team_abbr'],
                'vs_similar_to': away_data['archetype_team_name'],
                'cluster_label': away_data['cluster_name'],
                'cluster_description': away_data['cluster_description'],
                'similar_teams': away_data['similar_teams'],
                'sample': away_data['sample'],
                'season_avg': away_data.get('season_avg', {})
            }
        }

        return jsonify(response)

    except Exception as e:
        print(f"[SimilarOpponentBoxScores] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/games/<game_id>/review')
def get_game_review(game_id):
    """
    Get the AI review for a specific game (if it exists).

    Returns:
        {
            success: true,
            review: {...} or null if no review exists
        }
    """
    try:
        from api.utils.db_schema_game_reviews import get_connection as get_reviews_db

        with get_reviews_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM game_reviews WHERE game_id = ?
            ''', (game_id,))
            row = cursor.fetchone()

            if not row:
                return jsonify({'success': True, 'review': None})

            # Convert row to dict
            review = dict(row)

            # Parse JSON fields
            if review.get('ai_review_json'):
                review['ai_review'] = json.loads(review['ai_review_json'])

            return jsonify({'success': True, 'review': review})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/model-review/summary')
def model_coach_summary():
    """
    Get "Today's Model Coach" summary for a specific date.

    Query params:
        - date: YYYY-MM-DD (default: today)

    Returns:
        {
            success: true,
            summary: {
                date, total_games, avg_error,
                games_within_3, games_within_7,
                overall_performance, patterns, action_items,
                biggest_miss, biggest_win
            }
        }
    """
    try:
        from api.utils.db_schema_game_reviews import get_connection as get_reviews_db
        from api.utils.openai_client import generate_daily_coach_summary

        # Get date from query params (default: today)
        date_str = request.args.get('date')
        if not date_str:
            date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        # Fetch all reviews for this date
        with get_reviews_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM game_reviews
                WHERE game_date = ?
                ORDER BY abs_error_total DESC
            ''', (date_str,))
            rows = cursor.fetchall()

        if not rows:
            return jsonify({
                'success': True,
                'summary': {
                    'date': date_str,
                    'total_games': 0,
                    'message': 'No reviews available for this date yet.'
                }
            })

        # Convert rows to dicts
        reviews = []
        for row in rows:
            review_dict = dict(row)
            # Parse JSON if present
            if review_dict.get('ai_review_json'):
                review_dict['ai_review'] = json.loads(review_dict['ai_review_json'])
            reviews.append(review_dict)

        # Generate AI coaching summary
        print(f"[Model Coach] Generating daily summary for {date_str} ({len(reviews)} games)")
        summary = generate_daily_coach_summary(reviews, model="gpt-4.1-mini")

        summary['date'] = date_str

        return jsonify({'success': True, 'summary': summary})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/debug/openai-key')
def debug_openai_key():
    """
    Debug endpoint to check if OPENAI_API_KEY is configured.

    Returns only a boolean - does NOT expose the actual key value.

    Returns:
        { "hasKey": true/false }
    """
    from api.utils.openai_client import has_openai_key

    return jsonify({'hasKey': has_openai_key()})


# ============================================================================
# END GAME REVIEW ENDPOINTS
# ============================================================================


# Catch-all route to serve React app for client-side routing
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    """Serve React app for all non-API routes"""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return app.send_static_file(path)
    else:
        return app.send_static_file('index.html')

if __name__ == '__main__':
    # Checkpoint all databases on startup to ensure WAL changes are committed
    # This prevents data loss when processes are killed with SIGKILL (-9)
    try:
        from api.utils.db_checkpoint import checkpoint_all_databases
        checkpoint_all_databases()
    except Exception as e:
        print(f"[Server] Warning: Database checkpoint failed: {e}")

    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
