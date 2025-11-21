# Team Statistics Rankings Feature

## Overview

This feature adds **league rankings** to the "Team Statistics Comparison" table on the game details page. Each team's stats now show their rank compared to all other teams in the league.

## How It Works

### 1. Backend: Ranking Calculation (`api/utils/team_rankings.py`)

The ranking module calculates league standings for 9 key statistics:

**Ranking Rules:**
- **Rank 1 = Best**
- **Higher is better:** PPG, FG%, 3P%, FT%, OFF RTG, NET RTG, PACE
- **Lower is better:** OPP PPG (defense), DEF RTG (defense)

**Example:**
- Team with highest PPG → Rank 1
- Team with lowest DEF RTG (best defense) → Rank 1

**Caching Strategy:**
- Rankings stored in SQLite (`api/data/team_rankings.db`)
- Auto-refreshes every 6 hours
- First request after refresh triggers NBA API fetch for all 30 teams
- Subsequent requests use cached data (fast!)

**Key Functions:**
```python
# Main entry point - gets stats with rankings
get_team_stats_with_ranks(team_id, season='2025-26')

# Returns:
{
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
```

### 2. Backend: API Endpoint

**Endpoint:** `GET /api/team-stats-with-ranks`

**Query Parameters:**
- `team_id` (required): NBA team ID (e.g., 1610612747 for LAL)
- `season` (optional): Season string, defaults to '2025-26'

**Example Request:**
```bash
GET /api/team-stats-with-ranks?team_id=1610612746&season=2025-26
```

**Example Response (LAC @ ORL matchup):**

**For LAC (Team ID: 1610612746):**
```json
{
  "success": true,
  "team_id": 1610612746,
  "team_abbreviation": "LAC",
  "season": "2025-26",
  "stats": {
    "ppg": {"value": 111.7, "rank": 18},
    "opp_ppg": {"value": 116.3, "rank": 25},
    "fg_pct": {"value": 47.3, "rank": 12},
    "three_pct": {"value": 35.9, "rank": 9},
    "ft_pct": {"value": 83.3, "rank": 4},
    "off_rtg": {"value": 113.9, "rank": 15},
    "def_rtg": {"value": 118.5, "rank": 27},
    "net_rtg": {"value": -4.6, "rank": 24},
    "pace": {"value": 96.7, "rank": 20}
  }
}
```

**For ORL (Team ID: 1610612753):**
```json
{
  "success": true,
  "team_id": 1610612753,
  "team_abbreviation": "ORL",
  "season": "2025-26",
  "stats": {
    "ppg": {"value": 115.9, "rank": 8},
    "opp_ppg": {"value": 113.9, "rank": 1},
    "fg_pct": {"value": 47.1, "rank": 15},
    "three_pct": {"value": 33.3, "rank": 25},
    "ft_pct": {"value": 80.0, "rank": 18},
    "off_rtg": {"value": 114.3, "rank": 12},
    "def_rtg": {"value": 112.7, "rank": 1},
    "net_rtg": {"value": 1.5, "rank": 10},
    "pace": {"value": 100.5, "rank": 8}
  }
}
```

**Interpretation:**
- ORL has the #1 defense (lowest OPP PPG and DEF RTG)
- LAC has poor defense (#27 DEF RTG, #25 OPP PPG)
- LAC has better free throw shooting (#4 vs #18)

### 3. Frontend: Updated Components

**StatsTable Component (`src/components/StatsTable.jsx`):**

The component now:
1. Receives `homeTeamId` and `awayTeamId` props
2. Fetches rankings using `useTeamStatsWithRanks()` React Query hook
3. Displays ranks with ordinal suffixes (1st, 2nd, 3rd, etc.)

**Changes:**
```jsx
// OLD - No rankings
<td className="px-6 py-4">
  111.7
</td>

// NEW - With rankings
<td className="px-6 py-4">
  111.7 <span className="text-xs text-gray-500">18th</span>
</td>
```

**Ordinal Formatting:**
- 1 → "1st"
- 2 → "2nd"
- 3 → "3rd"
- 4 → "4th"
- 18 → "18th"
- 21 → "21st"
- 22 → "22nd"
- 23 → "23rd"

### 4. Visual Example

**Before (no rankings):**
```
LAC         STAT        ORL
4-10        Record      8-7
111.7       PPG         115.9
116.3       OPP PPG     113.9
47.3%       FG%         47.1%
```

**After (with rankings):**
```
LAC              STAT           ORL
4-10             Record         8-7
111.7 18th       PPG            115.9 8th
116.3 25th       OPP PPG        113.9 1st ⭐
47.3% 12th       FG%            47.1% 15th
35.9% 9th        3P%            33.3% 25th
83.3% 4th ⭐     FT%            80.0% 18th
113.9 15th       OFF RTG        114.3 12th
118.5 27th 📉    DEF RTG        112.7 1st ⭐
-4.6 24th        NET RTG        1.5 10th
96.7 20th        Pace           100.5 8th
```

**Key Insights from Rankings:**
- 🔴 LAC has the 27th worst defense (#27 DEF RTG, #25 OPP PPG) - major weakness!
- 🟢 ORL has the #1 defense in the league - elite!
- 🟢 LAC excels at free throws (#4 FT%, #9 3P%)
- 🔴 ORL struggles from three (#25 3P%)

## Performance

**Backend:**
- First request: ~15-30 seconds (fetches all 30 teams from NBA API)
- Cached requests: <100ms (SQLite lookup)
- Cache refresh: Every 6 hours automatically

**Frontend:**
- React Query caches rankings for 6 hours
- No loading state needed (instant from cache after first load)
- Parallel requests for both teams (efficient)

## Usage

### For Developers

**To manually refresh rankings:**
```python
from api.utils import team_rankings

# Force refresh all rankings
rankings = team_rankings.calculate_rankings_from_api('2025-26')
team_rankings.save_rankings_to_cache(rankings)
```

**To clear cache:**
```bash
rm api/data/team_rankings.db
# Will auto-recreate on next request
```

### For Users

Just navigate to any game detail page:
1. Click on a game from the dashboard
2. Scroll to "Team Statistics Comparison"
3. See rankings automatically displayed next to each stat

## Code Structure

```
api/utils/team_rankings.py    # Ranking calculation & caching
server.py                      # API endpoint
src/utils/api.js              # Frontend API client
src/components/StatsTable.jsx # UI component
src/pages/GamePage.jsx        # Parent page (passes team IDs)
```

## Error Handling

**If rankings fail to load:**
- Component gracefully shows stats without rankings
- No error thrown to user
- Logs error to console for debugging

**If NBA API is down:**
- Uses last cached rankings (up to 6 hours old)
- Better to show slightly stale data than no data

## Future Enhancements

Potential improvements:
- Color-code ranks (green for top 10, yellow for 11-20, red for 21-30)
- Add tooltips explaining what "rank 1" means for each stat
- Show rank change over time (↑↓ indicators)
- Add percentile instead of rank (e.g., "Top 25%")
- Filter rankings by conference (Eastern vs Western)

## Testing

**Test the feature:**
```bash
# Start server
python3 server.py

# Test API endpoint
curl "http://localhost:8080/api/team-stats-with-ranks?team_id=1610612747&season=2025-26"

# Visit frontend
# Navigate to http://localhost:5173
# Click any game → should see rankings in stats table
```

**Expected behavior:**
1. First load: May take 15-30 seconds to calculate all rankings
2. Subsequent loads: Instant (from cache)
3. Rankings appear as small gray text next to stat values
4. Format: "18th", "1st", "3rd" with ordinal suffixes
