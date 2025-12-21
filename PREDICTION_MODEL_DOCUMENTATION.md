# NBA Over/Under Prediction Model - Complete Documentation

## Model Architecture Overview

**Current Version:** 4.6 (Smart Baseline + Advanced Pace + **Pace Volatility** + **Enhanced Defense** + Defense Quality + **Opponent Matchup Stats** + Dynamic HCA + Road Penalty + Dynamic 3PT Shootout + **Scoring Compression**)

**Pipeline Order:**
1. Smart Baseline (season + recent form blended)
2. **Advanced Pace Calculation** - includes turnover-driven pace impact
3. **Pace Volatility & Contextual Dampening** - reduces over-reliance on volatile pace
4. Defense Adjustment (Dynamic)
5. **Enhanced Defensive Adjustments** - MORE AGGRESSIVE DRTG multipliers
6. Matchup Adjustments
7. **Opponent Matchup Adjustments (NEW in v4.6!)** - team offense vs opponent defense analysis
8. **Defense Quality Adjustment** - supplementary rank-based adjustment
9. Home Court Advantage (Dynamic)
10. **Road Penalty** - non-linear penalty for away teams
11. Dynamic 3PT Shootout Adjustment
12. Fatigue/Rest Adjustment
13. **Scoring Compression & Bias Correction** - final anti-inflation safeguard

Each factor applies adjustments sequentially, building on the previous step.

---

## Smart Baseline (NEW in v4.0)

**Purpose:** Eliminate double-counting of recent form by creating a single intelligent baseline that already accounts for trends.

### Formula:
```python
# Calculate recent metrics
recent_ppg = average of last 5 games
recent_ortg_change = recent_ortg - season_ortg

# Determine trend strength
ppg_change = abs(recent_ppg - season_ppg)
abs_ortg_change = abs(recent_ortg_change)

# Adaptive weighting based on trend magnitude
if ppg_change > 10 OR abs_ortg_change > 8:
    # Extreme trend: offense clearly playing very differently
    baseline = season_ppg × 0.60 + recent_ppg × 0.40
elif ppg_change > 3 OR abs_ortg_change > 3:
    # Normal trend: noticeable shift in performance
    baseline = season_ppg × 0.70 + recent_ppg × 0.30
else:
    # Minimal trend: team playing like season average
    baseline = season_ppg × 0.80 + recent_ppg × 0.20
```

### Example:
```
BOS: Season 115.3 PPG, Recent 122.0 PPG, ORTG Δ+0.0
PPG change: |122.0 - 115.3| = 6.7 > 3 → normal trend
Baseline: 115.3 × 0.70 + 122.0 × 0.30 = 117.3 PPG

NYK: Season 120.2 PPG, Recent 119.8 PPG, ORTG Δ+0.0
PPG change: |119.8 - 120.2| = 0.4 < 3 → minimal trend
Baseline: 120.2 × 0.80 + 119.8 × 0.20 = 120.1 PPG
```

**Starting Point:**
```
home_projected = home_smart_baseline  (e.g., 117.3)
away_projected = away_smart_baseline  (e.g., 120.1)
```

---

## STEP 1: ADVANCED PACE CALCULATION (NEW in v4.3!)

**Purpose:** Replace simple season pace average with sophisticated, context-aware pace projection.

### Key Innovation: Multi-Factor Pace Projection

The model now uses an advanced pace calculation that goes beyond simple averaging:
- Blends season pace (60%) with recent pace (40%) for each team
- Applies pace mismatch penalty when slow teams meet fast teams
- Boosts pace for high-turnover games (transition basketball)
- Reduces pace for free-throw-heavy games (clock stoppages)
- Reduces pace for elite defense games (defensive grind)
- Clamps result to realistic NBA range (92-108)

### Old System vs New System

**Old (Simple Average):**
```python
game_pace = (team1_season_pace + team2_season_pace) / 2
```
❌ Ignored recent trends
❌ Missed high-turnover games
❌ Missed FT-heavy games
❌ Didn't account for pace mismatches

**New (Advanced Multi-Factor):**
```python
# See full formula below
```
✅ Captures recent pace trends
✅ Identifies high-turnover games
✅ Identifies FT-heavy games
✅ Accounts for pace mismatches
✅ Accounts for elite defenses

### Step-by-Step Formula:

**1. Adjusted Pace (Season + Recent Blend)**
```python
Team1_Adjusted_Pace = Team1_Season_Pace × 0.60 + Team1_Last5_Pace × 0.40
Team2_Adjusted_Pace = Team2_Season_Pace × 0.60 + Team2_Last5_Pace × 0.40

# Rationale: 60% season (stable), 40% recent (current form)
```

**2. Base Pace (Average of Both Teams)**
```python
Base_Pace = (Team1_Adjusted_Pace + Team2_Adjusted_Pace) / 2

# Starting point for all adjustments
```

**3. Pace Mismatch Penalty (Slow Team Drags Game Down)**
```python
Pace_Difference = |Team1_Adjusted_Pace - Team2_Adjusted_Pace|

IF Pace_Difference > 8:
    Pace_Mismatch_Penalty = -2.0  # Large mismatch
ELSE IF Pace_Difference > 5:
    Pace_Mismatch_Penalty = -1.0  # Moderate mismatch
ELSE:
    Pace_Mismatch_Penalty = 0     # Similar pace

# Rationale: Slow teams drag games down by walking ball up court
# Example: Warriors (108) vs Grizzlies (95) = slower than average
```

**4. Turnover-Driven Pace Impact (More Turnovers = Faster)**
```python
Projected_Turnovers = (Team1_Season_Turnovers + Team2_Season_Turnovers) / 2

IF Projected_Turnovers > 15:
    Turnover_Pace_Impact = (Projected_Turnovers - 15) × 0.3
ELSE:
    Turnover_Pace_Impact = 0

# Rationale: Turnovers create fast breaks and transition opportunities
# Example: 18 turnovers → (18 - 15) × 0.3 = +0.9 pace
```

**5. Free Throw Rate Penalty (More FTs = Slower)**
```python
Combined_FT_Rate = (Team1_FT_Rate + Team2_FT_Rate) / 2

IF Combined_FT_Rate > 0.25:
    FT_Pace_Penalty = (Combined_FT_Rate - 0.25) × 10
ELSE:
    FT_Pace_Penalty = 0

# Rationale: Free throws stop clock and prevent transition
# Example: FT rate 0.30 → (0.30 - 0.25) × 10 = 0.5 pace penalty
```

**6. Elite Defense Penalty (Defensive Grind)**
```python
IF Team1_Is_Elite_Defense OR Team2_Is_Elite_Defense:
    Defense_Pace_Penalty = -1.5
ELSE:
    Defense_Pace_Penalty = 0

# Rationale: Elite defenses force longer possessions, prevent easy buckets
# Example: Celtics defense forces half-court sets
```

**7. Final Calculation**
```python
Final_Pace = Base_Pace
           + Pace_Mismatch_Penalty
           + Turnover_Pace_Impact
           - FT_Pace_Penalty
           + Defense_Pace_Penalty

# Clamp to realistic NBA range
Final_Pace = clamp(Final_Pace, 92, 108)
```

### Example Scenarios:

**Scenario 1: High-Scoring Shootout**
```
Warriors: 108 pace (season), 110 pace (recent)
Kings: 106 pace (season), 110 pace (recent)
Turnovers: 16 and 15 (high)
FT Rate: 0.18 and 0.20 (low)
Elite Defense: None

Calculation:
  Adjusted Paces: 108.8 and 107.6
  Base Pace: 108.2

  Adjustments:
    Pace Mismatch: 0 (diff 1.2 < 5)
    Turnover Boost: +0.15 (15.5 turnovers)
    FT Penalty: 0 (rate 0.19 < 0.25)
    Defense Penalty: 0

  Final: 108.2 + 0 + 0.15 - 0 + 0 = 108.35
  Clamped: 108.0 (upper bound)

Result: Very fast pace shootout ✓
```

**Scenario 2: Defensive Grind**
```
Celtics: 98 pace (season), 95 pace (recent), ELITE DEFENSE
Knicks: 96 pace (season), 95 pace (recent), ELITE DEFENSE
Turnovers: 11 and 10 (low)
FT Rate: 0.28 and 0.26 (high)

Calculation:
  Adjusted Paces: 96.8 and 95.6
  Base Pace: 96.2

  Adjustments:
    Pace Mismatch: 0 (diff 1.2 < 5)
    Turnover Boost: 0 (10.5 < 15)
    FT Penalty: -0.2 (rate 0.27)
    Defense Penalty: -1.5 (elite defense)

  Final: 96.2 + 0 + 0 - 0.2 + (-1.5) = 94.5

Result: Slow defensive grind ✓
```

**Scenario 3: Pace Mismatch**
```
Pacers: 110 pace (season), 112 pace (recent)
Grizzlies: 95 pace (season), 93 pace (recent)
Turnovers: 14 and 13 (normal)
FT Rate: 0.22 and 0.24 (normal)

Calculation:
  Adjusted Paces: 110.8 and 94.2
  Base Pace: 102.5
  Pace Difference: 16.6

  Adjustments:
    Pace Mismatch: -2.0 (diff > 8)
    Turnover Boost: 0
    FT Penalty: 0
    Defense Penalty: 0

  Final: 102.5 + (-2.0) = 100.5

Result: Mismatch drags pace down ✓
```

**Scenario 4: Turnover Fest**
```
Both teams: 100 pace (average)
Turnovers: 19 and 18 (high)
FT Rate: 0.20 and 0.21 (normal)

Calculation:
  Adjusted Paces: 100 and 100
  Base Pace: 100

  Adjustments:
    Pace Mismatch: 0
    Turnover Boost: +1.05 (18.5 turnovers)
    FT Penalty: 0
    Defense Penalty: 0

  Final: 100 + 1.05 = 101.05

Result: Turnovers push pace above average ✓
```

### Impact Range:

| Scenario | Typical Pace | Key Factors |
|----------|--------------|-------------|
| Fast shootout | 106-108 | Fast teams, high turnovers, no elite D |
| Normal game | 98-102 | Average across all factors |
| Pace mismatch | 98-101 | One fast, one slow (-1 to -2 penalty) |
| Defensive grind | 92-96 | Elite defense, high FT rate, low turnovers |
| Turnover game | 102-105 | 17+ turnovers per team |

### Application to Scoring:

Once pace is calculated, it's applied as a multiplier to team projections:

```python
league_avg_pace = 100.0
pace_diff = final_pace - league_avg_pace
pace_multiplier = 1.0 + (pace_diff / 100.0) * 0.3

home_projected *= pace_multiplier
away_projected *= pace_multiplier
```

**Example:**
```
Final pace: 105 (fast game)
Pace diff: 105 - 100 = +5
Multiplier: 1.0 + (5 / 100) * 0.3 = 1.015

Home: 115.0 × 1.015 = 116.7
Away: 112.0 × 1.015 = 113.7
```

### Data Sources:

- **Season pace:** Team's season average pace (possessions per 48 min)
- **Last 5 pace:** Team's last 5 games average pace
- **Season turnovers:** Team's season average turnovers per game
- **FT rate:** Team's FTA / FGA ratio
- **Elite defense:** Top 10 defensive rating (DRTG rank 1-10)

---

## STEP 1B: PACE VOLATILITY & CONTEXTUAL DAMPENING (NEW in v4.5!)

**Purpose:** Prevent over-reliance on pace in games with high pace volatility or contextual factors that slow tempo.

### Key Innovation: Anti-Inflation Pace Correction

After calculating the advanced pace projection, the model now applies volatility-based dampening to reduce prediction inflation when pace is unreliable.

**Problem Solved:** Model was over-trusting pace in volatile games (teams with inconsistent tempo) and missing contextual factors (turnovers, free throws) that reduce effective pace impact.

### Step-by-Step Formula:

**1. Calculate Pace Volatility (σ) for Each Team**
```python
Recent_Game_Paces = [pace from last 10 games]
Pace_Std_Dev = standard_deviation(Recent_Game_Paces)

IF Pace_Std_Dev > 3.5:
    Volatility_Factor = 0.85  # High volatility: reduce pace confidence 15%
ELSE IF Pace_Std_Dev > 2.5:
    Volatility_Factor = 0.92  # Medium volatility: reduce 8%
ELSE IF Pace_Std_Dev < 1.5:
    Volatility_Factor = 1.05  # Low volatility: trust pace slightly more
ELSE:
    Volatility_Factor = 1.0   # Normal volatility: unchanged
```

**2. Calculate Contextual Pace Dampener**
```python
Combined_TOV_PCT = (Team1_TOV_PCT + Team2_TOV_PCT) / 2
Combined_FT_Rate = (Team1_FTA_Rate + Team2_FTA_Rate) / 2

Dampener = 1.0

# High turnover rate (slows effective pace)
IF Combined_TOV_PCT > 14.5%:
    Dampener *= 0.97

# High FT rate (clock stoppages)
IF Combined_FT_Rate > 0.28:
    Dampener *= 0.96

# Both teams volatile (unpredictable pace)
IF Home_Volatility_Factor < 0.95 AND Away_Volatility_Factor < 0.95:
    Dampener *= 0.94

# Clamp to minimum 0.90 (never reduce more than 10%)
Dampener = max(0.90, Dampener)
```

**3. Apply Volatility Factors and Dampener**
```python
Home_Projected *= Home_Volatility_Factor
Away_Projected *= Away_Volatility_Factor
Home_Projected *= Contextual_Dampener
Away_Projected *= Contextual_Dampener
```

### Example Scenarios:

**Scenario 1: Volatile Pace Team (Warriors Style)**
```
Team recent paces: [108, 95, 110, 92, 106, 98, 112, 94, 109, 96]
Pace Std Dev: 7.8 (VERY HIGH)

Volatility Factor: 0.85 (reduce pace impact by 15%)

Before: 115 projected pts
After: 115 × 0.85 = 97.8 projected pts

Rationale: Team's pace is all over the map, can't reliably predict high pace
```

**Scenario 2: Stable Pace, High Turnovers**
```
Team 1 pace std dev: 1.2 → Volatility Factor: 1.05
Team 2 pace std dev: 1.4 → Volatility Factor: 1.05
Combined TOV%: 15.2% (high)
Combined FT rate: 0.26 (normal)

Contextual Dampener: 0.97 (high turnovers slow effective pace)

Before: 120 projected pts
After: 120 × 1.05 × 0.97 = 122.2 projected pts

Rationale: Stable pace (slight boost) but turnovers dampen it slightly
```

**Scenario 3: Both Teams Volatile + High FT Rate**
```
Team 1 pace std dev: 4.2 → Volatility Factor: 0.85
Team 2 pace std dev: 3.8 → Volatility Factor: 0.85
Combined FT rate: 0.30 (high)

Contextual Dampener: 0.96 × 0.94 = 0.90 (both volatile + high FT)

Before: 118 projected pts
After: 118 × 0.85 × 0.90 = 90.3 projected pts

Rationale: Maximum dampening - unreliable pace + clock stoppages
```

### Impact Range:

| Scenario | Volatility | Dampener | Total Impact |
|----------|-----------|----------|--------------|
| Stable pace, normal game | 1.05x | 1.0x | +5% |
| Normal volatility | 1.0x | 1.0x | 0% (unchanged) |
| Medium volatility | 0.92x | 1.0x | -8% |
| High volatility, high turnovers | 0.85x | 0.97x | -17% |
| Maximum dampening | 0.85x | 0.90x | -23% |

**Expected Effect:** Reduces over-prediction in volatile pace games by 8-23%, preventing inflation.

---

## STEP 2: TURNOVER ADJUSTMENT

**Note:** Turnover adjustment is now integrated into the Advanced Pace Calculation (STEP 1).
The turnover-driven pace impact accounts for high-turnover games creating faster tempo.

See STEP 1 for details on how turnovers affect pace projection.

---

## STEP 3: DEFENSE ADJUSTMENT (Dynamic)

**Weight:** Base 30% × dynamic multiplier (0.30 to 1.50)

### Key Innovation: Defense Impact Scales with Offensive Form

The model now adjusts defensive penalties based on whether the offense is hot, normal, or cold:

- **Hot offense (+4 ORTG or PPG):** Defense matters less (30-50% of normal)
- **Cold offense (-4 ORTG or PPG):** Defense matters more (150% of normal)
- **Normal offense:** Defense matters at baseline (100% of normal)

---

## STEP 3B: ENHANCED DEFENSIVE ADJUSTMENTS (NEW in v4.5!)

**Purpose:** Apply MORE AGGRESSIVE defensive multipliers to prevent over-prediction against elite defenses.

### Key Innovation: Tiered DRTG Multipliers with Trend Modifiers

**Problem Solved:** Previous defense adjustments were too mild. Elite defenses (rank 1-10) were not suppressing opponent scoring enough, leading to over-prediction in defensive matchups.

### Formula:

**1. Base Defensive Multiplier (Applied to Opponent's Projected Scoring)**

| Defense Tier | DRTG Rank | Base Multiplier | Effect on Opponent |
|--------------|-----------|-----------------|-------------------|
| **Elite Top-5** | 1-5 | 0.91 | -9% scoring |
| **Elite** | 6-10 | 0.94 | -6% scoring |
| **Above Average** | 11-15 | 0.97 | -3% scoring |
| **Average** | 16-20 | 0.99 | -1% scoring |
| **Below Average** | 21-25 | 1.01 | +1% scoring |
| **Weak** | 26-30 | 1.03 | +3% scoring |

**2. Recent Defensive Trend Modifier**

```python
Recent_DRTG = avg(last 5 games DRTG)
Season_DRTG = season average DRTG
Trend = Recent_DRTG - Season_DRTG

IF Trend < -1.5:
    Trend_Modifier = 0.97  # Defense improving → more strict
ELSE IF Trend > 1.5:
    Trend_Modifier = 1.02  # Defense declining → less strict
ELSE:
    Trend_Modifier = 1.0   # Normal
```

**3. Final Defensive Multiplier**

```python
Final_Multiplier = Base_Multiplier × Trend_Modifier
Opponent_Projected_Score *= Final_Multiplier
```

**4. Double-Strong-Defense Penalty**

When **BOTH teams** have elite defenses:

```python
IF Both_Teams_DRTG_Rank <= 15:
    Additional_Penalty = 0.98  # -2% additional
    Both_Teams_Score *= 0.98

IF Both_Teams_DRTG_Rank <= 10:
    Additional_Penalty = 0.96  # -4% additional
    Both_Teams_Score *= 0.96
```

### Examples:

**Example 1: Elite Defense (Rank 3) with Improving Trend**
```
Opponent faces Celtics defense:
  DRTG Rank: #3
  Recent DRTG: 107.2
  Season DRTG: 109.5
  Trend: -2.3 (improving)

Base Multiplier: 0.91 (elite top-5 tier)
Trend Modifier: 0.97 (improving defense)
Final Multiplier: 0.91 × 0.97 = 0.88

Before: 115 projected pts
After: 115 × 0.88 = 101.2 projected pts (-11.8%)

Result: Elite defense with hot form significantly suppresses scoring
```

**Example 2: Average Defense (Rank 18)**
```
Opponent faces average defense:
  DRTG Rank: #18
  Trend: 0.0 (normal)

Base Multiplier: 0.99 (average tier)
Trend Modifier: 1.0
Final Multiplier: 0.99

Before: 112 projected pts
After: 112 × 0.99 = 110.9 projected pts (-1%)

Result: Minor adjustment for average defense
```

**Example 3: Weak Defense (Rank 28) with Declining Trend**
```
Opponent faces weak defense:
  DRTG Rank: #28
  Recent DRTG: 118.5
  Season DRTG: 116.2
  Trend: +2.3 (declining)

Base Multiplier: 1.03 (weak tier)
Trend Modifier: 1.02 (declining defense)
Final Multiplier: 1.03 × 1.02 = 1.05

Before: 108 projected pts
After: 108 × 1.05 = 113.4 projected pts (+5%)

Result: Weak defense getting worse → opponent scores more
```

**Example 4: Both Teams Elite Defense (Ranks 5 and 7)**
```
Team 1 defense: Rank #5 → mult 0.91
Team 2 defense: Rank #7 → mult 0.94

Team 1 projected: 110 → 110 × 0.94 = 103.4
Team 2 projected: 108 → 108 × 0.91 = 98.3

Both ranked ≤10 → Apply double-penalty: 0.96
Team 1: 103.4 × 0.96 = 99.3
Team 2: 98.3 × 0.96 = 94.4

Total: 193.7 (defensive slugfest)

Result: Combined effect of elite defenses + double-penalty = low-scoring game
```

### Impact Summary:

| Matchup Type | Base Effect | With Trends | Total Range |
|--------------|-------------|-------------|-------------|
| vs Elite top-5 defense | -9% | -11% to -7% | 10-13 pts reduction |
| vs Elite defense (6-10) | -6% | -8% to -4% | 7-9 pts reduction |
| vs Average defense | -1% | -3% to +1% | 1-3 pts reduction |
| vs Weak defense | +3% | +1% to +5% | 1-6 pts increase |
| Both elite defenses | Additional -4% to -2% | - | 4-8 pts total reduction |

**Expected Effect:** Prevents 5-15 point over-prediction in defensive matchups.

### Process:

**Step 1: Get base defensive adjustment**
```python
defense_adjusted_ppg = get_historical_ppg_vs_defense_tier(team, opponent_defense_tier)
defense_delta = defense_adjusted_ppg - season_avg_ppg
```

**Step 2: Calculate dynamic multiplier**
```python
# Determine offensive form
offense_change = recent_ortg_change OR recent_ppg_change

if offense_change >= 4.0:  # HOT OFFENSE
    if opponent_def_rank <= 10:
        multiplier = 0.30  # Elite defense: reduce to 30%
    elif opponent_def_rank <= 25:
        multiplier = 0.40  # Average defense: reduce to 40%
    else:
        multiplier = 0.50  # Weak defense: reduce to 50%

elif offense_change <= -4.0:  # COLD OFFENSE
    multiplier = 1.50  # Amplify all defenses to 150%

else:  # NORMAL OFFENSE
    multiplier = 1.00  # Keep at 100% (unchanged)
```

**Step 3: Apply scaled adjustment**
```python
adjustment = defense_delta × 0.3 × multiplier
projected_score += adjustment
```

### Examples:

**Hot Offense vs Elite Defense (BOS):**
```
BOS: Recent PPG +6.7, Recent ORTG +0.0 → HOT
Opponent: NYK Defense rank #14 (average)

Base delta: -6.8 pts (vs average defense historically)
Multiplier: 0.40 (hot vs average defense)
Adjustment: -6.8 × 0.3 × 0.40 = -0.82 pts

Result: Hot offense reduces defense impact from -2.04 to -0.82 pts
        "We're on fire, defense can't stop us completely!"
```

**Normal Offense vs Strong Defense (NYK):**
```
NYK: Recent PPG -0.4, Recent ORTG +0.0 → NORMAL
Opponent: BOS Defense rank #19 (average)

Base delta: -21.2 pts (vs average defense historically)
Multiplier: 1.00 (normal offense)
Adjustment: -21.2 × 0.3 × 1.00 = -6.36 pts

Result: Normal offense keeps defense penalty unchanged
```

**Cold Offense vs Weak Defense (Hypothetical):**
```
Team: Recent PPG -5.0, Recent ORTG -5.5 → COLD
Opponent: Defense rank #28 (weak)

Base delta: -3.0 pts (vs weak defense)
Multiplier: 1.50 (cold offense amplifies)
Adjustment: -3.0 × 0.3 × 1.50 = -1.35 pts

Result: Cold offense amplifies even weak defense from -0.9 to -1.35 pts
        "Can't score on anyone, even weak defenses hurt!"
```

### Multiplier Table:

| Offensive Status | vs Elite (1-10) | vs Avg (11-25) | vs Weak (26-30) |
|------------------|-----------------|----------------|-----------------|
| Hot (+4 or more) | 0.30x (↓70%)   | 0.40x (↓60%)  | 0.50x (↓50%)   |
| Normal (-3.9 to +3.9) | 1.00x (unchanged) | 1.00x (unchanged) | 1.00x (unchanged) |
| Cold (-4 or worse) | 1.50x (↑50%)   | 1.50x (↑50%)  | 1.50x (↑50%)   |

### Data Quality Levels:
- **Excellent:** 3+ games vs similar defense
- **Limited:** 1-2 games (less weight)
- **Fallback:** No historical data, uses season average

---

## STEP 4: DEFENSE QUALITY ADJUSTMENT (Supplementary) - NEW in v4.4!

**Weight:** -6.0 to +5.0 points (supplementary to dynamic defense adjustment)

### Key Innovation: Rank-Based Defense Adjustment

This is a supplementary adjustment that works alongside the dynamic defense adjustment above. While the dynamic adjustment uses historical matchup data and offensive form, this adjustment provides additional context based purely on the opponent's defensive rank.

**Purpose:**
- Provide proportional adjustment based on defensive quality
- Use linear interpolation within tiers for smooth scaling
- Asymmetric impact (elite defenses penalize more than bad defenses boost)

### Formula:

```python
# Elite Defense Tier (Ranks 1-10)
IF opponent_def_rank >= 1 AND opponent_def_rank <= 10:
    adjustment = -6.0 + ((opponent_def_rank - 1) * (2.0 / 9))
    # Ranges from -6.0 (rank 1) to -4.0 (rank 10)

# Average Defense Tier (Ranks 11-19)
ELSE IF opponent_def_rank >= 11 AND opponent_def_rank <= 19:
    adjustment = 0.0
    # No adjustment for average defenses

# Bad Defense Tier (Ranks 20-30)
ELSE IF opponent_def_rank >= 20 AND opponent_def_rank <= 30:
    adjustment = 3.0 + ((opponent_def_rank - 20) * (2.0 / 10))
    # Ranges from +3.0 (rank 20) to +5.0 (rank 30)
```

### Examples:

**Playing Against Elite Defense (Rank 1):**
```
Opponent defense rank: #1 (best in league)
Adjustment: -6.0 + ((1 - 1) * 0.222) = -6.0 pts

Result: Strongest penalty for facing the best defense
```

**Playing Against Good Defense (Rank 7):**
```
Opponent defense rank: #7 (elite tier)
Adjustment: -6.0 + ((7 - 1) * 0.222) = -6.0 + 1.33 = -4.67 pts

Result: Solid penalty for facing strong defense
```

**Playing Against Average Defense (Rank 15):**
```
Opponent defense rank: #15 (average tier)
Adjustment: 0.0 pts

Result: No adjustment for average defenses
```

**Playing Against Bad Defense (Rank 25):**
```
Opponent defense rank: #25 (bad tier)
Adjustment: 3.0 + ((25 - 20) * 0.2) = 3.0 + 1.0 = +4.0 pts

Result: Moderate bonus for facing weak defense
```

**Playing Against Worst Defense (Rank 30):**
```
Opponent defense rank: #30 (worst in league)
Adjustment: 3.0 + ((30 - 20) * 0.2) = 3.0 + 2.0 = +5.0 pts

Result: Maximum bonus for facing the worst defense
```

### Adjustment Table by Tier:

| Tier | Ranks | Range | Slope | Rationale |
|------|-------|-------|-------|-----------|
| Elite | 1-10 | -6.0 to -4.0 | 0.222 pts/rank | Strong penalty for top defenses |
| Average | 11-19 | 0.0 | N/A | No adjustment for middle tier |
| Bad | 20-30 | +3.0 to +5.0 | 0.2 pts/rank | Moderate bonus for weak defenses |

### Design Rationale:

1. **Linear interpolation within tiers:** Ensures smooth scaling rather than discrete jumps. A rank 5 defense should be penalized more than rank 10, but less than rank 1.

2. **Asymmetric ranges:** Elite defenses get -6.0 to -4.0 (2-point range), while bad defenses get +3.0 to +5.0 (2-point range). Elite defense penalty is stronger (6.0 max) than bad defense bonus (5.0 max).

3. **Zero for average:** Ranks 11-19 (middle third) get no adjustment to avoid unnecessary noise.

4. **Supplementary role:** This works WITH the dynamic defense adjustment, not instead of it. The dynamic adjustment handles offensive form and matchup history; this handles defensive quality.

### Interaction with Dynamic Defense Adjustment:

**Combined Example:**
```
Team with hot offense (+5 PPG recent) vs Rank 5 defense:

Dynamic Defense Adjustment: -2.0 pts (reduced from -6.0 due to hot form)
Defense Quality Adjustment: -5.11 pts (rank 5 elite penalty)
Total Defense Impact: -7.11 pts

Interpretation: Even a hot offense faces significant penalty against elite defense
```

---

## STEP 5: HOME COURT ADVANTAGE (Dynamic)

**Weight:** Variable (0-6 points to home team)

### Key Innovation: Context-Aware Home Court Advantage

The model now calculates a dynamic home court advantage that varies from 0-6 points based on:
- Home team's home record strength
- Away team's road record weakness
- Home team's recent home momentum (last 3 games)

This replaces the old static 2.5-point home advantage with a context-aware calculation.

### Formula:

```python
Base_Home_Advantage = 2.5

# Factor 1: Home record strength
# Teams with strong home records get bigger boost
Home_Record_Multiplier = (home_win_pct - 0.500) * 3

# Factor 2: Opponent road weakness
# Playing against poor road teams increases advantage
Road_Weakness_Multiplier = (0.500 - road_win_pct) * 2

# Factor 3: Recent home performance momentum
IF last3_home_wins >= 2:
    Home_Momentum = +1.0  # Hot at home
ELSE IF last3_home_wins == 0:
    Home_Momentum = -1.0  # Cold at home
ELSE:
    Home_Momentum = 0     # Neutral

# Final calculation
Home_Court_Advantage = Base_Home_Advantage * (1 + Home_Record_Multiplier + Road_Weakness_Multiplier) + Home_Momentum

# Clamp result between 0 and 6
Home_Court_Advantage = max(0, min(6, Home_Court_Advantage))
```

### Examples:

**Strong Home Team vs Weak Road Team:**
```
Home team: 20-5 at home (0.800 win%)
Away team: 8-17 on road (0.320 win%)
Last 3 home games: 3 wins

Home_Record_Multiplier = (0.800 - 0.500) * 3 = 0.900
Road_Weakness_Multiplier = (0.500 - 0.320) * 2 = 0.360
Home_Momentum = +1.0

HCA = 2.5 * (1 + 0.900 + 0.360) + 1.0
    = 2.5 * 2.260 + 1.0
    = 5.65 + 1.0
    = 6.65 → clamped to 6.0 points
```

**Average Teams, Neutral Momentum:**
```
Home team: 12-12 at home (0.500 win%)
Away team: 10-10 on road (0.500 win%)
Last 3 home games: 1 win

Home_Record_Multiplier = (0.500 - 0.500) * 3 = 0.000
Road_Weakness_Multiplier = (0.500 - 0.500) * 2 = 0.000
Home_Momentum = 0

HCA = 2.5 * (1 + 0.000 + 0.000) + 0
    = 2.5 points (baseline)
```

**Weak Home Team vs Strong Road Team, Cold at Home:**
```
Home team: 8-17 at home (0.320 win%)
Away team: 18-7 on road (0.720 win%)
Last 3 home games: 0 wins

Home_Record_Multiplier = (0.320 - 0.500) * 3 = -0.540
Road_Weakness_Multiplier = (0.500 - 0.720) * 2 = -0.440
Home_Momentum = -1.0

HCA = 2.5 * (1 + (-0.540) + (-0.440)) + (-1.0)
    = 2.5 * 0.020 + (-1.0)
    = 0.05 - 1.0
    = -0.95 → clamped to 0.0 points
```

### Impact Range:

| Scenario | Typical Range |
|----------|---------------|
| Elite home team vs weak road team, hot at home | 5.0-6.0 pts |
| Strong home team vs average road team | 3.5-4.5 pts |
| Average teams, neutral momentum | 2.0-3.0 pts |
| Weak home team vs strong road team | 0.5-1.5 pts |
| Terrible home team vs elite road team, cold | 0.0-0.5 pts |

### Data Sources:

- **home_win_pct:** Calculated from team_game_logs table (home games only)
- **road_win_pct:** Calculated from team_game_logs table (away games only)
- **last3_home_wins:** Count of wins in team's last 3 home games

---

## STEP 6: ROAD PENALTY (Away Team) - NEW in v4.4!

**Weight:** -7.0 to 0.0 points (applied to away team only)

### Key Innovation: Non-Linear Road Penalty

This is the counterpart to home court advantage - it penalizes away teams based on their road win percentage using non-linear scaling with tiered multipliers. Teams with very poor road records struggle disproportionately more than their win percentage alone would suggest.

**Purpose:**
- Penalize teams with poor road records
- Use tiered multipliers for non-linear scaling (worse records = harsher penalties)
- Cap maximum penalty to prevent over-penalization

### Formula:

```python
# Good Road Teams (≥50% road win rate)
IF road_win_pct >= 0.50:
    penalty = 0.0  # No penalty for competent road teams

# Below-Average to Poor Road Teams (<50%)
ELSE:
    distance_below = 0.50 - road_win_pct
    base_penalty = -distance_below * 10.0

    # Apply tiered multiplier based on severity
    IF road_win_pct < 0.30:  # Catastrophic (<30%)
        penalty = base_penalty * 1.4
    ELSE IF road_win_pct < 0.40:  # Poor (30-39%)
        penalty = base_penalty * 1.2
    ELSE:  # Below-average (40-49%)
        penalty = base_penalty * 1.0

    # Clamp to maximum penalty
    penalty = max(-7.0, min(0.0, penalty))
```

### Penalty Tiers:

| Road Win % | Tier | Multiplier | Typical Penalty Range |
|------------|------|------------|----------------------|
| ≥50% | Good | 0.0x | 0.0 pts |
| 40-49% | Below-Average | 1.0x | 0.0 to -1.0 pts |
| 30-39% | Poor | 1.2x | -1.2 to -2.4 pts |
| <30% | Catastrophic | 1.4x | -2.8 to -7.0 pts |

### Examples:

**Good Road Team (55%):**
```
Away team road record: 11-9 (0.550 win%)

Penalty: 0.0 pts (≥50% road win rate)

Result: No penalty for competent road teams
```

**Below-Average Road Team (45%):**
```
Away team road record: 9-11 (0.450 win%)

Distance below 50%: 0.50 - 0.450 = 0.050
Base penalty: -0.050 * 10.0 = -0.5
Multiplier: 1.0x (below-average tier)
Penalty: -0.5 * 1.0 = -0.5 pts

Result: Minor penalty for slightly below-average road team
```

**Poor Road Team (35%):**
```
Away team road record: 7-13 (0.350 win%)

Distance below 50%: 0.50 - 0.350 = 0.150
Base penalty: -0.150 * 10.0 = -1.5
Multiplier: 1.2x (poor tier)
Penalty: -1.5 * 1.2 = -1.8 pts

Result: Enhanced penalty for poor road performance
```

**Catastrophic Road Team (25%):**
```
Away team road record: 5-15 (0.250 win%)

Distance below 50%: 0.50 - 0.250 = 0.250
Base penalty: -0.250 * 10.0 = -2.5
Multiplier: 1.4x (catastrophic tier)
Penalty: -2.5 * 1.4 = -3.5 pts

Result: Strong penalty for terrible road record
```

**Worst-Case Road Team (15%):**
```
Away team road record: 3-17 (0.150 win%)

Distance below 50%: 0.50 - 0.150 = 0.350
Base penalty: -0.350 * 10.0 = -3.5
Multiplier: 1.4x (catastrophic tier)
Penalty: -3.5 * 1.4 = -4.9 pts

Result: Severe penalty for extremely poor road team
```

### Design Rationale:

1. **No penalty for good road teams:** Teams with ≥50% road win rate are competitive on the road and don't need penalization. Road advantage is handled by the home team's home court advantage adjustment.

2. **Linear base formula:** The distance below 50% is multiplied by 10 to create a meaningful penalty scale (0.10 = -1.0 penalty).

3. **Tiered multipliers:** Different multipliers for different tiers reflect that teams with very poor road records struggle more than their win percentage alone would suggest:
   - Below-average (40-49%): Normal penalty (1.0x)
   - Poor (30-39%): Enhanced penalty (1.2x)
   - Catastrophic (<30%): Strong penalty (1.4x)

4. **-7.0 cap:** Prevents extreme over-penalization. Even the worst road teams can occasionally have good games.

5. **Non-negative results:** Penalty is always ≤0, never positive. Good road teams get 0, not a bonus.

### Relationship to Home Court Advantage:

**Combined Example:**
```
Strong home team (0.800 home win%) vs Weak road team (0.280 road win%)

Home Court Advantage: +5.7 pts (to home team)
Road Penalty: -3.1 pts (to away team)
Total Home/Road Impact: +8.8 pts swing

Interpretation: Massive advantage for dominant home team facing terrible road team
```

### Data Sources:

- **road_win_pct:** Calculated from team_game_logs table (away games only, where is_home = 0)

---

## STEP 7: MATCHUP ADJUSTMENTS

**NEW in v4.0:** Specific matchup-based bonuses/penalties

### Rules Applied:
1. **Pace Matchups:** Fast vs fast (+8), slow vs slow (-8)
2. **Elite Offense vs Weak Defense:** Top-5 offense vs bottom-5 defense (+10 total, +4 to offense)
3. **Elite Defense Matchups:** Elite defense vs elite offense (-10 total, -5 to offense)
4. **3PT Volume:** Both teams high 3PT volume (+6.5), both strong 3PT defense (-6.5)
5. **Rim Protection:** Strong rim protection vs paint-heavy offense (-5.5 to offense)
6. **Foul Rate:** Both teams high foul rate (+7), both low foul rate (-4.5)

See MATCHUP_ADJUSTMENTS documentation for full details.

---

## STEP 7B: OPPONENT MATCHUP ADJUSTMENTS (NEW in v4.6!)

**Weight:** -10.0 to +10.0 points per team

### Key Innovation: Defense-Based Matchup Analysis

This feature compares each team's offensive capabilities directly against their opponent's specific defensive weaknesses/strengths. Unlike generic defensive adjustments, this analyzes how a team's offense matches up against what the opponent's defense typically allows.

**Purpose:**
- Compare team offense vs opponent defense (not just league averages)
- Identify favorable/unfavorable matchups based on opponent-specific defensive metrics
- Apply targeted scoring adjustments for FG%, 3P%, and pace matchups
- Enhance AI Coach analysis with opponent context

### What Are Opponent Stats?

Opponent statistics represent what each team **ALLOWS** their opponents to do on average:
- `opp_fg_pct_allowed` - FG% allowed to opponents
- `opp_3p_pct_allowed` - 3P% allowed to opponents
- `opp_pace_allowed` - Pace allowed to opponents
- `opp_ppg_allowed` - Points per game allowed

**Example:** If Team A has `opp_fg_pct_allowed = 0.465`, it means opponents shoot 46.5% FG against Team A's defense.

### Formula Components:

**1. FG% Matchup Adjustment**
```python
# Calculate FG% advantage
fg_advantage = (team_fg_pct - opponent_opp_fg_pct_allowed) × 100

# Convert to points: +1% FG advantage = +2 pts
fg_adjustment = fg_advantage × 2.0

# Cap at ±5 points
fg_adjustment = max(min(fg_adjustment, 5.0), -5.0)
```

**Example:**
```
Team shoots 47.5% FG
Opponent allows 46.5% FG (opp_fg_pct_allowed)
→ FG advantage: +1.0%
→ FG adjustment: +1.0 × 2.0 = +2.0 pts
```

**2. 3-Point Matchup Adjustment**
```python
# Calculate 3P% advantage
three_advantage = (team_3p_pct - opponent_opp_3p_pct_allowed) × 100

# Convert to points based on 3PA volume
# +1% 3P% with 35 attempts = 0.35 more 3PM = 1.05 pts
three_adjustment = (three_advantage / 100) × team_3pa × 3.0

# Cap at ±4 points
three_adjustment = max(min(three_adjustment, 4.0), -4.0)
```

**Example:**
```
Team shoots 37.5% from 3 (38 attempts per game)
Opponent allows 35.0% from 3 (opp_3p_pct_allowed)
→ 3P advantage: +2.5%
→ 3P adjustment: (0.025 × 38 × 3.0) = +2.85 pts
```

**3. Pace Matchup Adjustment**
```python
# Calculate pace difference
pace_diff = team_pace - opponent_opp_pace_allowed

# Each +1 possession = ~1.1 pts (league avg efficiency)
# Apply conservative 50% multiplier (pace factored elsewhere)
pace_adjustment = pace_diff × 1.1 × 0.5

# Cap at ±3 points
pace_adjustment = max(min(pace_adjustment, 3.0), -3.0)
```

**Example:**
```
Team pace: 102.0 possessions per game
Opponent allows: 98.0 pace (opp_pace_allowed)
→ Pace difference: +4.0 possessions
→ Pace adjustment: 4.0 × 1.1 × 0.5 = +2.2 pts
```

**4. Total Adjustment Cap**
```python
# Sum all adjustments
total_adjustment = fg_adjustment + three_adjustment + pace_adjustment

# Cap total at ±10 points to prevent extreme stacking
total_adjustment = max(min(total_adjustment, 10.0), -10.0)
```

### Complete Example:

**Game: Milwaukee Bucks @ Phoenix Suns**

**Milwaukee Offense vs Phoenix Defense:**
```
Milwaukee FG%: 48.5%
Phoenix allows: 46.0% FG → +2.5% advantage → +5.0 pts (capped)

Milwaukee 3P%: 38.0% (40 attempts)
Phoenix allows: 35.5% from 3 → +2.5% advantage → +3.0 pts

Milwaukee pace: 104.0
Phoenix allows: 100.0 pace → +4.0 possessions → +2.2 pts

Total Milwaukee adjustment: +10.0 pts (capped at +10)
```

**Phoenix Offense vs Milwaukee Defense:**
```
Phoenix FG%: 47.0%
Milwaukee allows: 47.5% FG → -0.5% disadvantage → -1.0 pts

Phoenix 3P%: 36.5% (38 attempts)
Milwaukee allows: 37.0% from 3 → -0.5% disadvantage → -0.57 pts

Phoenix pace: 102.0
Milwaukee allows: 103.0 pace → -1.0 possessions → -0.55 pts

Total Phoenix adjustment: -2.1 pts
```

**Impact on Total:**
```
Milwaukee projected: 115.0 → 125.0 (+10.0 from favorable matchup)
Phoenix projected: 112.0 → 109.9 (-2.1 from tough matchup)
Total: 227.0 → 234.9 (+7.9 pts from opponent matchups)
```

### Design Rationale:

1. **Individual caps prevent dominance:** FG% (±5), 3P% (±4), Pace (±3) capped individually before total cap
2. **Conservative multipliers:** All multipliers are conservative to avoid over-adjusting
3. **Total ±10 cap:** Prevents extreme adjustments from stacking when all matchups favor one team
4. **Volume-based 3P adjustment:** 3-point impact scales with attempt volume (high-volume shooters affected more)
5. **50% pace multiplier:** Pace already factored in baseline, so matchup only adds marginal impact

### Data Pipeline:

**Automatic ETL Integration:**
1. Every game sync automatically computes opponent stats for both teams
2. Season stats aggregator computes average opponent stats (what team ALLOWS)
3. Prediction engine loads opponent defensive stats
4. Matchup adjustments applied to both team projections
5. AI Coach receives opponent matchup context for explanations

**Database Schema:**
- **team_game_logs:** 28 opponent stat columns (per-game opponent stats)
- **team_season_stats:** 31 opponent stat columns (season-average opponent stats)
- **Coverage:** 100% of games (896/896 for 2025-26 season)

### AI Coach Integration:

The AI Coach now has access to opponent matchup analysis and can explain:

**Example AI Explanation:**
```
"Miami shot 40.5% from three in this game, significantly higher than
the 34% they typically allow. This suggests Orlando exploited a
defensive weakness that our model correctly identified in the matchup
analysis, adding +4 points to Orlando's projection."

"Expected pace was 102 possessions based on season averages, but the
matchup analysis showed Phoenix typically slows teams down to 98 pace.
The actual game had 96 possessions, validating the opponent-adjusted
pace projection."
```

### Validation:

**Database Coverage:**
```sql
SELECT COUNT(*) as total_games,
       SUM(CASE WHEN opp_fg3a IS NOT NULL THEN 1 ELSE 0 END) as with_opp_stats
FROM team_game_logs WHERE season='2025-26';
-- Result: 896 | 896 (100% coverage)
```

**Symmetry Check:**
```
Team A's opponent stats = Team B's actual stats
Team B's opponent stats = Team A's actual stats
(Validated for all 896 games)
```

### Key Differences from Other Adjustments:

| Adjustment Type | What It Does |
|----------------|--------------|
| **Defense Adjustment** | Generic defensive quality (DRTG-based) |
| **Defense Quality** | Rank-based defensive penalty/bonus |
| **Old Matchup Adjustments** | Rule-based bonuses (fast vs fast, elite vs weak) |
| **Opponent Matchup (NEW)** | Team-specific offense vs defense comparison |

The opponent matchup adjustment is **complementary** to other defensive adjustments - it adds team-specific context on top of general defensive quality metrics.

---

## STEP 8: DYNAMIC 3PT SHOOTOUT ADJUSTMENT

**Weight:** Variable (0-15+ points per team based on context)

### Key Innovation: Context-Aware 3-Point Scoring

The model now uses an advanced, multi-factor 3PT adjustment system that identifies true shootout environments like LAL/BOS (24 made threes), DEN/ATL (36 made threes), and UTA/NYK (massive scoring).

**This replaces the old disabled shootout detection** with a sophisticated scoring system that considers:
- Team 3PT shooting talent vs league average
- Opponent 3PT defense quality
- Recent 3PT shooting form (last 5 games)
- Game pace (more possessions = more 3PT attempts)
- Rest/fatigue impact on shooting

### Formula Components:

**1. Team 3PT Ability Score**
```python
Team_3PT_Ability = (team_3p_pct - league_avg_3p_pct) × 100

Example: Team shoots 41%, league avg 36%
        = (0.41 - 0.36) × 100 = 5.0
```

**2. Opponent 3PT Defense Score**
```python
Opponent_3PT_Defense = (opponent_3p_allowed_pct - league_avg_3p_pct) × 100

Example: Opponent allows 39%, league avg 36%
        = (0.39 - 0.36) × 100 = 3.0

Positive = weak 3PT defense (allows more 3s)
Negative = strong 3PT defense (allows fewer 3s)
```

**3. Recent 3PT Trend Score**
```python
Recent_3PT_Trend = (last5_3p_pct - season_3p_pct) × 50

Example: Recent 43%, season 38%
        = (0.43 - 0.38) × 50 = 2.5
```

**4. Pace Factor**
```python
Pace_Factor = (projected_pace - 100) × 0.15

Example: Projected pace 105 possessions
        = (105 - 100) × 0.15 = 0.75

Faster games = more 3PT opportunities
Slower games = fewer 3PT opportunities
```

**5. Rest Factor**
```python
IF rest_days >= 2:
    Rest_Factor = +1.0  # Fresh legs, better shooting
ELSE IF on_back_to_back:
    Rest_Factor = -1.5  # Tired legs, worse shooting
ELSE:
    Rest_Factor = 0     # Normal rest (1 day)
```

### Combined Shootout Score:

```python
Shootout_Score = Team_3PT_Ability
               + Opponent_3PT_Defense
               + Recent_3PT_Trend
               + Pace_Factor
               + Rest_Factor
```

### Bonus Tiers:

The shootout score is converted to a points bonus using confidence tiers:

```python
IF Shootout_Score > 10:
    Shootout_Bonus = Shootout_Score × 0.8  # High-confidence shootout
ELSE IF Shootout_Score > 6:
    Shootout_Bonus = Shootout_Score × 0.6  # Medium-confidence shootout
ELSE IF Shootout_Score > 3:
    Shootout_Bonus = Shootout_Score × 0.4  # Low-confidence shootout
ELSE:
    Shootout_Bonus = 0  # No meaningful 3PT boost
```

### Example Calculations:

**Elite 3PT Team vs Weak 3PT Defense (High Shootout):**
```
Team: 40.0% 3PT (season), 42.5% (last 5 games)
Opponent allows: 38.5% from 3PT
Projected pace: 105
Rest: 2 days (fresh)
League avg: 36.5%

Components:
  Team_3PT_Ability = (0.400 - 0.365) × 100 = 3.5
  Opponent_3PT_Defense = (0.385 - 0.365) × 100 = 2.0
  Recent_3PT_Trend = (0.425 - 0.400) × 50 = 1.25
  Pace_Factor = (105 - 100) × 0.15 = 0.75
  Rest_Factor = +1.0

Shootout_Score = 3.5 + 2.0 + 1.25 + 0.75 + 1.0 = 8.5

Tier: Medium (score > 6 but ≤ 10)
Shootout_Bonus = 8.5 × 0.6 = 5.1 pts
```

**Average 3PT Team, Normal Conditions:**
```
Team: 36.5% 3PT (season), 36.0% (last 5 games)
Opponent allows: 36.5% from 3PT
Projected pace: 100
Rest: 1 day (normal)
League avg: 36.5%

Components:
  Team_3PT_Ability = (0.365 - 0.365) × 100 = 0.0
  Opponent_3PT_Defense = (0.365 - 0.365) × 100 = 0.0
  Recent_3PT_Trend = (0.360 - 0.365) × 50 = -0.25
  Pace_Factor = (100 - 100) × 0.15 = 0.0
  Rest_Factor = 0

Shootout_Score = 0.0 + 0.0 + (-0.25) + 0.0 + 0.0 = -0.25

Tier: None (score ≤ 3)
Shootout_Bonus = 0.0 pts
```

**Elite Shooters, Hot Streak, Fast Pace (Extreme Shootout):**
```
Team: 42.0% 3PT (season), 45.0% (last 5 games)
Opponent allows: 39.0% from 3PT
Projected pace: 108
Rest: 3 days (very fresh)
League avg: 36.5%

Components:
  Team_3PT_Ability = (0.420 - 0.365) × 100 = 5.5
  Opponent_3PT_Defense = (0.390 - 0.365) × 100 = 2.5
  Recent_3PT_Trend = (0.450 - 0.420) × 50 = 1.5
  Pace_Factor = (108 - 100) × 0.15 = 1.2
  Rest_Factor = +1.0

Shootout_Score = 5.5 + 2.5 + 1.5 + 1.2 + 1.0 = 11.7

Tier: High (score > 10)
Shootout_Bonus = 11.7 × 0.8 = 9.4 pts
```

**Cold Shooting Team on B2B vs Elite Defense:**
```
Team: 34.0% 3PT (season), 30.0% (last 5 games)
Opponent allows: 34.0% from 3PT
Projected pace: 95
Rest: B2B (tired)
League avg: 36.5%

Components:
  Team_3PT_Ability = (0.340 - 0.365) × 100 = -2.5
  Opponent_3PT_Defense = (0.340 - 0.365) × 100 = -2.5
  Recent_3PT_Trend = (0.300 - 0.340) × 50 = -2.0
  Pace_Factor = (95 - 100) × 0.15 = -0.75
  Rest_Factor = -1.5

Shootout_Score = -2.5 + (-2.5) + (-2.0) + (-0.75) + (-1.5) = -9.25

Tier: None (score ≤ 3)
Shootout_Bonus = 0.0 pts (no negative penalties)
```

### Impact Range:

| Scenario | Shootout Score | Tier | Typical Bonus |
|----------|----------------|------|---------------|
| Elite shooters vs weak defense, hot, fast pace | 10-15 | High | 8-12 pts |
| Good shooters vs average defense, normal pace | 6-10 | Medium | 4-6 pts |
| Decent shooters vs average defense | 3-6 | Low | 1-2 pts |
| Average or below conditions | ≤3 | None | 0 pts |

### Why This Works:

1. **Multiplicative Effect:** Great shooting + weak defense + fast pace compounds
2. **Form Matters:** Recent hot shooting (LAL/BOS, DEN/ATL scenarios) gets boosted
3. **Context-Aware:** Fatigue (B2B) reduces bonus, fresh legs increase it
4. **No Over-Penalization:** Poor shooting environments get 0 bonus, not negative
5. **Scales Appropriately:** Extreme shootouts can add 15+ combined pts to total

### Data Sources:

- **team_3p_pct:** Season 3PT% from team_game_logs (FG3M / FG3A)
- **opponent_3p_allowed_pct:** Opponent's defensive 3PT% against
- **last5_3p_pct:** Last 5 games 3PT% from recent team_game_logs
- **rest_days:** Calculated from last game_date in team_game_logs
- **on_back_to_back:** True if last game was yesterday

---

## STEP 9: FATIGUE/REST ADJUSTMENT

**NEW in v4.0:** Penalties based on rest days and recent game intensity

### Rules:
1. **Extreme Recent Game:** Team played within 2 days AND game was 280+ total or likely OT
   - Penalty: -7 points from total

2. **Back-to-Back:** Team played yesterday (normal game)
   - Penalty: -4 points from total

3. **Well-Rested:** Both teams have 2+ days rest
   - Penalty: 0 points (no adjustment)

### Example:
```
NYK played yesterday (back-to-back), 215 total pts (normal game)
Penalty: -4.0 pts from final total
Total: 223.8 → 219.8
```

See FATIGUE_ADJUSTMENT_SUMMARY documentation for full details.

---

## STEP 10: SCORING COMPRESSION & BIAS CORRECTION (NEW in v4.5!)

**Purpose:** Final anti-inflation safeguard to prevent over-prediction when multiple high-scoring signals stack.

### Key Innovation: Master Compression Factor

**Problem Solved:** When pace is high AND offense is strong AND defense is weak AND 3PT shooting is hot, the model was stacking all these bonuses without dampening, leading to 10-20 point over-predictions.

This step applies a final compression to prevent signal stacking inflation.

### Formula Components:

**1. Signal Stacking Compression**

```python
Count high-scoring signals:
- Pace is high (>103 possessions)
- Offense is strong (top-10 ORTG rank)
- Three-point shooting is hot (>38% or above season avg)
- Defense is weak (bottom-10 DRTG rank)

IF 4 signals are high:
    Signal_Compression = 0.94  # -6% compression
ELSE IF 3 signals are high:
    Signal_Compression = 0.97  # -3% compression
ELSE IF 2 signals are high:
    Signal_Compression = 0.99  # -1% compression
ELSE:
    Signal_Compression = 1.0   # No compression
```

**2. Defensive Battle Detection**

```python
Low_Tempo = Projected_Pace < 98
Both_Strong_Defenses = (Home_DRTG_Rank <= 12 AND Away_DRTG_Rank <= 12)

IF Low_Tempo AND Both_Strong_Defenses:
    Defensive_Battle_Cap = 0.95  # -5% cap
ELSE IF Low_Tempo OR Both_Strong_Defenses:
    Defensive_Battle_Cap = 0.98  # -2% mild cap
ELSE:
    Defensive_Battle_Cap = 1.0   # No cap
```

**3. Projection vs Betting Line**

```python
Projected_Total = Home_Projected + Away_Projected
Line_Difference = Projected_Total - Betting_Line

IF Line_Difference > 8.0:
    Line_Compression = 0.96  # Way above line → compress 4%
ELSE IF Line_Difference > 5.0:
    Line_Compression = 0.98  # Above line → compress 2%
ELSE:
    Line_Compression = 1.0   # Within range
```

**4. Extreme High Total**

```python
IF Projected_Total > 240:
    High_Total_Compression = 0.96  # -4% compression
ELSE IF Projected_Total > 235:
    High_Total_Compression = 0.98  # -2% compression
ELSE:
    High_Total_Compression = 1.0   # Normal
```

**5. Pace Volatility Compression**

```python
Avg_Volatility = (Home_Volatility_Factor + Away_Volatility_Factor) / 2

IF Avg_Volatility < 0.92:
    Pace_Vol_Compression = 0.97  # High volatility → compress
ELSE:
    Pace_Vol_Compression = 1.0   # Normal
```

### Master Compression Calculation:

```python
Compression_Factor = 1.0

# Apply all compression factors multiplicatively
IF Signal_Compression < 1.0:
    Compression_Factor *= Signal_Compression

IF Defensive_Battle_Cap < 1.0:
    Compression_Factor *= Defensive_Battle_Cap

IF Line_Compression < 1.0:
    Compression_Factor *= Line_Compression

IF High_Total_Compression < 1.0:
    Compression_Factor *= High_Total_Compression

IF Pace_Vol_Compression < 1.0:
    Compression_Factor *= Pace_Vol_Compression

# Apply final compression
Home_Projected *= Compression_Factor
Away_Projected *= Compression_Factor
```

### Example Scenarios:

**Scenario 1: Maximum Inflation Risk**
```
Projected total: 242 pts (very high)
Betting line: 230 pts
High-scoring signals: 4 (pace high, offense strong, 3PT hot, defense weak)
Pace volatility: avg 0.90 (high)
Tempo/Defense: Normal

Compression factors:
  Signal stacking: 0.94 (4 signals)
  High total: 0.96 (>240)
  Line difference: 0.96 (12 pts above)
  Pace volatility: 0.97 (high vol)

Master compression: 0.94 × 0.96 × 0.96 × 0.97 = 0.84

Before: 242 pts total
After: 242 × 0.84 = 203.3 pts total

Reduction: 38.7 points (16% compression)

Rationale: Extreme stacking of high-scoring signals → aggressive dampening
```

**Scenario 2: Defensive Battle**
```
Projected total: 215 pts
Projected pace: 95 (low tempo)
Both defenses: Ranks #7 and #9 (elite)
Other signals: Normal

Compression factors:
  Defensive battle: 0.95 (low tempo + elite defenses)

Master compression: 0.95

Before: 215 pts total
After: 215 × 0.95 = 204.3 pts total

Reduction: 10.7 points (5% compression)

Rationale: Defensive grind detected → prevent over-prediction
```

**Scenario 3: Moderate Stacking**
```
Projected total: 228 pts
Betting line: 225 pts
High-scoring signals: 3 (pace high, offense strong, defense average)
Other factors: Normal

Compression factors:
  Signal stacking: 0.97 (3 signals)

Master compression: 0.97

Before: 228 pts total
After: 228 × 0.97 = 221.2 pts total

Reduction: 6.8 points (3% compression)

Rationale: Moderate stacking → mild dampening
```

**Scenario 4: No Compression Needed**
```
Projected total: 218 pts
Betting line: 220 pts
High-scoring signals: 1 (only pace high)
Pace volatility: Normal
Tempo/Defense: Normal

Compression factors: All 1.0 (no triggers)

Master compression: 1.0

Before: 218 pts total
After: 218 × 1.0 = 218 pts total

Reduction: 0 points

Rationale: No inflation risk → no compression applied
```

### Compression Trigger Summary:

| Trigger | Condition | Compression | When Applied |
|---------|-----------|-------------|--------------|
| 4 high signals | All offensive indicators firing | 0.94 (-6%) | Rare shootouts |
| 3 high signals | Most indicators firing | 0.97 (-3%) | Common in fast games |
| Defensive battle | Low pace + elite defenses | 0.95 (-5%) | Grind games |
| Way above line | Proj 8+ pts above betting line | 0.96 (-4%) | Model overconfident |
| Extreme total | Projection >240 pts | 0.96 (-4%) | Unrealistic totals |
| High pace volatility | Avg volatility <0.92 | 0.97 (-3%) | Unreliable pace |

**Maximum Compression:** 0.84 (when all factors stack) = 16% reduction

**Expected Effect:** Prevents 5-20 point over-prediction in high-scoring projections.

### Why This Works:

1. **Multiplicative stacking prevention:** When all high-scoring signals align, they compound the error. Compression prevents this.

2. **Context-aware:** Only applies when there's genuine inflation risk (high totals, many signals, above betting line).

3. **Final safeguard:** Applied AFTER all other adjustments, catches any remaining over-prediction.

4. **Never over-compresses:** Minimum compression is 1.0 (no reduction), never penalizes normal predictions.

5. **Real-world calibration:** Betting line comparison provides market reality check.

---

## Version History

### v4.6 - Opponent Matchup Stats (Current)
**Major Changes:**
- Added **Opponent Matchup Adjustments** - team offense vs opponent defense analysis
- Database extended with 59 opponent stat columns (what teams ALLOW opponents to do)
- New module: `opponent_matchup_stats.py` for matchup-based scoring adjustments
- AI Coach integration for opponent-aware game analysis
- Automated ETL pipeline for opponent stats computation

**Key Benefits:**
- FG% matchup analysis: compares team shooting vs what opponent allows (±5 pts cap)
- 3P% matchup analysis: volume-adjusted 3-point advantage/disadvantage (±4 pts cap)
- Pace matchup analysis: team tempo vs opponent pace allowed (±3 pts cap)
- Total adjustment capped at ±10 pts per team to prevent extreme swings
- 100% data coverage (896/896 games for 2025-26 season)
- Symmetrical validation: Team A's stats = Team B's opponent stats
- **Expected impact:** More accurate predictions for matchup-specific offensive/defensive advantages

**Implementation:**
- Database migration: 28 columns in team_game_logs, 31 in team_season_stats
- Possession formula: FGA + 0.44×FTA - OREB + TOV
- Zero manual intervention required for future data syncs
- AI Coach now explains matchup-based adjustments in game reviews

### v4.5 - Bias Correction & Anti-Inflation
**Major Changes:**
- Added **Pace Volatility & Contextual Dampening** - reduces over-reliance on volatile pace
- Added **Enhanced Defensive Adjustments** - MORE AGGRESSIVE DRTG multipliers (elite defenses now -9% to -11%)
- Added **Scoring Compression & Bias Correction** - final anti-inflation safeguard
- Double-strong-defense penalty for defensive battles
- Master compression factor combining 5 inflation indicators

**Key Benefits:**
- Pace volatility factor (0.85-1.05x) prevents over-trusting inconsistent tempo
- Contextual pace dampening for high turnovers/FT rate
- Elite defenses (rank 1-5) now apply -9% to -11% suppression (was -6%)
- Both elite defenses trigger additional -4% penalty
- Signal stacking compression prevents 6-16% inflation when all indicators align
- Defensive battle detection (low pace + elite D) caps at -5%
- Betting line comparison provides market reality check
- **Expected total impact:** 5-20 point reduction in high-scoring over-predictions

### v4.4 - Defense Quality + Road Penalty
**Major Changes:**
- Added **Defense Quality Adjustment** - supplementary rank-based defense adjustment
- Added **Road Penalty** - non-linear penalty for away teams with poor road records
- Provides additional defensive context beyond dynamic defense adjustment
- Penalizes away teams based on road performance with tiered multipliers

**Key Benefits:**
- Elite defenses (rank 1-10) apply -6.0 to -4.0 pts penalty with linear interpolation
- Bad defenses (rank 20-30) provide +3.0 to +5.0 pts bonus with linear interpolation
- Average defenses (rank 11-19) apply no adjustment (0.0 pts)
- Works alongside dynamic defense adjustment for comprehensive defensive impact
- Road penalty uses non-linear scaling (1.0x, 1.2x, 1.4x multipliers by tier)
- Catastrophic road teams (<30% win rate) face up to -7.0 pts penalty
- Good road teams (≥50%) face no penalty
- More accurate modeling of home/road performance splits

### v4.3 - Advanced Pace Calculation
**Major Changes:**
- Added **Advanced Pace Calculation** - sophisticated multi-factor pace projection
- Replaces simple season pace average with context-aware formula
- Blends season (60%) + recent (40%) pace for each team
- Accounts for pace mismatches (slow teams drag games down)
- Accounts for turnover-driven pace increases (transition basketball)
- Accounts for free throw rate impacts (clock stoppages)
- Accounts for elite defense effects (defensive grind)
- Clamps to realistic NBA range (92-108)

**Key Benefits:**
- Correctly identifies high-turnover games (+0.3 pace per turnover above 15)
- Correctly identifies FT-heavy games (-0.1 pace per 1% FT rate above 25%)
- Handles pace mismatches (-1 to -2 penalty when one team much slower)
- Handles elite defense games (-1.5 penalty for defensive grind)
- Captures recent pace trends (40% weight to last 5 games)
- Estimated 5-8% improvement in pace prediction accuracy

### v4.2 - Dynamic 3PT Shootout Adjustment
**Major Changes:**
- Added **Dynamic 3PT Shootout Adjustment** - advanced multi-factor 3PT scoring system
- Replaces old disabled shootout detection with context-aware calculation
- Considers team talent, opponent defense, recent form, pace, and rest
- Variable 0-15+ pts per team based on shootout environment
- Successfully identifies high-scoring games like LAL/BOS, DEN/ATL, UTA/NYK

**Key Benefits:**
- Elite shooters vs weak defense in fast-paced games get proper 8-12 pt boost
- Average conditions get 0 pts (no inflation)
- Hot shooting streaks properly rewarded
- Fatigue (B2B) reduces shooting bonus appropriately
- No negative penalties (only adds points in true shootout conditions)

### v4.1 - Dynamic Home Court Advantage
**Major Changes:**
- Added **Dynamic Home Court Advantage** (0-6 points based on home/road records + momentum)
- Replaces static 2.5-point home advantage with context-aware calculation
- Considers home team's home record, opponent's road record, and recent home momentum

**Key Benefits:**
- Elite home teams vs weak road teams get proper 5-6 point advantage
- Weak home teams vs strong road teams get minimal 0-1 point advantage
- Average matchups maintain ~2.5 point baseline
- More accurate reflection of actual home court impact

### v4.0 - Dynamic Defense + Smart Baseline
**Major Changes:**
- Added **Smart Baseline** that blends season + recent form with adaptive weights
- Implemented **Dynamic Defense** that scales impact based on offensive form
- Added **Matchup Adjustments** for specific game scenarios
- Added **Fatigue/Rest Adjustment** based on back-to-backs and extreme games
- **Disabled Recent Form step** (integrated into Smart Baseline)
- **Disabled Shootout Bonus** (based on live results showing inflation)

**Key Benefits:**
- Eliminates double-counting of recent form
- Hot offenses not over-suppressed by elite defenses
- Cold offenses properly penalized even vs weak defenses
- More context-aware predictions

### v3.0 - Defense-First Architecture
**Changes:**
- Changed from defense-first to equal-weight sequential
- Increased 3PT weight from 25% to 50%
- Made shootout detection more aggressive
- Increased shootout bonuses from +4/+8 to +6/+12

### v2.0 - Early Iterations
**Initial implementation of:**
- Pace adjustments
- Defensive tier analysis
- Recent form weighting
- Basic shootout detection

---

## Complete Pipeline Example

### Game: BOS vs NYK (Line: 230.5)

**Smart Baseline:**
```
BOS: Season 115.3, Recent 122.0, ORTG Δ+0.0
  → normal trend (70/30) = 117.3 PPG
NYK: Season 120.2, Recent 119.8, ORTG Δ+0.0
  → minimal trend (80/20) = 120.1 PPG
```

**STEP 1 - Advanced Pace:**
```
Game pace: 96.0 (slow)
Multiplier: 0.9879x
BOS: 117.3 → 115.9
NYK: 120.1 → 118.7
```

**STEP 1B - Pace Volatility & Dampening (NEW!):**
```
BOS pace volatility: σ=2.1 → factor 1.0 (normal)
NYK pace volatility: σ=3.2 → factor 0.92 (medium vol)
Combined TOV%: 14.2%, FT rate: 0.25 → dampener 1.0

BOS: 115.9 × 1.0 × 1.0 = 115.9
NYK: 118.7 × 0.92 × 1.0 = 109.2

Effect: NYK pace less reliable → 9.5 pt reduction
```

**STEP 2 - Turnovers:**
```
(Integrated into pace calculation)
```

**STEP 3 - Defense (Dynamic):**
```
BOS offense: hot (+6.7 PPG)
  vs NYK defense #14 → multiplier: 0.40x
  Base: -6.8 pts → Applied: -0.8 pts

NYK offense: normal (-0.4 PPG)
  vs BOS defense #19 → multiplier: 1.00x
  Base: -21.2 pts → Applied: -6.4 pts

BOS: 115.9 → 115.1
NYK: 109.2 → 102.8
```

**STEP 3B - Enhanced Defense (NEW!):**
```
BOS faces NYK defense (rank #14):
  Base multiplier: 0.97 (above avg)
  Trend: 0.0 → modifier 1.0
  Final: 115.1 × 0.97 = 111.6

NYK faces BOS defense (rank #19):
  Base multiplier: 0.99 (average)
  Trend: 0.0 → modifier 1.0
  Final: 102.8 × 0.99 = 101.8

BOS: 111.6
NYK: 101.8
```

**STEP 4 - Defense Quality:**
```
(Supplementary adjustment - included in Step 3B)
```

**STEP 5 - Home Court Advantage (Dynamic):**
```
BOS home record: 15-8 (0.652 win%)
NYK road record: 10-13 (0.435 win%)
BOS last 3 home games: 2/3 wins

Home_Record_Multiplier = (0.652 - 0.500) * 3 = 0.456
Road_Weakness_Multiplier = (0.500 - 0.435) * 2 = 0.130
Home_Momentum = +1.0

HCA = 2.5 * (1 + 0.456 + 0.130) + 1.0
    = 2.5 * 1.586 + 1.0
    = 3.965 + 1.0
    = 4.965 → 5.0 pts to BOS

BOS: 111.6 + 5.0 = 116.6
NYK: 101.8
```

**STEP 6 - Road Penalty:**
```
NYK road record: 10-13 (0.435 win%)
Below 50% by 0.065 → penalty -0.65 pts
Tier: Below-average (1.0x multiplier)

NYK: 101.8 - 0.7 = 101.1
```

**STEP 7 - Matchup Adjustments:**
```
No matchup adjustments triggered
```

**STEP 8 - 3PT Shootout:**
```
No significant shootout indicators
(Normal 3PT conditions)
```

**STEP 9 - Fatigue:**
```
NYK on back-to-back (played yesterday)
Penalty: -4.0 pts from total
Total before: 217.7
Total after: 213.7
```

**STEP 10 - Scoring Compression (NEW!):**
```
Projected total: 213.7
Betting line: 230.5
Signals: 0 high (slow pace, avg defense)
Pace volatility: avg 0.96 (normal)

Compression factors:
  Signal stacking: 1.0 (no high signals)
  Defensive battle: 1.0 (not detected)
  Line difference: 1.0 (below line, no compression)
  High total: 1.0 (<235)
  Pace volatility: 1.0 (normal)

Master compression: 1.0

Final: 213.7 × 1.0 = 213.7

Effect: No inflation detected → no compression applied
```

**Final Prediction:**
```
Home (BOS): 116.6
Away (NYK): 97.1
Total: 213.7

Line: 230.5
Difference: -16.8
Recommendation: STRONG UNDER

Key Factors:
- NYK pace volatility reduced projection by 9.5 pts
- Enhanced defense adjustments reduced total by 7.9 pts
- NYK fatigue penalty -4.0 pts
- Combined bias correction: ~21.4 pt reduction from v4.4 baseline
```

---
