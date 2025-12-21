# 3PA and FTA Not Populating - FIXED

## Problem
The Matchup Indicators component was showing "-" for:
- 3-point attempts (3PA)
- Free throw attempts (FTA)

All other stats were displaying correctly.

---

## Root Cause
**The `get_team_stats()` function in `db_queries.py` was not returning FG3A and FTA fields.**

### Data Flow
1. Frontend component `MatchupIndicators.jsx` reads: `homeStats.fg3a_per_game` and `homeStats.fta_per_game`
2. `server.py` (lines 651-652, 678-679) sends these fields by reading from `home_overall` dictionary:
   ```python
   'fg3a_per_game': round(home_overall.get('FG3A', 0), 1),
   'fta_per_game': round(home_overall.get('FTA', 0), 1),
   ```
3. `home_overall` comes from `get_team_stats()` in `db_queries.py`
4. **BUT** `get_team_stats()` was only returning these fields:
   - GP, W, L, PTS, FG_PCT, FG3_PCT, FT_PCT, REB, AST, STL, BLK, TOV
5. **Missing:** FGA, FG3A, FTA

### Why This Happened
The database table `team_season_stats` **does have** these columns:
- `fg3a` (column 36)
- `fta` (column 38)
- `fg2a` (column 33) - needed to calculate total FGA

But the query function simply wasn't including them in the returned dictionary.

---

## The Fix

### File: `/api/utils/db_queries.py`

#### Change 1: Lines 173-190
Added shot attempt fields to `get_team_stats()` return value:

```python
# BEFORE (Lines 173-186):
result[split_type] = {
    'GP': row['games_played'],
    'W': row['wins'],
    'L': row['losses'],
    'PTS': row['ppg'],
    'FG_PCT': row['fg_pct'],
    'FG3_PCT': row['fg3_pct'],
    'FT_PCT': row['ft_pct'],
    'REB': row['rebounds'],
    'AST': row['assists'],
    'STL': row['steals'],
    'BLK': row['blocks'],
    'TOV': row['turnovers'],
}

# AFTER (Lines 173-190):
result[split_type] = {
    'GP': row['games_played'],
    'W': row['wins'],
    'L': row['losses'],
    'PTS': row['ppg'],
    'FG_PCT': row['fg_pct'],
    'FG3_PCT': row['fg3_pct'],
    'FT_PCT': row['ft_pct'],
    'REB': row['rebounds'],
    'AST': row['assists'],
    'STL': row['steals'],
    'BLK': row['blocks'],
    'TOV': row['turnovers'],
    # Shot attempts for MatchupIndicators
    'FGA': row['fg2a'] + row['fg3a'],  # Total FG attempts = 2PA + 3PA
    'FG3A': row['fg3a'],
    'FTA': row['fta'],
}
```

#### Change 2: Lines 695-717
Added shot attempt fields to fallback values (for teams with missing data):

```python
# Added to league average fallback:
'FGA': 88.0,  # League average ~88 FGA/game
'FG3A': 35.0,  # League average ~35 3PA/game
'FTA': 23.0,  # League average ~23 FTA/game
```

---

## Verification

### Before Fix:
```bash
curl http://localhost:8080/api/game_detail?game_id=0022501207
# Result:
fg3a_per_game: None
fta_per_game: None
```

### After Fix:
```bash
curl http://localhost:8080/api/game_detail?game_id=0022501207
# Result:
=== HOME STATS (NOP) ===
fg3a_per_game: 31.8
fta_per_game: 25.3

=== AWAY STATS (POR) ===
fg3a_per_game: 41.7
fta_per_game: 28.5
```

---

## Database Schema Reference

The database already had these columns in `team_season_stats`:
```
32|fg2m|REAL        → 2-point field goals made
33|fg2a|REAL        → 2-point field goals attempted
35|fg3m|REAL        → 3-point field goals made
36|fg3a|REAL        → 3-point field goals attempted ✅
37|ftm|REAL         → free throws made
38|fta|REAL         → free throws attempted ✅
```

Sample data:
```sql
SELECT team_id, fg3a, fta FROM team_season_stats
WHERE season = '2025-26' AND split_type = 'overall' LIMIT 5;

1610612737|overall|37.8|21.9  (Atlanta Hawks)
1610612738|overall|43.3|18.6  (Boston Celtics)
1610612739|overall|44.0|24.6  (Cleveland Cavaliers)
1610612740|overall|31.8|25.3  (New Orleans Pelicans)
```

---

## Summary

**Issue:** Missing FG3A and FTA in query results
**Fix:** Added 3 fields to `get_team_stats()` return dictionary
**Lines Changed:** 2 locations in `/api/utils/db_queries.py`
**Impact:** ✅ Matchup Indicators now display 3PA and FTA correctly

**Server restart required:** Yes (prediction cache cleared on restart)

---

## Related Components

### Frontend
- `/src/components/MatchupIndicators.jsx` (Lines 28-29, 84-85)
  - Reads `homeStats.fg3a_per_game` and `homeStats.fta_per_game`

### Backend
- `/server.py` (Lines 651-652, 678-679)
  - Sends `fg3a_per_game` and `fta_per_game` in API response
- `/api/utils/db_queries.py` (Lines 173-190)
  - ✅ **FIXED:** Now includes FGA, FG3A, FTA in returned dictionary
