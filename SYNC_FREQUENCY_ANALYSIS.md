# Sync Frequency Analysis: Every 3 Hours vs Daily

## What Gets Synced in a Full Sync

Each sync fetches 6 data types from the NBA API:

1. **Teams** (30 records) - Rarely changes
2. **Season Stats** (~90 records) - Updates after each game
3. **Game Logs** (Last 10 games per team = ~300 records) - Updates after each game
4. **Today's Games** (6-15 games) - Updates live during games
5. **Team Profiles** (~30 records) - Computed from game logs
6. **Scoring vs Pace** (~90 records) - Computed from game logs

**Total per sync:** ~540-600 records

---

## Impact of 3-Hour Sync vs Daily Sync

### ✅ What WOULD Improve

#### 1. **Live Game Updates**
- **Current (Daily at 9am MT):** Game scores update once per day
- **Every 3 Hours:** Games in progress get updated throughout the day
  - 9am MT: Pre-game data
  - 12pm MT: Early games (if any)
  - 3pm MT: Mid-day update
  - 6pm MT: **RIGHT BEFORE GAMES START** ⭐
  - 9pm MT: **DURING PRIME TIME** (most games)
  - 12am MT: Late games + final scores

**Impact:** 🔥 **HIGH** - Users see live/recent scores, not yesterday's data

#### 2. **Last 5/10 Game Trends**
- **Current:** "Last 5 games" uses data from yesterday
- **Every 3 Hours:** Fresh data includes games from last night
  - If a team played at 8pm ET (finishes ~10:30pm ET)
  - Daily sync at 9am MT next day (11am ET) ✓ Gets it
  - But users at 8am MT see stale data

**Impact:** 🟡 **MEDIUM** - Slightly fresher trend data

#### 3. **Injury/Lineup Changes**
- NBA API doesn't provide this in the endpoints we're syncing
- No impact

**Impact:** ⚪ **NONE**

#### 4. **Prediction Accuracy**
- Predictions use:
  - Season averages (changes slowly)
  - Last 10 games (updates nightly)
  - Defense tiers (updates nightly)
  - 3PT scoring splits (updates nightly)

**Impact:** 🟡 **LOW-MEDIUM** - Predictions would be 0-12 hours fresher max

---

### ⚠️ What COULD Be Affected

#### 1. **NBA API Rate Limits**
- **Current:** 1 sync/day = ~600 API calls/day
- **Every 3 hours:** 8 syncs/day = ~4,800 API calls/day
- **NBA API limits:** Unknown, but typically generous for CDN endpoints

**Risk:** 🟡 **LOW** - NBA CDN is designed for high traffic, but worth monitoring

#### 2. **Database Write Load**
- **Current:** 1 full table refresh/day
- **Every 3 hours:** 8 full table refreshes/day

**Impact:** 🟢 **MINIMAL** - SQLite handles this easily (600 records is tiny)

#### 3. **Server CPU/Memory**
- Each sync takes ~5-15 seconds of processing
- **Current:** 15 seconds/day
- **Every 3 hours:** 120 seconds/day (2 minutes total)

**Impact:** 🟢 **NEGLIGIBLE** - 2 minutes of CPU per day is nothing

#### 4. **Network Bandwidth**
- Each sync downloads ~500KB-2MB of JSON
- **Current:** ~2MB/day
- **Every 3 hours:** ~16MB/day

**Impact:** 🟢 **TRIVIAL** - 16MB is nothing for Railway

---

## Recommended Schedule

### Option 1: Strategic 3-Hour Windows (Recommended)
Instead of every 3 hours, sync at **key times**:

```bash
# Cron expressions (UTC times)
0 16 * * *  # 9am MT  - Morning pre-game
0 22 * * *  # 3pm MT  - Afternoon update
0 1 * * *   # 6pm MT  - RIGHT before games
0 4 * * *   # 9pm MT  - During prime time
0 7 * * *   # 12am MT - Late games + final scores
```

**Benefits:**
- Fresh data when users need it most
- Only 5 syncs/day instead of 8
- Catches all game times

### Option 2: Every 3 Hours (Simple)
```bash
0 */3 * * *  # Every 3 hours starting at midnight UTC
```

**Simplified schedule:**
- 9am, 12pm, 3pm, 6pm, 9pm, 12am MT (and 3am, 6am)

### Option 3: Keep Daily + On-Demand
```bash
0 16 * * *  # 9am MT daily sync
```

**Plus:** Manual trigger before big games or when needed

---

## Cost-Benefit Analysis

| Metric | Daily | Every 3 Hours | Strategic Windows |
|--------|-------|---------------|-------------------|
| API Calls | 600/day | 4,800/day | 3,000/day |
| Data Freshness | 0-24 hours old | 0-3 hours old | 0-3 hours old |
| Server Load | Minimal | Still minimal | Still minimal |
| Game Coverage | Next day | Live + next day | Live + next day |
| Complexity | Simple | Simple | Simple |

---

## My Recommendation

**Use Strategic Windows (Option 1):**

1. **9am MT** - Pre-game baseline
2. **6pm MT** - Right before most games start
3. **9pm MT** - During prime time (catch scores)
4. **12am MT** - Final scores for west coast games

**Why:**
- ✅ Users see live game updates
- ✅ Predictions use fresher data
- ✅ Minimal API/server impact
- ✅ Only 4 syncs/day (very reasonable)

**Cron config:**
```bash
# 9am MT (4pm UTC)
0 16 * * *

# 6pm MT (1am UTC next day)
0 1 * * *

# 9pm MT (4am UTC next day)
0 4 * * *

# 12am MT (7am UTC next day)
0 7 * * *
```

---

## What Would NOT Change

❌ Prediction algorithm (same logic)
❌ Historical data (stays the same)
❌ User interface (same features)
❌ Database schema (same structure)
❌ API endpoints (same routes)

## What WOULD Change

✅ **Today's Games board** - Shows live/recent scores
✅ **"Last 5 games" trends** - Uses data from last night
✅ **User experience** - Feels more "live" and current
✅ **Data staleness** - Max 3 hours old instead of 24 hours
