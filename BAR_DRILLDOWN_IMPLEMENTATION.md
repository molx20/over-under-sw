# Bar Drilldown Feature - Implementation Guide

## ✅ Completed Components

### Backend
1. **`api/utils/bar_drilldown.py`** - Shared drilldown utility functions
   - `get_drilldown_games()` - Main function that returns game list for any bar
   - `get_pace_tier()`, `get_defense_tier_from_rank()`, etc. - Classification functions
   - `get_opponent_def_rank()`, `get_opponent_threept_def_rank()`, `get_opponent_pressure_rank()` - Rank lookup functions

2. **`server.py` (line ~1570)** - API endpoint `/api/team/<int:team_id>/drilldown`
   - Validates query params (metric, dimension, context, bucket/tier, pace_type, season)
   - Returns `{success, count, bar_value, avg_pace, games}`
   - Tested successfully: NYK home games vs elite 3PT defense returned 2 games, 55.5 avg

### Frontend
3. **`src/components/BarDrilldownPopover.jsx`** - Reusable popover component
   - Props: `isOpen`, `onClose`, `teamId`, `metric`, `dimension`, `context`, `bucket`, `tier`, `paceType`, `season`, `barValue`, `anchorEl`
   - Features:
     - Scrollable game list (max-height: 384px)
     - Click row to navigate to `/game/:gameId`
     - Shows game details based on metric (scoring, 3PT, turnovers)
     - Displays opponent rank/tier if applicable
     - Footer validation showing if bar value matches computed value
     - Auto-positioning based on anchor element

4. **`src/components/ThreePointScoringVsDefenseChart.jsx`** - FULLY IMPLEMENTED
   - Added drilldown state management
   - Added "View games (N)" button to tooltips
   - Integrated `BarDrilldownPopover`
   - Working example for all other charts to follow

---

## 🔧 Pattern for Remaining Charts

You need to update **5 more chart components** following the exact same pattern:

1. **Scoring vs Defense Tiers** - `src/components/???` (find the file)
2. **Scoring vs Pace Buckets** - `src/components/ScoringVsPaceChart.jsx`
3. **3PT vs Pace Buckets** - `src/components/ThreePointScoringVsPaceChart.jsx`
4. **Turnovers vs Defense Pressure** - `src/components/TurnoverVsDefensePressureChart.jsx`
5. **Turnovers vs Pace Buckets** - `src/components/TurnoverVsPaceChart.jsx`

---

## 📋 Step-by-Step Implementation for Each Chart

### Step 1: Add Imports and State (Top of Component)

```jsx
import { useState } from 'react'
import BarDrilldownPopover from './BarDrilldownPopover'

function YourChartComponent({ teamData, compact = false }) {
  // Drilldown state
  const [drilldownOpen, setDrilldownOpen] = useState(false)
  const [drilldownParams, setDrilldownParams] = useState(null)
  const [drilldownAnchor, setDrilldownAnchor] = useState(null)

  // ... rest of component
```

### Step 2: Update Tooltip to Add "View games" Button

Find the HOME BAR tooltip section (usually around line 160-200):

```jsx
{/* Tooltip */}
{homeValue && (
  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block z-20">
    <div className="bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-md py-2 px-3 whitespace-nowrap shadow-xl">
      <div className="font-semibold text-blue-300">Home</div>
      <div className="text-lg font-bold">{homeValue.toFixed(1)} YOUR_METRIC</div>
      <div className="text-gray-300 dark:text-gray-400 text-xs">{homeGames} game{homeGames !== 1 ? 's' : ''}</div>
      {!hasHomeData && (
        <div className="text-yellow-400 text-xs mt-1">⚠ Need 3+ games</div>
      )}

      {/* ADD THIS BUTTON */}
      {homeGames >= 1 && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            const rect = e.currentTarget.closest('[class*="group"]').getBoundingClientRect()
            setDrilldownParams({
              teamId: teamData.team_id,
              metric: 'YOUR_METRIC',  // 'scoring', 'threept', or 'turnovers'
              dimension: 'YOUR_DIMENSION',  // See table below
              context: 'home',
              tier: tier,  // OR bucket: bucket (for pace charts)
              paceType: 'actual',  // OR 'projected' for pace bucket charts
              season: teamData.season || '2025-26',
              barValue: homeValue
            })
            setDrilldownAnchor({ x: rect.left + rect.width / 2, y: rect.bottom })
            setDrilldownOpen(true)
          }}
          className={`mt-2 w-full px-2 py-1 rounded text-xs font-medium transition-colors ${
            homeGames >= 3
              ? 'bg-blue-500 hover:bg-blue-600 text-white'
              : 'bg-gray-600 hover:bg-gray-500 text-gray-300'
          }`}
          disabled={homeGames < 1}
        >
          View games ({homeGames})
        </button>
      )}
    </div>
  </div>
)}
```

Repeat for AWAY BAR tooltip (change `context: 'away'` and button color to orange).

### Step 3: Add Popover at End of Component (Before Final `</div>`)

```jsx
      {/* Info note */}
      <div className="mt-3 sm:mt-4 text-[10px] sm:text-xs ...">
        Your existing info note
      </div>

      {/* ADD THIS POPOVER */}
      {drilldownParams && (
        <BarDrilldownPopover
          isOpen={drilldownOpen}
          onClose={() => setDrilldownOpen(false)}
          teamId={drilldownParams.teamId}
          metric={drilldownParams.metric}
          dimension={drilldownParams.dimension}
          context={drilldownParams.context}
          tier={drilldownParams?.tier}
          bucket={drilldownParams?.bucket}
          paceType={drilldownParams.paceType}
          season={drilldownParams.season}
          barValue={drilldownParams.barValue}
          anchorEl={drilldownAnchor}
        />
      )}
    </div>
  )
}
```

---

## 🎯 Dimension and Metric Mapping

| Chart Component | metric | dimension | tier/bucket param |
|-----------------|--------|-----------|-------------------|
| **Scoring vs Defense Tiers** | `'scoring'` | `'defense_tier'` | `tier: tier` ('elite', 'avg', 'bad') |
| **Scoring vs Pace Buckets** | `'scoring'` | `'pace_bucket'` | `bucket: bucket` ('slow', 'normal', 'fast') |
| **3PT vs Defense Tiers** | `'threept'` | `'threept_def_tier'` | `tier: tier` ('elite', 'avg', 'bad') |
| **3PT vs Pace Buckets** | `'threept'` | `'pace_bucket'` | `bucket: bucket` ('slow', 'normal', 'fast') |
| **Turnovers vs Pressure** | `'turnovers'` | `'pressure_tier'` | `tier: tier` ('elite', 'avg', 'low') |
| **Turnovers vs Pace Buckets** | `'turnovers'` | `'pace_bucket'` | `bucket: bucket` ('slow', 'normal', 'fast') |

### Pace Type Selection

- **Defense tier charts**: Always use `paceType: 'actual'`
- **Pace bucket charts**: Use `paceType: 'actual'` (or 'projected' if chart is based on projected pace)

---

## 🧪 Testing Checklist

### For Each Chart:

1. **Visual Test**
   - [ ] Hover over bar → tooltip appears
   - [ ] "View games (N)" button appears in tooltip
   - [ ] Button is blue/orange (matching bar color)
   - [ ] Button shows correct game count

2. **Interaction Test**
   - [ ] Click "View games" → popover opens
   - [ ] Popover shows exactly N games
   - [ ] Popover positioned near the bar
   - [ ] Click backdrop → popover closes
   - [ ] Click X button → popover closes

3. **Data Accuracy Test**
   - [ ] Count in popover header matches tooltip "N games"
   - [ ] Bar value in popover matches chart bar value (within 0.2 rounding)
   - [ ] Footer shows "✓ Values match" (green)
   - [ ] Games shown match the metric (e.g., 3PT chart shows 3PM/3PA/3P%)

4. **Navigation Test**
   - [ ] Click a game row → navigates to `/game/:gameId`
   - [ ] Game page loads correctly
   - [ ] Can navigate back and drilldown still works

5. **Edge Cases**
   - [ ] Bar with 0 games → no "View games" button
   - [ ] Bar with 1-2 games → button is gray, still works
   - [ ] Bar with 3+ games → button is colored (blue/orange)
   - [ ] Historical games (old dates) → drilldown returns games

---

## 🔍 Backend Query Verification

Test backend directly to verify game counts match:

```bash
# Example: Test NYK home games vs elite 3PT defense
python3 -c "
from api.utils.bar_drilldown import get_drilldown_games
result = get_drilldown_games(
    team_id=1610612752,  # NYK
    metric='threept',
    dimension='threept_def_tier',
    context='home',
    tier='elite',
    pace_type='actual',
    season='2025-26'
)
print(f'Count: {result[\"count\"]}')
print(f'Bar value: {result[\"bar_value\"]}')
"

# Should match what the chart shows for that bar
```

---

## 🚀 Deployment Notes

### Database Requirements
- ✅ `team_game_logs` table has all required fields (game_id, pace, fg3m, turnovers, etc.)
- ✅ `team_season_stats` has opponent rankings (def_rating, opp_fg3_pct, opp_turnovers)
- ⚠️ **MISSING**: `pace_projected` per game (currently computed on-demand)
  - **Workaround**: Use `pace_actual` for now in all charts
  - **Future improvement**: Store `pace_projected` when predictions are generated

### Frontend Performance
- ✅ Drilldown data fetched only when popover opens (lazy loading)
- ✅ No caching yet (add later if needed)
- ✅ Popover unmounts when closed (no memory leaks)

### Error Handling
- ✅ Backend validates all params, returns 400 for invalid requests
- ✅ Frontend shows error message if fetch fails
- ✅ Frontend shows "No games found" if count = 0

---

## 📦 Files Created/Modified

### New Files:
1. `api/utils/bar_drilldown.py` - Drilldown backend utilities
2. `src/components/BarDrilldownPopover.jsx` - Reusable popover component
3. `BAR_DRILLDOWN_IMPLEMENTATION.md` - This guide

### Modified Files:
1. `server.py` - Added `/api/team/<int:team_id>/drilldown` endpoint (line ~1570)
2. `src/components/ThreePointScoringVsDefenseChart.jsx` - ✅ Drilldown added
3. `src/components/ScoringSpitsChart.jsx` - ✅ Drilldown added (Scoring vs Defense Tiers)
4. `src/components/ScoringVsPaceChart.jsx` - ✅ Drilldown added
5. `src/components/ThreePointScoringVsPaceChart.jsx` - ✅ Drilldown added
6. `src/components/TurnoverVsDefensePressureChart.jsx` - ✅ Drilldown added
7. `src/components/TurnoverVsPaceChart.jsx` - ✅ Drilldown added

---

## 🎓 Example Implementation

See **`src/components/ThreePointScoringVsDefenseChart.jsx`** for the complete reference implementation. This file demonstrates:

- ✅ Correct state management
- ✅ Tooltip button integration
- ✅ Anchor positioning
- ✅ Popover integration
- ✅ Proper parameter passing

Copy this pattern exactly for the other 5 charts, only changing:
- `metric` value
- `dimension` value
- `tier` vs `bucket` parameter
- `paceType` (for pace bucket charts)

---

## ✨ User Experience Features

### Clean UI
- ✅ No permanent clutter - drilldown only appears on hover/click
- ✅ Popover positioned near clicked bar (not random location)
- ✅ Backdrop darkens screen, focuses attention on popover
- ✅ Smooth transitions and hover states

### Informative Display
- ✅ Shows game count, average value, and (if applicable) average pace
- ✅ Each game row shows: date, opponent, score, result, relevant metric
- ✅ Color-coded home (blue) vs away (orange)
- ✅ Validation footer confirms values match

### Developer-Friendly
- ✅ Console logs for debugging (can be removed later)
- ✅ Error messages displayed to user
- ✅ Backend validates all params before querying database
- ✅ Reusable component pattern - add to any chart in minutes

---

## 🔧 Future Enhancements (Optional)

1. **Client-side caching**: Cache drilldown results per team/dimension/bucket
2. **Pace projected storage**: Store projected pace per game for accuracy
3. **Export games**: Add button to export game list as CSV
4. **Filter games**: Add date range filter in popover
5. **Sort games**: Add sort by date/score/metric value
6. **Highlight current game**: If viewing a game, highlight it in drilldown list
7. **Keyboard navigation**: Arrow keys to navigate game list, Enter to open

---

## 🎯 Acceptance Criteria (Must Pass)

- [ ] All 6 charts have working drilldown
- [ ] Clicking "View games (N)" shows exactly N games
- [ ] Bar value matches computed average from returned games
- [ ] No UI overlap or layout shift
- [ ] Clicking game row navigates to game page
- [ ] Works for historical games (not just today)
- [ ] No changes to prediction math
- [ ] No console errors in production build

---

## 🐛 Common Issues & Solutions

### Issue: "View games" button doesn't appear
**Solution**: Check `homeGames >= 1` condition, verify `teamData.team_id` exists

### Issue: Popover opens in wrong location
**Solution**: Ensure `getBoundingClientRect()` is called on the bar element, not tooltip

### Issue: Game count doesn't match tooltip
**Solution**: Verify backend query filters match chart's grouping logic

### Issue: TypeError: Cannot read property 'team_id'
**Solution**: Add null check: `teamData?.team_id` and ensure `teamData` prop is passed

### Issue: Navigation doesn't work
**Solution**: Verify `useNavigate()` is imported from `react-router-dom`

---

## ✅ Final Deployment Steps

1. Update all 6 chart components following the pattern
2. Test each chart on dev server
3. Verify counts and values match
4. Test navigation to game pages
5. Build production bundle: `npm run build`
6. Deploy to Railway
7. Test on production with real data
8. Monitor for errors in Railway logs

---

**Status**: ✅ Complete (6/6 charts completed)
**Next**: Test all charts and deploy to Railway
