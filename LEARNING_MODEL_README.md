# Self-Learning Team Ratings Model

A lightweight, transparent prediction system with online learning capabilities.

## Overview

This feature adds a simple team-ratings model that learns from actual game results. It runs **alongside** (not replacing) the existing complex prediction system.

### Model Formula

```
PTS_home_hat = base + HCA + Off[home] - Def[away]
PTS_away_hat = base - HCA + Off[away] - Def[home]
```

**Parameters:**
- `base`: Base points per team (default: 100)
- `HCA`: Home court advantage (default: +2)
- `Off[team]`: Team offensive rating (starts at 0)
- `Def[team]`: Team defensive rating (starts at 0)

### Learning Updates

After each game, ratings update using gradient descent (η = 0.02):

```python
err_h = pts_home_final - PTS_home_hat
err_a = pts_away_final - PTS_away_hat

Off[home] += η * err_h
Def[away] -= η * err_h
Off[away] += η * err_a
Def[home] -= η * err_a

# All ratings clamped to [-20, +20]
```

---

## Setup

### 1. Environment Variables (Vercel Dashboard)

Go to Vercel Dashboard → Project Settings → Environment Variables:

```bash
GH_TOKEN=<your-github-personal-access-token>
GH_REPO=molx20/over-under-sw
GH_MODEL_PATH=api/data/model.json
```

**Important:** `GH_TOKEN` needs `repo` scope to commit files.

### 2. Deploy to Vercel

```bash
cd "/Users/malcolmlittle/NBA OVER UNDER SW"
git add -A
git commit -m "Add self-learning team ratings feature"
vercel --prod
```

---

## API Usage

### GET /api/predict

Get prediction for a matchup using current team ratings.

**Query Parameters:**
- `home` (required): Home team tricode (e.g., `BOS`)
- `away` (required): Away team tricode (e.g., `LAL`)

**Example:**

```bash
curl "https://nba-over-under-sw.vercel.app/api/predict?home=BOS&away=LAL"
```

**Response:**

```json
{
  "success": true,
  "home_team": "BOS",
  "away_team": "LAL",
  "home_pts": 102.0,
  "home_pts_rounded": 102,
  "away_pts": 98.0,
  "away_pts_rounded": 98,
  "predicted_total": 200.0,
  "model_version": "1.0"
}
```

---

### POST /api/feedback

Submit actual game result to update team ratings.

**Headers:**
- `Content-Type: application/json`

**Body:**

```json
{
  "home": "BOS",
  "away": "LAL",
  "home_pts_final": 110,
  "away_pts_final": 95
}
```

**Example:**

```bash
curl -X POST https://nba-over-under-sw.vercel.app/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "home": "BOS",
    "away": "LAL",
    "home_pts_final": 110,
    "away_pts_final": 95
  }'
```

**Response:**

```json
{
  "success": true,
  "message": "Model updated successfully",
  "updated_ratings": {
    "BOS": {"off": 0.16, "def": 0.06},
    "LAL": {"off": -0.06, "def": -0.16}
  },
  "old_ratings": {
    "BOS": {"off": 0, "def": 0},
    "LAL": {"off": 0, "def": 0}
  },
  "errors": {
    "home": 8.0,
    "away": -3.0
  },
  "predictions": {
    "home_predicted": 102.0,
    "away_predicted": 98.0,
    "home_actual": 110,
    "away_actual": 95
  },
  "learning_rate": 0.02,
  "github_committed": true,
  "commit_sha": "abc123...",
  "commit_url": "https://github.com/molx20/over-under-sw/commit/abc123..."
}
```

---

## Complete Workflow Example

### 1. Get initial prediction

```bash
curl "https://nba-over-under-sw.vercel.app/api/predict?home=BOS&away=LAL"
```

**Result:** `BOS 102, LAL 98` (baseline, no learning yet)

---

### 2. Watch the actual game

Let's say the actual result was: **BOS 110, LAL 95**

---

### 3. Submit feedback

```bash
curl -X POST https://nba-over-under-sw.vercel.app/api/feedback \
  -H "Content-Type: application/json" \
  -d '{"home":"BOS","away":"LAL","home_pts_final":110,"away_pts_final":95}'
```

**What happens:**
- Model calculates errors: `BOS +8 better than expected`, `LAL -3 worse`
- Updates ratings:
  - `BOS Off += 0.16` (offense stronger)
  - `BOS Def -= 0.06` (defense slightly weaker, from LAL error)
  - `LAL Off -= 0.06` (offense weaker)
  - `LAL Def -= 0.16` (defense worse)
- Commits updated `model.json` to GitHub
- Returns commit SHA for tracking

---

### 4. Get updated prediction

```bash
curl "https://nba-over-under-sw.vercel.app/api/predict?home=BOS&away=LAL"
```

**Result:** `BOS 102.32, LAL 97.88` (adjusted based on learning!)

---

## Team Tricodes

All 30 NBA teams are supported:

```
ATL, BOS, BKN, CHA, CHI, CLE, DAL, DEN, DET, GSW,
HOU, IND, LAC, LAL, MEM, MIA, MIL, MIN, NOP, NYK,
OKC, ORL, PHI, PHX, POR, SAC, SAS, TOR, UTA, WAS
```

---

## Tuning Parameters

Edit `api/data/model.json` to adjust:

```json
{
  "parameters": {
    "base": 100,           // Base points per team
    "hca": 2,              // Home court advantage
    "learning_rate": 0.02  // How fast the model learns (0.01-0.05 recommended)
  }
}
```

**Tips:**
- Smaller `learning_rate` (0.01) = slower, more stable learning
- Larger `learning_rate` (0.05) = faster adaptation, but more volatile
- Ratings are clamped to `[-20, +20]` to prevent runaway values

---

## Architecture

```
┌─────────────────────────────────────┐
│   Existing Prediction System        │
│   (games.py + prediction_engine.py) │
│   [NOT MODIFIED]                    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│   NEW: Team Ratings Model           │
│   (api/utils/team_ratings_model.py) │
│   - Simple rating calculation       │
│   - Online learning updates         │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│   NEW: GitHub Persistence           │
│   (api/utils/github_persistence.py) │
│   - Commits to GitHub after updates│
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│   NEW: API Endpoints                │
│   GET  /api/predict                 │
│   POST /api/feedback                │
└─────────────────────────────────────┘
```

---

## Cost

**$0** - Uses only:
- GitHub (free repo storage)
- Vercel (free tier serverless)
- No paid APIs or databases

---

## Maintenance

The model automatically commits to GitHub after each feedback submission, so:

✅ Model state persists across deployments
✅ Full version history in Git
✅ Can manually edit `api/data/model.json` if needed
✅ Can rollback to previous ratings via Git

---

## Limitations

- Simple linear model (no interactions, no situational factors)
- Needs ~20-30 games per team to converge
- No player-level data (team-level only)
- Ratings reset when manually editing `model.json`

---

## Future Enhancements (Optional)

```python
# In api/data/model.json "parameters":
"base_learning_rate": 0.001  # Allow base to drift slightly toward average totals
```

```python
# In team_ratings_model.py update_ratings():
avg_total = (home_pts_final + away_pts_final) / 2
base_error = avg_total - (2 * base)
base += base_learning_rate * base_error
```

This allows the `base` parameter to adjust if league scoring trends change over time.

---

## Support

For issues or questions:
- Check Vercel logs: `vercel logs --follow`
- Verify environment variables are set
- Test locally first: `python3 api/utils/team_ratings_model.py`

