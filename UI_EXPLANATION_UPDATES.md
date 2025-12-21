# UI Explanation Updates - Tuned Model

## Summary

Updated all user-facing explanation text to accurately reflect the newly tuned, conservative prediction model.

---

## Changes Made

### File: `src/utils/explanationText.js`

#### 1. Game Speed Description (Updated)

**Before:**
```javascript
gameSpeed: {
  description: 'Fast games have more trips up and down the court, which means more chances to score. Slow games have fewer possessions, so fewer total points.',
  fast: 'This will be a fast-paced game with lots of back-and-forth action.',
  slow: 'This will be a slower game with teams taking their time on offense.',
  normal: 'This game will move at a normal NBA speed.'
}
```

**After:**
```javascript
gameSpeed: {
  description: 'We use real possessions to estimate how fast this game will be, but we keep that impact small. Fast games get a tiny bump, slow games get a tiny drop.',
  fast: 'This will be a fast-paced game, but we only add a small boost for that.',
  slow: 'This will be a slower game, but we only subtract a little for that.',
  normal: 'This game will move at a normal NBA speed - no adjustment needed.'
}
```

**Rationale:** The new pace formula (0.92 + 0.08 * multiplier) has much less impact than before (was 0.85 + 0.15 * multiplier). The language now emphasizes that we "keep that impact small" and only add "a tiny bump" or "tiny drop."

---

#### 2. Home Edge & Road Trouble Description (Updated)

**Before:**
```javascript
homeEdge: {
  description: 'Home teams usually play better because of their fans and familiar court. Road teams often struggle when playing away from home.'
}
```

**After:**
```javascript
homeEdge: {
  description: 'If a team scores much better at home (or struggles much worse on the road), we add a tiny bonus. Most games get zero adjustment here - we\'re being very conservative.'
}
```

**Rationale:** The new home/road system only triggers in 2 of 9 patterns (both conditions must be extreme). Max adjustment is ±2 instead of ±4. The language now emphasizes that "most games get zero" and we're "very conservative."

---

#### 3. Little Matchup Bonuses Description (Updated)

**Before:**
```javascript
matchupBonuses: {
  description: 'Sometimes certain team styles clash in ways that create extra points or take points away. These are small tweaks based on how these teams match up.'
}
```

**After:**
```javascript
matchupBonuses: {
  description: 'If a team takes a lot of shots and grabs offensive rebounds, we give them a small scoring bump (usually +1 to +4 points). Lots of free throws usually add some extra points too, so we bump the score a bit in whistle-heavy games.'
}
```

**Rationale:** Now explicitly states the range (+1 to +4 points) instead of vague "small tweaks." Mentions the specific factors: shot volume, offensive rebounds, and free throws. These are the tuned volume-based adjustments.

---

#### 4. Pace Buckets Description (Updated)

**Before:**
```javascript
paceBuckets: {
  description: 'Game speed matters! Fast games mean more possessions and more shots for everyone. Slow games mean fewer possessions and fewer points. Some teams score way more in fast games, while others do better when it\'s slow.'
}
```

**After:**
```javascript
paceBuckets: {
  description: 'Game speed matters, but we keep the impact small. Fast games mean a few more possessions and shots. Slow games mean a bit fewer. We calculate real possessions (not just estimates) but only let it change the total by a tiny amount to avoid over-predicting.'
}
```

**Rationale:** Removed enthusiastic language ("matters!") and toned down impact description ("a few more" instead of "more"). Added explicit note about avoiding over-prediction and keeping impact small.

---

#### 5. Turnovers Removed Explanation (NEW)

**Added:**
```javascript
turnoversRemoved: {
  title: 'About Turnovers in the Model',
  description: 'Turnovers are already counted in our possessions formula (more turnovers = more possessions for the other team). We don\'t add extra bonuses for turnovers anymore because that would be counting them twice.'
}
```

**Rationale:** Explains why the turnover pace bonus was removed (double-counting issue). This can be used in Advanced Splits or as tooltip text if users ask why turnovers don't have a separate bonus anymore.

---

## Components Using Updated Text

### 1. HowWeBuiltThisTotalCard.jsx
- **Location:** Prediction tab
- **Uses:** All explanation text from `EXPLANATION_TEXT`
- **Auto-updated:** Yes (imports from explanationText.js)
- **Sections affected:**
  - Game Speed (Section 2)
  - Home Edge & Road Trouble (Section 4)
  - Little Matchup Bonuses (Section 7)

### 2. AdvancedSplitsPanel.jsx
- **Location:** Advanced Splits tab
- **Uses:** `paceBuckets` description
- **Auto-updated:** Yes (imports from explanationText.js)
- **Sections affected:**
  - Context toggle explanation (Pace Buckets)

### 3. PredictionExplainerCard.jsx (if exists)
- Would auto-update if it imports from explanationText.js

---

## Language Changes Summary

### Old Tone: Aggressive, Enthusiastic
- "Fast games mean MORE possessions!"
- "Home teams USUALLY play better"
- "Teams score WAY MORE in fast games"

### New Tone: Conservative, Measured
- "Fast games get a tiny bump"
- "MOST games get zero adjustment"
- "We keep the impact small"
- "Usually +1 to +4 points" (specific ranges)

---

## Alignment with Backend Tuning

| Component | Old Backend | New Backend | UI Language |
|-----------|-------------|-------------|-------------|
| Pace | ±15% | ±8% | "tiny bump" / "tiny drop" |
| Home/Road | ±4/±2 (6 of 9) | ±2/0 (2 of 9) | "zero adjustment" / "very conservative" |
| Shot volume | +7 max | +4 max | "+1 to +4 points" |
| ORB | +5 max | +2 max | (implied in "small scoring bump") |
| FT | +6 max | +3 max | "whistle-heavy games" |
| Turnover | +6 max | 0 | "don't add extra bonuses" |

---

## User Experience Impact

**Before:**
- Users saw aggressive language suggesting big swings
- No indication of conservatism or small adjustments
- Unclear why some bonuses were larger than others

**After:**
- Users understand we're being conservative
- Clear ranges (+1 to +4, "tiny", "small")
- Explanation of why turnovers don't get separate bonus
- Emphasis on avoiding over-prediction

---

## Testing Recommendations

1. **Check Prediction Tab:** Verify "How We Built This Total" card shows updated descriptions
2. **Check Advanced Splits:** Verify "About Game Speed" uses updated language
3. **Check tooltips:** If any tooltips reference these descriptions, verify they update
4. **User comprehension:** The new language should feel less "salesy" and more analytical

---

## Accessibility Notes

**Reading Level:** Still 5th grade (Flesch-Kincaid)
- Simple words: "tiny", "small", "bump"
- Short sentences
- No jargon except explained terms ("possessions")

**Tone:** Professional but approachable
- Honest about conservatism ("we're being very conservative")
- Transparent about methodology ("real possessions, not just estimates")
- Clear about limitations ("most games get zero")

---

## Future Enhancements

If predictions still run high after these changes, consider:

1. **Add explicit ranges to more sections:**
   - "Home edge: 0 to +2 points (rare)"
   - "Defense impact: usually -3 to -7 points"

2. **Add "confidence" indicators:**
   - "High confidence" for baselines
   - "Low confidence" for volume adjustments

3. **Show comparison to line:**
   - "Our prediction vs Vegas line: +7.2 points"
   - Color code: green if close, yellow if 5-10 over, red if >10 over

4. **Add historical accuracy:**
   - "This model is typically within ±5 points of actual totals"
   - Would require backend tracking

---

## Summary

✅ All explanation text updated to reflect tuned model
✅ Language emphasizes conservatism and small impacts
✅ Specific ranges provided (+1 to +4 instead of vague "small")
✅ Removed double-counting explanation added
✅ No component structure changes (text-only updates)
✅ Auto-updates via import (no hard-coded strings to chase down)

The UI now accurately represents the conservative, tuned prediction model without overstating the impact of any single adjustment.
