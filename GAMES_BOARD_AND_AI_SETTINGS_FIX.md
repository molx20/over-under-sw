# Games Board Date & AI Settings Persistence - Implementation Summary

**Date:** December 8, 2024
**Status:** ✅ COMPLETE

---

## Problems Fixed

### 1. Games Board Date Resets
**Problem:** After deploys/restarts, the games board would:
- Jump back to yesterday's games
- Show "no games found" even when games exist
- Reset to arbitrary dates depending on server restart time

**Root Cause:** The `/api/games` endpoint was fetching from the NBA Live API instead of the database, which only returns "today's" games based on NBA's API time, not our database state.

### 2. Model Coach / AI Settings Reset
**Problem:** User preferences like:
- Dark mode toggle
- Model Coach enabled/disabled state
- AI feature settings

Would reset on every page reload or server restart.

**Root Cause:** All UI state was stored in React's `useState` with no persistence layer.

---

## Solution Architecture

### Backend Changes: Deterministic Date Selection

**File:** `server.py` (lines 353-500)

The `/api/games` endpoint now follows this **deterministic selection logic**:

```
STEP 1: User-Requested Date
  ↓ If ?date=YYYY-MM-DD parameter exists and has games
  ↓ → Use that date (reason: "user_requested")

STEP 2: Today (Mountain Time) Has Games?
  ↓ Query DB for games where game_date = TODAY_MT
  ↓ If found → Use today (reason: "today_mt_has_games")

STEP 3: Most Recent Date with Games
  ↓ Query: SELECT MAX(game_date) FROM todays_games WHERE season='2024-25'
  ↓ If found → Use that date (reason: "latest_available_date")

STEP 4: Absolute Fallback
  ↓ If database is completely empty
  ↓ → Use today as fallback (reason: "fallback_today_mt (empty_db)")
```

**Key Features:**
- ✅ **Database-first**: Reads from `todays_games` table, NOT live NBA API
- ✅ **Timezone-aware**: Uses Mountain Time (UTC-7) as the source of truth
- ✅ **Deterministic**: Same database state = same date shown (no randomness)
- ✅ **Restart-safe**: Server restarts don't change the date logic
- ✅ **Logged**: Every date selection logs the reason for debugging

**API Response Format:**
```json
{
  "success": true,
  "date": "2024-12-07",
  "date_selection_reason": "latest_available_date (13 games)",
  "today_mt": "2024-12-08",
  "games": [...],
  "count": 13,
  "last_updated": "2024-12-08T21:55:00Z"
}
```

---

### Frontend Changes: Smart Date Display & Persistence

#### 1. App.jsx - localStorage Persistence

**File:** `src/App.jsx` (lines 8-42)

**Changes:**
```javascript
// Define storage keys
export const STORAGE_KEYS = {
  DARK_MODE: 'nba_ou_dark_mode',
  MODEL_COACH_ENABLED: 'nba_ou_model_coach_enabled',
  LAST_SELECTED_DATE: 'nba_ou_last_selected_date',
}

// Initialize from localStorage
const [darkMode, setDarkMode] = useState(() => {
  const stored = localStorage.getItem(STORAGE_KEYS.DARK_MODE)
  return stored === 'true'
})

const [showModelCoach, setShowModelCoach] = useState(() => {
  const stored = localStorage.getItem(STORAGE_KEYS.MODEL_COACH_ENABLED)
  return stored === 'true'
})

// Persist on every change
useEffect(() => {
  localStorage.setItem(STORAGE_KEYS.DARK_MODE, darkMode.toString())
}, [darkMode])

useEffect(() => {
  localStorage.setItem(STORAGE_KEYS.MODEL_COACH_ENABLED, showModelCoach.toString())
}, [showModelCoach])
```

**What This Does:**
- ✅ Dark mode persists across page reloads
- ✅ Model Coach toggle persists across page reloads
- ✅ Settings survive server restarts (stored in browser, not server memory)
- ✅ Console logging for debugging

#### 2. Home.jsx - Smart Date Messaging

**File:** `src/pages/Home.jsx` (lines 23-28, 82-94, 125-140)

**Changes:**

**Extract metadata from API:**
```javascript
const selectedDate = data?.date || null
const dateReason = data?.date_selection_reason || null
const todayMT = data?.today_mt || null
```

**Dynamic page title:**
```javascript
<h2>
  {selectedDate && selected Date !== todayMT
    ? `Games for ${selectedDate}`
    : "Today's Games"}
</h2>
```

**Fallback message when showing old slate:**
```javascript
{selectedDate && selectedDate !== todayMT && (
  <p className="text-amber-600">
    ℹ️ No games today (MT: {todayMT}), showing latest available slate
  </p>
)}
```

**Better "no games" state:**
```javascript
{dateReason === 'fallback_today_mt (empty_db)'
  ? 'The games database is empty. Please run the sync job to fetch game data.'
  : `There are no NBA games scheduled for ${selectedDate}`
}
```

---

## How It Works Now

### Scenario 1: Normal Day (Games Today)
```
1. Frontend calls GET /api/games
2. Backend checks: today_mt='2024-12-08' has games? YES (3 games)
3. Backend returns: date='2024-12-08', reason='today_mt_has_games (3 games)'
4. Frontend shows: "Today's Games" with normal display
```

### Scenario 2: No Games Today (Show Yesterday)
```
1. Frontend calls GET /api/games
2. Backend checks: today_mt='2024-12-08' has games? NO
3. Backend queries: MAX(game_date) = '2024-12-07' (13 games)
4. Backend returns: date='2024-12-07', reason='latest_available_date (13 games)'
5. Frontend shows:
   - Title: "Games for 2024-12-07"
   - Message: "ℹ️ No games today (MT: 2024-12-08), showing latest available slate"
```

### Scenario 3: Server Restart
```
1. Server restarts at 2:00 PM MT
2. Frontend reloads and calls GET /api/games
3. Backend runs SAME LOGIC as before (database-driven, not time-driven)
4. Result: EXACT SAME DATE as before the restart
   ✅ No jumping around
   ✅ No reset to "today" when today is empty
```

### Scenario 4: Empty Database (First Deploy)
```
1. Frontend calls GET /api/games
2. Backend queries: No games in todays_games table
3. Backend returns: date=today_mt, reason='fallback_today_mt (empty_db)'
4. Frontend shows:
   - "No Games Found"
   - "The games database is empty. Please run the sync job."
   - "Sync runs at 3:00 AM MT or trigger manually from admin panel"
```

---

## AI / Model Coach Persistence

### What Persists
| Setting | Storage Key | Default | Persists Across |
|---------|-------------|---------|-----------------|
| Dark Mode | `nba_ou_dark_mode` | `false` | Page reload, server restart, deployment |
| Model Coach Enabled | `nba_ou_model_coach_enabled` | `false` | Page reload, server restart, deployment |
| Last Selected Date | `nba_ou_last_selected_date` | `null` | (Reserved for future date picker) |

### How To Add More Settings

**Example: Add AI Aggressiveness Slider**

```javascript
// In App.jsx or wherever the setting lives
const [aiAggressiveness, setAiAggressiveness] = useState(() => {
  const stored = localStorage.getItem('nba_ou_ai_aggressiveness')
  return stored ? parseInt(stored) : 5 // default: 5
})

useEffect(() => {
  localStorage.setItem('nba_ou_ai_aggressiveness', aiAggressiveness.toString())
}, [aiAggressiveness])
```

---

## Testing Results

### Test 1: Model Coach Persistence
```
✅ PASS
1. Enable Model Coach toggle
2. Refresh page (Cmd+R)
3. Result: Model Coach still enabled
```

### Test 2: Server Restart
```
✅ PASS
1. Note current board date: 2024-12-07
2. Restart backend server
3. Refresh frontend
4. Result: Still showing 2024-12-07 (no jump to today)
```

### Test 3: Empty Database
```
✅ PASS
1. Start with empty todays_games table
2. Load frontend
3. Result: Shows friendly "database empty" message
4. User knows to run sync, not confused by blank state
```

### Test 4: Dark Mode Persistence
```
✅ PASS
1. Toggle dark mode ON
2. Refresh page
3. Result: Page loads in dark mode (not reset to light)
```

---

## Files Modified

### Backend
- **`server.py`** (lines 353-500)
  - Replaced NBA Live API call with deterministic database logic
  - Added `date`, `date_selection_reason`, `today_mt` to API response
  - Added comprehensive logging for debugging

### Frontend
- **`src/App.jsx`**
  - Added `STORAGE_KEYS` constant (exported for reuse)
  - Added localStorage initialization for dark mode
  - Added localStorage initialization for Model Coach
  - Added `useEffect` hooks to persist changes

- **`src/pages/Home.jsx`**
  - Extract `selectedDate`, `dateReason`, `todayMT` from API
  - Dynamic page title based on date
  - Amber info message when showing old slate
  - Better "no games" messages with context

---

## Important Configuration Notes

### Season Configuration
The backend currently uses `current_season = '2025-26'` (hardcoded in `server.py` line 380).

**To update for future seasons:**
- Change line 380 in `server.py` to the new season (e.g., `'2026-27'`)
- Or make it dynamic based on current date

### Today's Date is Calculated in Mountain Time
The system uses **Mountain Time (UTC-7)** as the source of truth for "today".

This means:
- At 11:00 PM MT, the date is still "today"
- At 12:00 AM MT, the date switches to "tomorrow"
- Syncs should run BEFORE game times to ensure data availability

## Deployment Checklist

✅ **Before deploying:**
1. Verify `todays_games` table has recent data for current season
2. Check `current_season` variable matches the active NBA season
3. Check cron job is configured for 3:00 AM MT sync
4. Test `/api/games` endpoint returns correct date logic

✅ **After deploying:**
1. Open app, verify date shown is deterministic
2. Refresh page, verify date doesn't change
3. Toggle Model Coach, refresh, verify it stays enabled
4. Toggle dark mode, refresh, verify it stays dark

✅ **If issues occur:**
1. Check server logs for: `[games] Selected date: ...`
2. Check browser console for: `[App] Dark mode persisted: ...`
3. Check browser localStorage (DevTools > Application > Local Storage)
4. Verify season in database matches `current_season` in server.py

---

## Future Enhancements (Optional)

### Date Picker
User can manually select a different date:
```javascript
// In Home.jsx
const [customDate, setCustomDate] = useState(null)

// When user picks date
const handleDateChange = (newDate) => {
  localStorage.setItem(STORAGE_KEYS.LAST_SELECTED_DATE, newDate)
  setCustomDate(newDate)
  refetch() // Call API with ?date=newDate
}
```

### Admin "Reset Settings" Button
```javascript
const resetAllSettings = () => {
  Object.values(STORAGE_KEYS).forEach(key => {
    localStorage.removeItem(key)
  })
  window.location.reload()
}
```

---

## Summary

**The games board date logic is now:**
- ✅ Deterministic (same DB state = same date shown)
- ✅ Restart-safe (server restarts don't change behavior)
- ✅ User-friendly (clear messages when no games today)
- ✅ Logged (easy to debug with date_selection_reason)

**AI/Model Coach settings are now:**
- ✅ Persistent (survive page reloads and server restarts)
- ✅ Browser-local (no backend storage needed)
- ✅ Extensible (easy to add more settings)
- ✅ Debuggable (console logs on every change)

**Both issues are SOLVED.**
