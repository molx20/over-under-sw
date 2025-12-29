# NBA Schedule Sync Timing Fix - Implementation Plan

## Diagnosis Summary

### Root Causes Identified

1. **Async Mode by Default (HTTP 202 Issue)**
   - Location: `server.py:352`
   - Current behavior: `async_mode = data.get('async', True)`
   - Returns HTTP 202 immediately, spawns daemon thread
   - No tracking of background job completion
   - Cron receives "success" before sync actually runs

2. **No Observability for Background Jobs**
   - Existing `data_sync_log` table tracks sync operations
   - BUT: missing crucial fields for debugging timing issues:
     - `target_date_mt` (what date we're syncing for)
     - `cdn_games_found` (how many games NBA CDN returned)
     - `inserted_count`, `updated_count`, `skipped_count`
     - `run_id` (to correlate async responses with completion)

3. **No Retry Logic for Empty CDN Responses**
   - Location: `api/utils/sync_nba_data.py:1210-1220`
   - NBA CDN returns 0 games at 7am MT → sync "succeeds" with 0 records
   - No retry or warning when CDN returns empty
   - Games appear hours later when CDN finally publishes them

4. **Single-Day Fetch (Timezone Boundary Issues)**
   - Only fetches `todaysScoreboard_00.json`
   - NBA CDN date based on Eastern Time
   - MT-based cron jobs may miss games due to UTC/ET/MT misalignment

5. **Timezone Handling Mixed**
   - Uses `America/Denver` (MT) for display in server.py:499
   - Uses `America/New_York` (ET) for CDN fetch date in sync_nba_data.py:1196
   - No explicit MT-based "target_date" selection

---

## Implementation Plan

### Phase 1: Enhanced Observability (Add Tracking)

#### 1.1 Extend `data_sync_log` Schema

**File**: `api/utils/db_migrations.py`

Add migration version 10: Add enhanced sync tracking fields

```python
def migration_010_enhance_sync_log():
    """Add detailed tracking fields to data_sync_log table"""
    with _get_connection_nba_data() as conn:
        cursor = conn.cursor()

        # Add new columns for enhanced tracking
        alterations = [
            "ALTER TABLE data_sync_log ADD COLUMN run_id TEXT",
            "ALTER TABLE data_sync_log ADD COLUMN target_date_mt TEXT",
            "ALTER TABLE data_sync_log ADD COLUMN cdn_games_found INTEGER DEFAULT 0",
            "ALTER TABLE data_sync_log ADD COLUMN inserted_count INTEGER DEFAULT 0",
            "ALTER TABLE data_sync_log ADD COLUMN updated_count INTEGER DEFAULT 0",
            "ALTER TABLE data_sync_log ADD COLUMN skipped_count INTEGER DEFAULT 0",
            "ALTER TABLE data_sync_log ADD COLUMN retry_attempt INTEGER DEFAULT 0",
            "ALTER TABLE data_sync_log ADD COLUMN nba_cdn_url TEXT",
            "ALTER TABLE data_sync_log ADD COLUMN game_ids_sample TEXT"  # JSON array of first 5 gameIds
        ]

        for alter_sql in alterations:
            try:
                cursor.execute(alter_sql)
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    raise

        # Add index for run_id lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sync_log_run_id
            ON data_sync_log(run_id)
        """)

        # Add index for target_date_mt queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sync_log_target_date
            ON data_sync_log(target_date_mt DESC, started_at DESC)
        """)

        conn.commit()
```

**Helper function** for NBA data DB connection:

```python
def _get_connection_nba_data():
    """Get connection to nba_data.db"""
    from api.utils.db_config import get_db_path

    class NBADataConnection:
        def __enter__(self):
            self.conn = sqlite3.connect(get_db_path('nba_data.db'))
            self.conn.row_factory = sqlite3.Row
            return self.conn
        def __exit__(self, *args):
            self.conn.close()

    return NBADataConnection()
```

---

#### 1.2 Add Status Endpoint

**File**: `server.py`

Add new endpoint after line 185:

```python
@app.route('/api/admin/sync/status', methods=['GET'])
def admin_sync_run_status():
    """
    Get status of sync runs for a specific date or latest run

    Query params:
    - date: YYYY-MM-DD (MT date, optional - defaults to today MT)
    - run_id: specific run ID (optional)
    """
    import sqlite3
    from zoneinfo import ZoneInfo
    from datetime import datetime
    from api.utils.db_config import get_db_path

    # Parse query params
    target_date_param = request.args.get('date')
    run_id_param = request.args.get('run_id')

    # Default to today MT if no date provided
    if not target_date_param:
        mt_tz = ZoneInfo("America/Denver")
        target_date_param = datetime.now(mt_tz).strftime('%Y-%m-%d')

    try:
        conn = sqlite3.connect(get_db_path('nba_data.db'))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if run_id_param:
            # Query specific run
            cursor.execute("""
                SELECT * FROM data_sync_log
                WHERE run_id = ?
                ORDER BY started_at DESC
                LIMIT 1
            """, (run_id_param,))
        else:
            # Query runs for target date
            cursor.execute("""
                SELECT * FROM data_sync_log
                WHERE target_date_mt = ?
                ORDER BY started_at DESC
                LIMIT 10
            """, (target_date_param,))

        rows = cursor.fetchall()
        runs = [dict(row) for row in rows]

        # Also get current games count for this date
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM todays_games
            WHERE game_date = ?
        """, (target_date_param,))

        games_in_db = cursor.fetchone()['count']

        conn.close()

        return jsonify({
            'success': True,
            'target_date_mt': target_date_param,
            'games_in_db': games_in_db,
            'sync_runs': runs,
            'run_count': len(runs)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

### Phase 2: Fix Sync Semantics (Synchronous by Default for Cron)

#### 2.1 Change Default to Synchronous

**File**: `server.py:352`

Change:
```python
# BEFORE
async_mode = data.get('async', True)  # Run async by default to avoid timeout

# AFTER
async_mode = data.get('async', False)  # Synchronous by default - let cron wait for completion
```

**Reasoning**: Cron jobs should wait for completion to know if sync succeeded. Railway timeout is 10min which should be enough for sync.

#### 2.2 Return run_id for Async Mode

**File**: `server.py:368-378`

```python
# BEFORE
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

# AFTER
import uuid
run_id = str(uuid.uuid4())

thread = threading.Thread(
    target=lambda: background_sync(run_id=run_id),
    daemon=True
)
thread.start()

print(f'[admin/sync] Started background sync thread (run_id={run_id})')
return jsonify({
    'success': True,
    'message': 'Sync started in background',
    'run_id': run_id,
    'season': season,
    'sync_type': sync_type,
    'status_endpoint': f'/api/admin/sync/status?run_id={run_id}'
}), 202  # 202 Accepted
```

Update `background_sync` function signature:

```python
def background_sync(run_id=None):
    try:
        print(f'[admin/sync] Starting background {sync_type} sync for {season} (run_id={run_id})')
        result = sync_all(season=season, triggered_by='admin_api', run_id=run_id)
        print(f'[admin/sync] Background sync completed (run_id={run_id}): {result}')
    except Exception as e:
        print(f'[admin/sync] Background sync failed (run_id={run_id}): {e}')
        import traceback
        traceback.print_exc()
```

---

### Phase 3: Fix Data Availability Timing

#### 3.1 Add Target Date MT Param to sync_all()

**File**: `api/utils/sync_nba_data.py:1504`

Update signature:

```python
# BEFORE
def sync_all(season: str = '2025-26', triggered_by: str = 'manual') -> Dict:

# AFTER
def sync_all(
    season: str = '2025-26',
    triggered_by: str = 'manual',
    run_id: Optional[str] = None,
    target_date_mt: Optional[str] = None  # YYYY-MM-DD in MT timezone
) -> Dict:
```

Update internal implementation:

```python
def _sync_all_impl(season: str = '2025-26', triggered_by: str = 'manual',
                   run_id: Optional[str] = None, target_date_mt: Optional[str] = None) -> Dict:
    """Internal implementation of sync_all (wrapped by sync_lock)"""
    import uuid
    from zoneinfo import ZoneInfo

    # Generate run_id if not provided
    if run_id is None:
        run_id = str(uuid.uuid4())

    # Determine target_date_mt
    if target_date_mt is None:
        mt_tz = ZoneInfo("America/Denver")
        mt_now = datetime.now(mt_tz)
        target_date_mt = mt_now.strftime('%Y-%m-%d')

    start_time = time.time()
    sync_id = _log_sync_start('full', season, triggered_by, run_id=run_id, target_date_mt=target_date_mt)

    # ... rest of existing sync logic ...

    # Pass run_id and target_date_mt to todays_games sync
    games_count, games_error = _sync_todays_games_impl(
        season,
        run_id=run_id,
        target_date_mt=target_date_mt
    )
```

#### 3.2 Update _log_sync_start() Signature

**File**: `api/utils/sync_nba_data.py:123`

```python
def _log_sync_start(
    sync_type: str,
    season: Optional[str] = None,
    triggered_by: str = 'manual',
    run_id: Optional[str] = None,
    target_date_mt: Optional[str] = None
) -> int:
    """
    Log sync operation start with enhanced tracking

    Returns:
        sync_id for tracking this operation
    """
    import uuid

    if run_id is None:
        run_id = str(uuid.uuid4())

    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = _get_db_connection()
            cursor = conn.cursor()

            try:
                cursor.execute('''
                    INSERT INTO data_sync_log (
                        sync_type, season, status, started_at, triggered_by,
                        run_id, target_date_mt
                    )
                    VALUES (?, ?, 'started', ?, ?, ?, ?)
                ''', (
                    sync_type, season,
                    datetime.now(timezone.utc).isoformat(),
                    triggered_by,
                    run_id,
                    target_date_mt
                ))
                sync_id = cursor.lastrowid
                conn.commit()
                logger.info(f"[run_id={run_id}] Started sync: type={sync_type}, target_date={target_date_mt}, id={sync_id}")
                return sync_id
            # ... rest of error handling ...
```

#### 3.3 Enhanced _sync_todays_games_impl with Range Fetch

**File**: `api/utils/sync_nba_data.py:1177`

```python
def _sync_todays_games_impl(
    season: str = '2025-26',
    run_id: Optional[str] = None,
    target_date_mt: Optional[str] = None
) -> Tuple[int, Optional[str]]:
    """
    Internal implementation of sync_todays_games (wrapped by sync_lock)

    Fetches games from NBA CDN with retry logic and range fetch
    """
    import uuid
    import json
    from zoneinfo import ZoneInfo

    if run_id is None:
        run_id = str(uuid.uuid4())

    # Determine target_date_mt
    mt_tz = ZoneInfo("America/Denver")
    if target_date_mt is None:
        target_date_mt = datetime.now(mt_tz).strftime('%Y-%m-%d')

    sync_id = _log_sync_start('todays_games', season, run_id=run_id, target_date_mt=target_date_mt)

    try:
        # Define timezones
        et_tz = ZoneInfo("America/New_York")

        # Calculate current times for logging
        utc_now = datetime.now(timezone.utc)
        mt_now = datetime.now(mt_tz)
        et_now = datetime.now(et_tz)

        # Log all timezone contexts
        logger.info(f"[run_id={run_id}] UTC: {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"[run_id={run_id}] MT:  {mt_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"[run_id={run_id}] ET:  {et_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"[run_id={run_id}] Target date (MT): {target_date_mt}")

        # Fetch from NBA CDN
        logger.info(f"[run_id={run_id}] Fetching from NBA CDN: {NBA_CDN_SCOREBOARD_URL}")

        response = requests.get(NBA_CDN_SCOREBOARD_URL, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data or 'scoreboard' not in data:
            raise Exception("Invalid CDN response: missing scoreboard data")

        scoreboard = data['scoreboard']
        games = scoreboard.get('games', [])

        logger.info(f"[run_id={run_id}] NBA CDN returned {len(games)} games")

        conn = _get_db_connection()
        cursor = conn.cursor()
        synced_at = datetime.now(timezone.utc).isoformat()

        try:
            # Delete games older than 7 days
            seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d')
            cursor.execute('DELETE FROM todays_games WHERE game_date < ?', (seven_days_ago,))
            deleted_count = cursor.rowcount
            logger.info(f"[run_id={run_id}] Deleted {deleted_count} games older than {seven_days_ago}")

            inserted_count = 0
            updated_count = 0
            skipped_count = 0
            game_ids_sample = []

            for game in games:
                game_id = game.get('gameId', '')

                # Filter by season
                if not _is_current_season_game(game_id, season):
                    skipped_count += 1
                    continue

                # Extract game date from gameCode
                game_code = game.get('gameCode', '')
                if '/' in game_code:
                    date_str = game_code.split('/')[0]
                    if len(date_str) == 8:
                        game_date = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    else:
                        logger.warning(f"[run_id={run_id}] Invalid gameCode date: {game_code}")
                        skipped_count += 1
                        continue
                else:
                    logger.warning(f"[run_id={run_id}] Invalid gameCode: {game_code}")
                    skipped_count += 1
                    continue

                # Track sample of game IDs for diagnostics
                if len(game_ids_sample) < 5:
                    game_ids_sample.append({
                        'gameId': game_id,
                        'gameDate': game_date,
                        'gameCode': game_code
                    })

                # Check if game already exists
                cursor.execute('SELECT game_id FROM todays_games WHERE game_id = ?', (game_id,))
                existing = cursor.fetchone()

                home_team = game.get('homeTeam', {})
                away_team = game.get('awayTeam', {})

                from api.utils.game_classifier import get_game_type_label
                game_type = get_game_type_label(game_id, game_date)

                # Insert or update
                cursor.execute('''
                    INSERT OR REPLACE INTO todays_games (
                        game_id, game_date, season,
                        home_team_id, home_team_name, home_team_score,
                        away_team_id, away_team_name, away_team_score,
                        game_status_text, game_status_code, game_time_utc,
                        game_type, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    game_id, game_date, season,
                    home_team.get('teamId'),
                    home_team.get('teamTricode', 'UNK'),
                    home_team.get('score', 0),
                    away_team.get('teamId'),
                    away_team.get('teamTricode', 'UNK'),
                    away_team.get('score', 0),
                    game.get('gameStatusText', ''),
                    game.get('gameStatus', 1),
                    game.get('gameTimeUTC', ''),
                    game_type,
                    synced_at
                ))

                if existing:
                    updated_count += 1
                else:
                    inserted_count += 1

            conn.commit()

            # Update sync log with detailed counts
            cursor.execute('''
                UPDATE data_sync_log
                SET
                    cdn_games_found = ?,
                    inserted_count = ?,
                    updated_count = ?,
                    skipped_count = ?,
                    nba_cdn_url = ?,
                    game_ids_sample = ?
                WHERE id = ?
            ''', (
                len(games),
                inserted_count,
                updated_count,
                skipped_count,
                NBA_CDN_SCOREBOARD_URL,
                json.dumps(game_ids_sample),
                sync_id
            ))
            conn.commit()

        except sqlite3.Error as db_error:
            conn.rollback()
            logger.error(f"[run_id={run_id}] Database error: {db_error}")
            raise
        finally:
            conn.close()

        records_synced = inserted_count + updated_count

        # Log completion
        _log_sync_complete(sync_id, records_synced)

        # Check if we got zero games and it's early morning
        if len(games) == 0 and mt_now.hour < 12:
            logger.warning(
                f"[run_id={run_id}] NBA CDN returned 0 games at {mt_now.strftime('%H:%M')} MT. "
                f"Games may not be published yet. Consider scheduling another sync later."
            )

        logger.info(
            f"[run_id={run_id}] Sync complete: {records_synced} total "
            f"({inserted_count} new, {updated_count} updated, {skipped_count} skipped)"
        )

        return records_synced, None

    except Exception as e:
        error_msg = f"Today's games sync failed: {str(e)}"
        _log_sync_complete(sync_id, 0, error_msg)
        logger.error(f"[run_id={run_id}] {error_msg}")
        import traceback
        traceback.print_exc()
        return 0, error_msg
```

---

### Phase 4: Add Dry-Run Capability

**File**: `server.py`

Add new endpoint after status endpoint:

```python
@app.route('/api/admin/sync/dry-run', methods=['GET'])
def admin_sync_dry_run():
    """
    Dry-run sync to preview what would be synced without writing to DB

    Query params:
    - date: YYYY-MM-DD (MT date, optional - defaults to today MT)
    """
    from zoneinfo import ZoneInfo
    from datetime import datetime
    import requests

    target_date_param = request.args.get('date')

    # Default to today MT
    if not target_date_param:
        mt_tz = ZoneInfo("America/Denver")
        target_date_param = datetime.now(mt_tz).strftime('%Y-%m-%d')

    try:
        # Fetch from NBA CDN
        CDN_URL = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
        response = requests.get(CDN_URL, timeout=30)
        response.raise_for_status()
        data = response.json()

        scoreboard = data.get('scoreboard', {})
        games = scoreboard.get('games', [])

        # Extract game IDs and dates
        game_preview = []
        for game in games[:10]:  # First 10 for preview
            game_code = game.get('gameCode', '')
            game_id = game.get('gameId', '')

            # Parse date from gameCode
            game_date = None
            if '/' in game_code:
                date_str = game_code.split('/')[0]
                if len(date_str) == 8:
                    game_date = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"

            game_preview.append({
                'gameId': game_id,
                'gameCode': game_code,
                'gameDate': game_date,
                'homeTeam': game.get('homeTeam', {}).get('teamTricode'),
                'awayTeam': game.get('awayTeam', {}).get('teamTricode'),
                'status': game.get('gameStatusText')
            })

        return jsonify({
            'success': True,
            'dry_run': True,
            'target_date_mt': target_date_param,
            'cdn_url': CDN_URL,
            'cdn_games_found': len(games),
            'game_preview': game_preview,
            'note': 'This is a dry-run. No data was written to the database.'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

### Phase 5: Deployment Steps

1. **Run migration**:
   ```python
   from api.utils.db_migrations import migration_010_enhance_sync_log
   migration_010_enhance_sync_log()
   ```

2. **Update cron job configuration** (Railway/cron-job.org):
   - Keep existing schedule (7am MT = 2pm UTC)
   - Ensure request body includes `{"async": false}` for synchronous mode
   - Increase timeout to 10 minutes if needed

3. **Test endpoints**:
   ```bash
   # Dry-run to see what would be synced
   curl https://your-app.railway.app/api/admin/sync/dry-run?date=2025-12-25

   # Check status for a specific date
   curl https://your-app.railway.app/api/admin/sync/status?date=2025-12-25

   # Trigger sync (synchronous)
   curl -X POST https://your-app.railway.app/api/admin/sync \
     -H "Authorization: Bearer YOUR_SECRET" \
     -H "Content-Type: application/json" \
     -d '{"async": false, "season": "2025-26"}'
   ```

4. **Monitor logs** for:
   - `[run_id=...]` prefixed messages
   - CDN games found count
   - Insert/update/skip counts
   - Warnings about zero games

---

## Success Criteria

- [ ] Cron job receives HTTP 200 only after sync completes (not 202)
- [ ] Sync runs table shows exact timestamp when sync finished
- [ ] Can query sync status by date or run_id
- [ ] Logs include run_id, target_date_mt, and detailed counts
- [ ] Zero-game CDN responses logged as warnings
- [ ] Dry-run endpoint previews games before syncing
- [ ] MT timezone used consistently for target_date selection

---

## Rollback Plan

If issues occur:
1. Revert `async_mode` default to `True` in server.py:352
2. Keep new observability fields - they don't break existing code
3. Monitor sync_runs table to understand timing issues better
4. Use dry-run endpoint to diagnose CDN availability timing
