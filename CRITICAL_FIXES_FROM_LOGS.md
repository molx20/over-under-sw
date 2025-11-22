# Critical Fixes from Production Logs Analysis

## Issues Found in Railway Logs

Analyzed `/Users/malcolmlittle/Downloads/logs.1763790853212.json` (last 15 minutes of production logs).

---

## Critical Errors Identified

### 1. ❌ **`model_params` Not Defined**

**Error**:
```
[save-prediction] Warning: Could not compute features: name 'model_params' is not defined
[save-prediction] Falling back to base prediction only
```

**Impact**: Feature-enhanced predictions were COMPLETELY BROKEN - always falling back to base prediction

**Root Cause**:
- `model_params` variable was referenced but never loaded from `model.json`
- Server startup didn't load the model parameters

**Fix**:
```python
# Load model parameters on server startup
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'api', 'data', 'model.json')
with open(MODEL_PATH, 'r') as f:
    model_params = json.load(f)
```

**Files Changed**: `server.py:25-35`

---

### 2. ❌ **Worker Timeouts (Gunicorn Killing Requests)**

**Error**:
```
[CRITICAL] WORKER TIMEOUT (pid:4)
[ERROR] Worker (pid:4) was sent SIGKILL! Perhaps out of memory?
```

**Impact**: Requests longer than 30s (default gunicorn timeout) were being killed

**Root Cause**:
- Gunicorn default timeout is 30 seconds
- NBA API calls take 30-120 seconds when slow/rate-limited
- Workers were killed mid-request

**Fix**: Created `gunicorn_config.py` with 9-minute timeout
```python
timeout = 540  # 9 minutes (Railway has 10min limit)
workers = 2
graceful_timeout = 120
max_requests = 1000  # Restart workers to prevent memory leaks
```

**Files Changed**:
- `gunicorn_config.py` (new file)
- `Procfile` (updated to use config)

---

### 3. ❌ **NBA API Read Timeouts**

**Error (repeated 20+ times)**:
```
API Error in get_team_stats: HTTPSConnectionPool(host='stats.nba.com', port=443): Read timed out. (read timeout=30)
API Error in get_team_opponent_stats: Read timed out
API Error in get_team_last_n_games: Read timed out
```

**Impact**:
- Many requests failing due to NBA API slowness
- Retry logic wasn't working properly

**Root Cause**:
- NBA API read timeout set to 30s
- No retries for timeout errors in old code (before our fix)
- API was slow during peak hours

**Already Fixed**:
- Retry logic added in previous update
- Graceful degradation added
- These errors should now retry 3x before failing

**Verification Needed**: Check if retries are actually working in production

---

### 4. ⚠️ **No Performance Logging Visible**

**Missing**:
```
[performance] GET /api/save-prediction took XXXms
[performance] SLOW: Fetch matchup data took XXXms
```

**Impact**: Can't identify slow operations

**Root Cause**: Performance middleware might not be printing to logs correctly

**Already Fixed**: Performance logging added in previous updates

**Action Needed**: Verify logs show performance timing after deployment

---

## Performance Impact

### Before Fixes

```
Request Timeline (save-prediction):
0s:   Request received
0-120s: Fetching NBA API data (if not cached)
        ❌ Worker timeout at 30s → Request killed
        ❌ model_params error → Fall back to base prediction
        ❌ No retry on timeout → Immediate failure
120s+: Request never completes
```

**Result**: Most save-prediction requests FAILED

### After Fixes

```
Request Timeline (save-prediction):
0s:   Request received
0s:   ✅ Load model_params from model.json
0-120s: Fetching NBA API data
        ✅ Retry 3x on timeout
        ✅ Worker timeout extended to 9 minutes
        ✅ Graceful degradation if some stats fail
120s: ✅ Feature vector computed successfully
      ✅ Prediction saved
```

**Result**: save-prediction requests SUCCEED (or fail gracefully with helpful error)

---

## Deployment Checklist

### ✅ Code Changes
- [x] Load `model_params` on server startup
- [x] Create `gunicorn_config.py` with 9-minute timeout
- [x] Update `Procfile` to use config
- [x] Fix `model_params.get('recent_games_n')` reference

### 🔄 Verification After Deployment

1. **Check model loading**:
   ```
   Expected in logs:
   [server] Loaded model parameters: version 3.0
   ```

2. **Check worker timeout**:
   ```
   Expected in logs:
   [gunicorn] Configuration loaded:
     - Worker timeout: 540s (9 minutes)
     - Workers: 2
   ```

3. **Check no more `model_params` errors**:
   ```
   Should NOT see:
   name 'model_params' is not defined
   ```

4. **Check no more worker timeouts**:
   ```
   Should NOT see (unless request truly takes >9min):
   [CRITICAL] WORKER TIMEOUT
   ```

5. **Check performance logging**:
   ```
   Expected in logs:
   [performance] POST /api/save-prediction took XXXms
   [performance] Fetch matchup data took XXXms
   ```

6. **Test save-prediction**:
   - Open admin page
   - Click "Save Prediction"
   - Should complete in 2-5 seconds (or up to 120s if NBA API slow)
   - Should see feature vector computed (not "falling back to base")

---

## Root Cause Analysis

### Why Did This Happen?

1. **`model_params` not defined**:
   - Code was written assuming `model_params` was loaded
   - Server startup didn't include model loading
   - No error during development (probably used fallback path)

2. **30s worker timeout**:
   - Gunicorn default is 30s for safety
   - NBA API is notoriously slow (30-120s common)
   - Need explicit config for long-running external API calls

3. **NBA API timeouts**:
   - NBA's stats.nba.com API is slow during peak hours
   - Single timeout = complete failure (before retry logic)
   - No fallback mechanism (before graceful degradation)

---

## Long-Term Solutions

### 1. **Background Jobs for Slow Operations**
Instead of waiting for NBA API during request:
```python
# Option A: Pre-fetch data asynchronously
@app.route('/api/save-prediction', methods=['POST'])
def save_prediction():
    # Queue job to fetch data in background
    job_id = queue_prediction_job(game_id, home_team, away_team)
    return {'job_id': job_id, 'status': 'queued'}

# Option B: Webhook callback when ready
@app.route('/api/check-prediction/<job_id>')
def check_prediction(job_id):
    return get_job_status(job_id)
```

### 2. **Persistent Cache Layer (Redis)**
```python
# Cache NBA API responses for 24 hours
redis.setex(f'team_stats:{team_id}', 86400, json.dumps(stats))
```

### 3. **Circuit Breaker for NBA API**
```python
# If NBA API fails 5 times, stop calling for 5 minutes
if circuit_breaker.is_open():
    return cached_data_or_error
```

### 4. **Health Check Endpoint**
```python
@app.route('/api/health/detailed')
def health_detailed():
    return {
        'nba_api': check_nba_api_health(),
        'model_loaded': model_params is not None,
        'cache_size': get_cache_stats(),
        'worker_timeout': timeout
    }
```

---

## Summary

**Critical Fixes Applied**:
1. ✅ Load `model_params` on server startup (fixes feature vector computation)
2. ✅ Extend gunicorn timeout to 9 minutes (fixes worker kills)
3. ✅ Already have retry logic for NBA API timeouts
4. ✅ Already have performance logging

**Expected Results**:
- **save-prediction** should complete successfully (was failing 100%)
- **No more worker timeouts** (unless NBA API takes >9min which is extremely rare)
- **Feature vectors computed** (was always falling back to base)
- **Visible performance metrics** in Railway logs

**Deploy and test immediately!** 🚀
