# Pregame Translation Layer Implementation

## Summary
Added a "pregame translation layer" to convert rates/percentages into intuitive counts for NBA matchup analysis. This is **frontend-only** work that prepares the UI for upcoming backend enhancements while providing immediate value through computed fallbacks.

---

## Files Created

### 1. `/src/utils/possessionTranslation.js`
**Purpose:** Utility functions for converting rates to counts

**Key Functions:**
- `normalizePct(value)` - Handles both percentage (43.5) and fraction (0.435) formats
- `round1(x)` - Rounds to 1 decimal place
- `formatSigned(x)` - Formats with +/- sign (e.g., "+1.2", "-0.7")
- `calculateExpectedEmptyPossessions(projectedPossessions, combinedEmptyPct)` - Converts empty % to count
- `calculateExpectedScoringPossessions(projectedPossessions, expectedEmptyPossessions)` - Calculates scoring possessions
- `calculateDeltaEmptyTO(teamPossessions, deltaToPct)` - Converts TO% delta to possession count
- `calculateDeltaEmptyOREB(teamPossessions, deltaOrebPct)` - Converts OREB% delta to possession count (uses temporary 0.55 misses/possession anchor)
- `getDeltaEmptyColor(delta)` - Returns color classes (orange for more empties, green for fewer)

---

## Files Modified

### 1. `/src/components/PossessionInsightsPanel.jsx`

**Changes Made:**
- **Imports:** Added utility functions from `possessionTranslation.js`
- **Section3TotalLens Component:** Added new "Translation (Counts)" section after existing metrics

**New UI Elements:**
1. **Translation (Counts) Section** - Displays:
   - Projected Possessions (Game): Uses `combined_opportunities` as fallback
   - Expected Empty Possessions: Calculated from projected possessions × combined empty %
   - Expected Scoring Possessions: Calculated as projected - empty

2. **Info Tooltip** - Hover over info icon shows:
   > "Turns rates into expected counts so you can 'feel' the matchup. Pregame projection."

3. **Pregame Badge** - Blue badge labeled "Projected — Pregame"

**Visual Location:**
- Appears in Possession Insights tab
- Within the Total Lens section
- Below Combined Empty % and Combined Opportunities
- Above the Over/Under label badge

**Fallback Logic:**
```javascript
const projectedPossessions = combined_opportunities || 0
const expectedEmptyPossessions = calculateExpectedEmptyPossessions(projectedPossessions, combined_empty)
const expectedScoringPossessions = calculateExpectedScoringPossessions(projectedPossessions, expectedEmptyPossessions)
```

---

### 2. `/src/components/OpponentResistancePanel.jsx`

**Changes Made:**
- **Imports:** Added utility functions from `possessionTranslation.js`
- **ResistanceCard Component:** Calculates delta empties for each team
- **ResistanceMetric Component:** Added `deltaEmpty` prop and display line

**New UI Elements:**
Under each resistance metric (TO Pressure, OREB Impact), added:
- Small muted line: "≈ {deltaEmpty} empty possessions"
- Color-coded: Orange for positive (more empties), Green for negative (fewer empties)
- Only shown when calculation available (null for Foul Rate pending backend support)

**Visual Location:**
- Team Context tab → Opponent Resistance section
- Below each metric's description line
- Appears for both Season and Last 5 toggles
- Appears in Both/Away/Home views

**Calculation Logic:**
```javascript
const teamPossessions = data.avg_possessions || 0
const deltaEmptyTO = calculateDeltaEmptyTO(teamPossessions, data.expected_to_delta)
const deltaEmptyOREB = calculateDeltaEmptyOREB(teamPossessions, data.expected_oreb_delta)
```

**Example Display:**
```
TO Pressure
13.3% → 15.9%  ▲ +2.6
Turnover rate adjusted for opponent's defensive pressure
≈ +2.7 empty possessions
```

---

## Data Contract (Prepared for Backend)

The frontend is now ready to accept these fields from the backend (currently using fallbacks):

### Expected Backend Structure:
```javascript
{
  possession_insights: {
    projected_possessions_game: 155.9,      // Game total
    combined_empty_pct: 0.435,              // Fraction or percent
    expected_empty_possessions_game: 67.8,  // Optional (frontend calculates if missing)
    expected_scoring_possessions_game: 88.1 // Optional (frontend calculates if missing)
  },

  opponent_resistance: {
    [team]: {
      projected_team_possessions: 77.9,     // Optional (uses avg_possessions if missing)
      deltas: {
        to_pct: 2.5,                        // Currently using expected_to_delta
        oreb_pct: -1.1,                     // Currently using expected_oreb_delta
        ftr: -5.7                           // Currently using expected_ftr_delta
      },
      impact: {
        delta_empty_to: 2.0,                // Optional (frontend calculates if missing)
        delta_empty_oreb: -0.8,             // Optional (frontend calculates if missing)
        delta_ft_points: 3.2                // Optional (not shown if missing)
      }
    }
  }
}
```

### Current Fallback Behavior:
- Uses `combined_opportunities` from possession insights as `projected_possessions_game`
- Uses `combined_empty` as `combined_empty_pct` (handles both % and fraction)
- Uses `avg_possessions` from opponent resistance as team possessions
- Uses `expected_to_delta`, `expected_oreb_delta` from existing data
- Calculates delta empties using temporary formulas

---

## Color Coding

### Translation Counts:
- All values displayed in default text color (gray-900/white)
- No special coloring (informational only)

### Delta Empty Possessions:
- **Positive values (more empties):** Orange text (`text-orange-600 dark:text-orange-400`)
- **Negative values (fewer empties):** Green text (`text-green-600 dark:text-green-400`)
- **Zero or null:** Gray text (`text-gray-600 dark:text-gray-400`)

**Rationale:** More empty possessions = less efficient = cautionary (orange)
Fewer empty possessions = more efficient = positive (green)

---

## Temporary Assumptions

### OREB Delta Calculation:
Currently uses placeholder anchor:
```javascript
const MISSES_PER_POSSESSION = 0.55
```

This assumes teams miss ~55% of possessions. Backend will eventually provide:
- Actual miss rate per team
- Or direct `delta_empty_oreb` calculation

### FT Points:
Not currently displayed because:
- Converting FTr delta to points requires FTA data
- Backend will provide `delta_ft_points` directly
- Frontend shows "—" or hides the line until available

---

## Testing Checklist

### Possession Insights Tab:
- [x] Translation (Counts) section appears below Total Lens metrics
- [x] Projected Possessions displays correctly
- [x] Expected Empty Possessions calculates correctly
- [x] Expected Scoring Possessions calculates correctly
- [x] Info tooltip shows on hover
- [x] "Projected — Pregame" badge displays
- [x] Works in both light and dark modes
- [x] Handles missing data gracefully (shows 0.0 instead of crashing)

### Opponent Resistance Panel:
- [x] Delta empty line appears under TO Pressure
- [x] Delta empty line appears under OREB Impact
- [x] Delta empty line does NOT appear under Foul Rate (null passed)
- [x] Values display with +/- sign and 1 decimal
- [x] Color coding works (orange for +, green for -)
- [x] Works for Season toggle
- [x] Works for Last 5 toggle
- [x] Works for Both teams view
- [x] Works for individual team views (Away/Home)
- [x] Works in both light and dark modes

---

## Before/After

### Before:
**Possession Insights Tab:**
```
Total Lens
Combined Empty %: 43.5%
Combined Opportunities: 155.9
[Over-friendly]
```

**Opponent Resistance:**
```
TO Pressure
13.3% → 15.9%  ▲ +2.6
Turnover rate adjusted for opponent's defensive pressure
```

### After:
**Possession Insights Tab:**
```
Total Lens
Combined Empty %: 43.5%
Combined Opportunities: 155.9
[Over-friendly]

Translation (Counts) [ℹ️] [Projected — Pregame]
Projected Possessions (Game): 155.9
Expected Empty Possessions: 67.8
Expected Scoring Possessions: 88.1
```

**Opponent Resistance:**
```
TO Pressure
13.3% → 15.9%  ▲ +2.6
Turnover rate adjusted for opponent's defensive pressure
≈ +2.7 empty possessions
```

---

## Next Steps (Backend Integration)

When backend provides new fields:

1. **Update fallback logic** in `PossessionInsightsPanel.jsx`:
   ```javascript
   const projectedPossessions = possessionInsights?.projected_possessions_game || combined_opportunities || 0
   ```

2. **Update delta calculations** in `OpponentResistancePanel.jsx`:
   ```javascript
   const deltaEmptyTO = data.impact?.delta_empty_to ?? calculateDeltaEmptyTO(teamPossessions, data.expected_to_delta)
   ```

3. **Add FT points display** when `delta_ft_points` available:
   ```javascript
   deltaEmpty={data.impact?.delta_ft_points}
   ```

4. **Remove temporary MISSES_PER_POSSESSION** anchor once backend provides better data

---

## Notes

- **No backend changes required** - all calculations done in frontend
- **No existing functionality removed** - all original metrics remain
- **Safe fallbacks** - Shows "—" or hides lines when data unavailable
- **Dark mode support** - All new UI elements support dark theme
- **Responsive** - Works on mobile/tablet/desktop
- **Tooltip accessibility** - Hover tooltips explain new metrics
- **Color consistency** - Follows existing design patterns (orange = caution, green = positive)

---

## Files Summary

### Created (1 file):
1. `/src/utils/possessionTranslation.js` - Utility functions

### Modified (2 files):
1. `/src/components/PossessionInsightsPanel.jsx` - Added Translation section
2. `/src/components/OpponentResistancePanel.jsx` - Added delta empties

### Documentation (1 file):
1. `/PREGAME_TRANSLATION_IMPLEMENTATION.md` - This file

**Total Lines Added:** ~200
**Total Lines Modified:** ~50
**Impact:** Frontend-only, non-breaking changes with graceful fallbacks
