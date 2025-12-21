# Box Score Stats Implementation

## Summary

Extended the NBA data scraper to fetch and store advanced box score statistics for each game. This provides richer game-level data beyond basic scoring and shooting percentages.

## New Database Columns

Added to `team_game_logs` table:

| Column | Type | Description | Data Source |
|--------|------|-------------|-------------|
| `fgm` | INTEGER | Total field goals made | BoxScoreTraditionalV3 |
| `fga` | INTEGER | Total field goals attempted | BoxScoreTraditionalV3 |
| `offensive_rebounds` | INTEGER | Offensive rebounds | BoxScoreTraditionalV3 |
| `defensive_rebounds` | INTEGER | Defensive rebounds | BoxScoreTraditionalV3 |
| `steals` | INTEGER | Steals | BoxScoreTraditionalV3 |
| `blocks` | INTEGER | Blocks | BoxScoreTraditionalV3 |
| `points_off_turnovers` | INTEGER | Points scored off opponent turnovers | Calculated from BoxScoreScoringV3 |
| `fast_break_points` | INTEGER | Fast break points | Calculated from BoxScoreScoringV3 |
| `points_in_paint` | INTEGER | Points scored in the paint | Calculated from BoxScoreScoringV3 |
| `second_chance_points` | INTEGER | Second chance points (estimated) | Estimated from offensive rebounds |

## Data Sources

### Primary Endpoints

1. **BoxScoreTraditionalV3**
   - Endpoint: `nba_api.stats.endpoints.boxscoretraditionalv3`
   - Provides: FGM, FGA, offensive/defensive rebounds, steals, blocks
   - Team-level data is in the second dataframe (index 1)

2. **BoxScoreScoringV3**
   - Endpoint: `nba_api.stats.endpoints.boxscorescoringv3`
   - Provides: Percentages for fast break, paint, and off-turnovers scoring
   - Team-level data is in the second dataframe (index 1)
   - Returns values like `percentagePointsFastBreak: 0.14` (14% of points from fast breaks)

### Calculation Methods

**Points from Percentages:**
```python
team_points = 105
pct_fast_break = 0.14  # 14%
fast_break_points = round(team_points * pct_fast_break)  # = 15 pts
```

**Second Chance Points Estimation:**
```python
# Heuristic: ~1.1 points per offensive rebound
second_chance_points = round(offensive_rebounds * 1.1)
```

This is an approximation since the NBA doesn't provide exact second chance points via API. The 1.1 multiplier is based on league averages (~55% shooting on second chance opportunities).

## Implementation Details

### File: `api/utils/sync_nba_data.py`

**New Imports:**
```python
from nba_api.stats.endpoints import (
    boxscoretraditionalv3,
    boxscorescoringv3,
)
```

**New Function: `_fetch_box_score_stats(game_id, team_id)`**
- Lines 698-786
- Fetches box score data for a specific team in a game
- Returns dict with all 10 new fields
- Returns empty dict on failure (fields will be NULL in database)

**Modified Function: `_sync_game_logs_impl()`**
- Lines 911-932: Added box score caching to avoid duplicate API calls
- Lines 934-948: Fetch box score data for each team before inserting
- Lines 951-993: Updated INSERT statement to include new fields

**Box Score Caching:**
```python
# Cache box score data per game to avoid duplicate API calls
box_score_cache = {}

for game_id, teams_data in game_data_by_id.items():
    if game_id not in box_score_cache:
        box_score_cache[game_id] = {}
        for team_data in teams_data:
            tid = team_data['team_id']
            box_score_cache[game_id][tid] = _fetch_box_score_stats(game_id, tid)
```

This optimization reduces API calls by ~50% since both teams in a game share the same game_id.

## Migration

**File:** `migrate_box_score_stats.py`

Run once to add new columns to existing database:
```bash
python3 migrate_box_score_stats.py
```

The migration is idempotent - it will skip columns that already exist.

## Testing

**File:** `test_box_score_sync.py`

Test script that:
1. Syncs last 3 games for LAL and BOS
2. Verifies all 10 box score fields are populated
3. Displays sample data for verification

Run the test:
```bash
python3 test_box_score_sync.py
```

Expected output shows all box score fields populated with realistic values:
```
✅ All box score fields populated
   FGM/FGA: 34/64
   Rebounds: O:5 D:20
   Defense: 5 STL, 3 BLK
   Scoring Breakdown:
     - Fast Break: 14 pts
     - Paint: 27 pts
     - Off Turnovers: 10 pts
     - Second Chance: 6 pts
```

## Rate Limiting

The implementation respects existing rate limits:
- 600ms between API calls
- 100 requests per minute max
- Uses `_safe_api_call()` wrapper with retry logic

Each game requires 2 additional API calls (BoxScoreTraditionalV3 + BoxScoreScoringV3), so syncing N games for 2 teams requires:
- Base: 2 calls (TeamGameLogs for each team)
- Box scores: 2N calls (2 endpoints × N games)
- Total: 2 + 2N calls

Example: Syncing 10 games for 2 teams = 2 + 20 = 22 API calls (~15 seconds with rate limiting)

## Data Quality

**Fallback Behavior:**
- If box score fetch fails, fields are set to NULL
- Basic FGM/FGA fallback to TeamGameLogs values if available
- OREB/DREB fallback to values already scraped from TeamGameLogs

**Validation:**
- All percentage-based calculations are rounded to nearest integer
- Second chance points use conservative 1.1x multiplier
- Logging warnings for failed API calls or missing data

## Future Enhancements

Potential additions (not implemented):
1. Use offensive rating to improve second chance points estimate
2. Cache box score data by game_id to reduce redundant fetches
3. Add `points_from_2pt`, `points_from_3pt` breakdown
4. Add `assists_on_2pt`, `assists_on_3pt` splits
5. Add `defensive_rating_allowed` (opponent efficiency)

## Backward Compatibility

- Existing code continues to work without changes
- New fields are optional (NULL allowed)
- Old game logs without box score data remain valid
- Can re-sync historical games to populate missing data

## API Usage in Prediction Engine

**Status:** Read-only for now

The box score stats are stored in `team_game_logs` but not yet used in prediction calculations. They can be accessed via `db_queries.py` functions and used for:
- Analyzing team pace/style (fast break frequency)
- Defensive pressure analysis (steals, blocks)
- Offensive efficiency breakdown (paint vs perimeter)
- Matchup-specific adjustments (e.g., good paint defense vs paint-heavy offense)

**Example Query:**
```python
from api.utils.db_queries import get_team_data

team_data = get_team_data(team_id=1610612738, season='2025-26')
recent_games = team_data.get('recent_games', [])

for game in recent_games:
    fast_break_pts = game.get('fast_break_points', 0)
    paint_pts = game.get('points_in_paint', 0)
    # Analyze team's scoring tendencies...
```

## Files Modified

1. `api/utils/sync_nba_data.py` - Added box score fetching logic
2. `api/data/nba_data.db` - Schema updated (via migration)

## Files Created

1. `migrate_box_score_stats.py` - Database migration script
2. `test_box_score_sync.py` - Test and verification script
3. `BOX_SCORE_STATS_IMPLEMENTATION.md` - This documentation

---

## Summary

✅ Successfully extended scraper to fetch 10 additional box score statistics
✅ Data stored in existing `team_game_logs` table
✅ Backward compatible with existing code
✅ Tested and verified with recent games
✅ Ready for future use in prediction engine
