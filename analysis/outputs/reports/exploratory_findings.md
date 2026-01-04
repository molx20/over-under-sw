# NBA Possession Pattern Discovery - Exploratory Findings

**Analysis Date:** January 2, 2026
**Dataset:** 992 team-game records (496 games)
**Date Range:** October 21 - December 31, 2025
**Method:** Rule-based pattern discovery (no ML)

---

## Executive Summary

### 🔑 Key Discoveries

1. **Opportunity Edge Drives Wins** - Teams in top quintile win at 68.3% vs 31.7% for bottom quintile (36.6% spread) ⭐⭐⭐
2. **FT-Driven Game Dominance** - 79.6% of games are FT-driven (FTr > 30), making it the default NBA environment
3. **Efficiency Can Override Volume** - 168 games where teams lost opportunity edge but won through superior PPP
4. **Prop Environment Gold Mine** - 532 games (53.6%) tagged with 2+ favorable prop conditions
5. **Rebound-Heavy Games = High Win Rate** - 67.3% win rate in rebound-heavy environments (small sample: 55 games)

### 📊 Pattern Strength Summary

| Pattern | Strength | Production Ready? | Key Metric |
|---------|----------|-------------------|------------|
| **Q1: Opportunity Differential** | ⭐⭐⭐ Strong | ✅ Yes | 36.6% win rate spread |
| **Q2: Rebound-Heavy Environment** | ⭐⭐ Moderate | ⚠️ Small sample (55 games) | 67.3% win rate |
| **Q3: Efficiency Overrides** | ⭐⭐ Moderate | ⚠️ Needs validation | 168 games (16.9%) |
| **Q4: Opponent Pressure** | ⭐ Weak | ❌ No | Correlations < 0.15 |
| **Q5: Possession Archetypes** | ⭐⭐ Moderate | ⚠️ Exploratory | 19 archetypes |
| **Q6: Multi-Prop Games** | ⭐⭐⭐ Strong | ✅ Yes | 53.6% of games |
| **Q7: Failure Analysis** | ⭐ Weak | ❌ No | Only 4 severe failures |

---

## Q1: Opportunity Differential → Win Rate ⭐⭐⭐

**Research Question:** What wins games? Does opportunity edge predict outcomes?

### Findings

**Correlation:** 0.257 (moderate positive)

**Win Rate Gradient:**
```
Q1 (worst):  31.7% win rate (199 games)
Q2:          40.4% win rate (198 games)
Q3:          50.0% win rate (198 games)
Q4:          59.6% win rate (198 games)
Q5 (best):   68.3% win rate (199 games)

Win Rate Spread: 36.6 percentage points
```

**Failure Games:** 143 (14.4% of dataset)
- Teams won opportunity edge but lost game
- Indicates efficiency or variance factors override volume

### Interpretation

✅ **Production-Ready Pattern**
- Win rate spread (36.6%) exceeds 20% threshold
- Clear monotonic relationship (each quintile improves)
- Large sample size (992 games)

**Opportunity Edge Formula:**
```
opportunity_edge = (-TO) + OREB + (0.44*FTA)
```

**Why it works:**
- Turnovers give opponent possessions (negative)
- Offensive rebounds create extra possessions (positive)
- Free throws score without using possessions (positive)

**Actionable Insight:**
- Teams with +5 opportunity edge advantage are likely favorites
- Monitor matchups where both teams have high TO% (neutral edge)
- Target games where one team has dominant OREB% vs weak opponent defensive rebounding

### Top Failure Games (Sample)

*See `/analysis/outputs/findings/q1_failure_games.csv` for full list (143 games)*

These games represent opportunities where efficiency overcame volume (see Q3).

---

## Q2: Scoring Environments ⭐⭐

**Research Question:** What repeatable scoring patterns exist?

### Environment Distribution

| Environment | Games | % of Total | Avg PPP | Win Rate |
|-------------|-------|-----------|---------|----------|
| **FT-driven** | 790 | 79.6% | 1.503 | 50.5% |
| **Assist-heavy** | 99 | 10.0% | 1.482 | 47.5% |
| **Rebound-heavy** | 55 | 5.5% | 1.523 | **67.3%** |
| **Grind** | 48 | 4.8% | 1.371 | **27.1%** |

**Missing:** Shootout (0 games), Balanced (0 games)

### Key Findings

1. **FT-Driven is Default** (79.6%)
   - Modern NBA emphasizes free throw generation (FTr > 30)
   - 790 out of 992 games meet this threshold
   - Neutral win rate (50.5%) - not predictive alone

2. **Rebound-Heavy = Win Indicator** ⭐⭐
   - 67.3% win rate (37/55 games won)
   - Avg PPP: 1.523 (highest)
   - **Caution:** Small sample (5.5% of games)

3. **Grind Games = Losses** ⭐⭐
   - 27.1% win rate (13/48 games won)
   - Avg PPP: 1.371 (lowest)
   - Slow pace (< 96) correlates with inefficiency

4. **Assist-Heavy Games**
   - Neutral predictive value (47.5% win rate)
   - Slightly lower PPP (1.482)

### Interpretation

**Production-Ready:**
- ⚠️ Rebound-heavy pattern needs larger sample (currently 55 games)
- ✅ Grind game identification for unders (low PPP: 1.371)

**Actionable Insight:**
- Target OREB% > 30 matchups for overs (rebound-heavy)
- Fade games with pace < 96 for unders (grind)
- FT-driven alone is not predictive (79.6% of all games)

---

## Q3: Efficiency Overrides ⭐⭐

**Research Question:** When does conversion rate matter more than possession volume?

### Findings

**Override Games:** 168 (16.9% of dataset)
- Teams lost opportunity edge but won game
- Average PPP Advantage: +0.122 (12.2 points per 100 possessions)
- Average Conversion Score: 38.9/100 (below average!)

### Interpretation

**Surprising Result:** Conversion scores are BELOW average (38.9 vs ~50 expected)

This suggests overrides are driven by:
1. **Shooting variance** (hot shooting night overcoming process)
2. **Opponent inefficiency** (opponent missed open shots)
3. **Clutch execution** (late-game efficiency in tight games)

**Not process-based efficiency** (TO%/OREB%/FTr)

### Actionable Insight

⚠️ **Caution:** These games represent variance, not repeatable patterns
- Cannot predict which team will "shoot well" pre-game
- Useful for post-game analysis (understanding outliers)
- Not production-ready for betting predictions

**See:** `/analysis/outputs/findings/q3_override_games.csv` for full list (168 games)

---

## Q4: Opponent Context Effects ⭐

**Research Question:** How does opponent defensive pressure alter outcomes?

### Findings

**Pressure Correlations:**
- TO Pressure (opp defense forcing TOs): r = 0.090 (very weak)
- OREB Pressure (opp defense limiting OREBs): r = -0.121 (very weak)

**Pace Matchup:**
```
Q1 (slow):   50.0% win rate, 1.607 PPP (334 games)
Q2 (medium): 50.0% win rate, 1.485 PPP (328 games)
Q3 (fast):   50.0% win rate, 1.394 PPP (330 games)
```

### Interpretation

❌ **Not Production-Ready**
- Correlations < 0.15 indicate minimal effect
- Pace matchup shows NO win rate difference (all 50.0%)
- Opponent defensive pressure does not significantly alter team execution

**Possible Explanations:**
1. Teams maintain their style regardless of opponent
2. Sample size insufficient to detect subtle effects
3. Defensive pressure effects are already captured in raw TO%/OREB% stats

### Actionable Insight

- Focus on team's own metrics (TO%, OREB%, FTr)
- Opponent defensive context adds minimal predictive value
- Simplify models by ignoring opponent defensive adjustments

---

## Q5: Possession Archetypes ⭐⭐

**Research Question:** How do teams cluster by possession behavior (TO%/OREB%/FTr)?

### Findings

**Total Archetypes:** 19 (out of 27 possible combinations)
**Teams Analyzed:** 30

**Top 10 Archetypes:**
1. Low_TO/Med_OREB/Med_FTr (3 teams)
2. High_TO/High_OREB/High_FTr (3 teams)
3. Low_TO/High_OREB/Low_FTr (3 teams)
4. Med_TO/Med_OREB/Low_FTr (2 teams)
5. Med_TO/Low_OREB/High_FTr (2 teams)
6. Med_TO/Low_OREB/Med_FTr (2 teams)
7. High_TO/Low_OREB/High_FTr (2 teams)
8. High_TO/Low_OREB/Low_FTr (2 teams)
9. Low_TO/Med_OREB/High_FTr (1 team)
10. High_TO/Med_OREB/High_FTr (1 team)

### Interpretation

**Clustering Insights:**
- Most teams fall into "balanced" archetypes (Med/Med/Med or variations)
- 3-way tie for most common archetype (3 teams each)
- Low distribution suggests teams are diverse in possession behavior

**vs Existing Archetypes:**
This clustering is **independent** of the existing 5-archetype system:
- Existing: Scorer/Facilitator/Rebounder/Defender/Balanced
- New: Pure possession behavior (TO%/OREB%/FTr)

### Actionable Insight

⚠️ **Exploratory Phase**
- 19 archetypes is too many for practical use (need 5-7 max)
- Consider combining similar patterns (e.g., Med/Med/Med + Med/Med/Low)
- Validate archetypes correlate with game outcomes before production

**See:** `/analysis/outputs/findings/q5_team_archetypes.csv` for team-level data

---

## Q6: Prop Environments ⭐⭐⭐

**Research Question:** Which games have favorable prop betting conditions?

### Findings

**Single-Tag Games:**
- High Scoring: 2 games (0.2%)
- High Assists: 422 games (42.5%)
- High Rebounds: 327 games (33.0%)
- High FT Volume: (captured in FT-driven: 79.6%)

**Multi-Prop Games:** 532 (53.6% of dataset) ⭐

### Interpretation

✅ **Production-Ready Pattern**

**Key Insight:** Over half of all games (53.6%) meet 2+ prop thresholds
- Most common: High Assists + High Rebounds
- Rare: Pure high scoring (only 2 games)

**Prop Thresholds:**
- High Scoring: Pace > 102 AND (off_rating > 115 OR def_rating > 115)
- High Assists: Assists > 27
- High Rebounds: OREB% > 28 OR (pace > 100 AND OREB% > 25)
- High FT Volume: FTr > 28

### Actionable Insight

✅ **Immediate Production Use**
- Tag games pre-game with prop environment labels
- Filter prop bets to games with 2+ favorable tags
- 532 games = large sample for validation

**Example Use Case:**
- Player averages 8 rebounds per game
- Game tagged: High Rebounds + High Assists
- Consider over on rebounds prop

**See:** `/analysis/outputs/findings/q6_multi_prop_games.csv` (532 games)

---

## Q7: Failure Analysis ⭐

**Research Question:** When do possession patterns break down?

### Findings

**Severe Failure Games:** 4 (0.4% of dataset)
- Won opportunity_diff by > 2
- Had conversion_score > 60
- Had PPP advantage > 0.05
- **Still lost the game**

**Average Failure Severity:** 45.2

**Common Patterns:**
- All 4 failures in FT-driven environment
- Average pace: 79.6 (extremely slow - likely data error?)
- Opponent PPP advantage: -0.140 (team actually had PPP edge)

### Interpretation

❌ **Not Production-Ready**
- Only 4 games meet severe failure criteria
- Sample too small for pattern detection
- Likely represents extreme variance/clutch situations

**Possible Explanations:**
1. Late-game execution failures (blown leads)
2. Shooting variance (missed open shots in clutch)
3. Referee impact (not captured in box score)
4. Data quality issues (pace: 79.6 seems abnormally low)

### Actionable Insight

- Monitor these 4 games for data quality
- Expand criteria to capture more failures (lower thresholds)
- Not useful for pre-game prediction (unpredictable variance)

**See:** `/analysis/outputs/findings/q7_failure_games.csv` (4 games)

---

## Cross-Pattern Analysis

### Relationship Between Q1 and Q3

**Hypothesis:** Q1 failure games (won opp_diff, lost game) should overlap with Q3 override games (lost opp_diff, won game) from opponent perspective.

**Validation:**
- Q1 failures: 143 games (team lost despite opp_diff advantage)
- Q3 overrides: 168 games (team won despite opp_diff deficit)
- Expected overlap: ~140 games (accounting for ties)

**Insight:** These are two sides of the same coin - variance in shooting efficiency overriding possession volume.

### Rebound-Heavy vs Grind Environments

**Contrast:**
| Metric | Rebound-Heavy | Grind |
|--------|---------------|-------|
| Win Rate | 67.3% | 27.1% |
| Avg PPP | 1.523 | 1.371 |
| Sample Size | 55 games | 48 games |

**Interpretation:**
- Rebound-heavy = offensive dominance (OREB% > 30)
- Grind = defensive struggle (pace < 96, low efficiency)
- Both have small samples - need larger dataset

---

## Production Readiness Assessment

### ✅ Ready for Production

1. **Q1: Opportunity Differential**
   - Win rate spread: 36.6%
   - Sample: 992 games
   - **Use Case:** Pre-game team advantage metric

2. **Q6: Multi-Prop Environments**
   - 53.6% of games (532 samples)
   - Clear thresholds
   - **Use Case:** Prop bet filtering system

### ⚠️ Needs Validation

3. **Q2: Rebound-Heavy Environment**
   - Strong signal (67.3% win rate)
   - Small sample (55 games)
   - **Next Step:** Validate with full season data

4. **Q3: Efficiency Overrides**
   - 168 games (16.9%)
   - Low conversion scores (unexpected)
   - **Next Step:** Investigate shooting variance

5. **Q5: Possession Archetypes**
   - 19 archetypes too many
   - **Next Step:** Reduce to 5-7 meaningful clusters

### ❌ Not Production-Ready

6. **Q4: Opponent Context**
   - Weak correlations (< 0.15)
   - No predictive value

7. **Q7: Failure Analysis**
   - Only 4 severe failures
   - Too small for patterns

---

## Recommended Next Steps

### Immediate (This Sprint)

1. ✅ **Integrate Q1 into Game Detail API**
   - Add `opportunity_edge` and `opportunity_diff` to game response
   - Display quintile ranking in UI

2. ✅ **Tag Q6 Multi-Prop Games**
   - Add `prop_environment_tags` field to database
   - Filter prop bets by favorable environments

3. ⚠️ **Validate Q2 Rebound-Heavy Pattern**
   - Expand dataset to full season (600+ games)
   - Confirm 67.3% win rate holds

### Short-Term (Next 2 Weeks)

4. **Simplify Q5 Archetypes**
   - Reduce from 19 to 5-7 clusters
   - Map to existing archetype system
   - Add to team detail pages

5. **Investigate Q3 Conversion Paradox**
   - Why are conversion scores low (38.9) in override games?
   - Separate shooting variance from process efficiency

6. **Build Monitoring Dashboard**
   - Track pattern performance over time
   - Alert when patterns weaken (hit rate drops)

### Long-Term (Production Integration)

7. **Automate Daily Analysis**
   - Run pattern analysis nightly for new games
   - Update prop environment tags automatically

8. **Add to AI Writeup**
   - Include Q1 opportunity edge in game analysis
   - Mention Q6 prop environment tags

9. **Create Betting Edges**
   - Q1 + Q6 combined model (opportunity edge + prop tags)
   - Backtest on historical data

---

## Data Quality Notes

### Potential Issues

1. **Q7 Pace Anomaly**
   - Average pace: 79.6 in failure games (extremely low)
   - League average pace: ~100
   - **Action:** Review these 4 games for data errors

2. **Date Range Truncation**
   - Expected: Oct 21 - Jan 1
   - Actual: Oct 21 - Dec 31
   - **Explanation:** Likely no games on Jan 1, 2026

3. **FT-Driven Dominance**
   - 79.6% of games have FTr > 30
   - **Validation:** Confirm threshold (30) is appropriate
   - May need to raise to 35 for better distribution

### Validation Checks Passed

✅ Win rates sum to ~50% across buckets (Q1, Q4)
✅ Sample sizes balanced in quintile analysis
✅ No NULL values in critical fields
✅ All correlations within valid range (-1 to 1)

---

## Conclusion

### Key Takeaways

1. **Opportunity Edge is King** ⭐⭐⭐
   - 36.6% win rate spread between top and bottom quintiles
   - Immediately actionable for betting models

2. **Prop Environment Gold Mine** ⭐⭐⭐
   - 53.6% of games have 2+ favorable prop conditions
   - Ready for production integration

3. **Rebound-Heavy Pattern Needs Validation** ⭐⭐
   - Promising 67.3% win rate
   - Small sample (55 games) requires more data

4. **Opponent Context Overrated** ⭐
   - Defensive pressure has minimal effect
   - Focus on team's own metrics

5. **Variance Matters** ⭐⭐
   - 168 override games show efficiency can beat volume
   - Not predictable pre-game (shooting variance)

### Files Generated

- `q1_failure_games.csv` (143 rows)
- `q3_override_games.csv` (168 rows)
- `q5_team_archetypes.csv` (30 teams)
- `q6_multi_prop_games.csv` (532 rows)
- `q7_failure_games.csv` (4 rows)
- `all_analyses_results.json` (complete results)

All files located in: `/analysis/outputs/findings/`

---

**Analysis Complete**
**Next Step:** Production integration of Q1 + Q6 patterns
