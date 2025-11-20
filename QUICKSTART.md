# Self-Learning Feature - Quick Start

## 🚀 Get Started in 3 Steps

### 1️⃣ Save a Pre-Game Prediction

Before a game starts, save your model's prediction:

```bash
curl -X POST https://your-app.railway.app/api/save-prediction \
  -H "Content-Type: application/json" \
  -d '{"game_id": "0022500263", "home_team": "POR", "away_team": "CHI"}'
```

**You'll get back:**
```json
{
  "success": true,
  "prediction": {
    "home": 110.5,
    "away": 105.2,
    "total": 215.7
  }
}
```

### 2️⃣ Submit the Sportsbook Line

Enter the over/under line from ESPN, FanDuel, DraftKings, etc:

```bash
curl -X POST https://your-app.railway.app/api/submit-line \
  -H "Content-Type: application/json" \
  -d '{"game_id": "0022500263", "sportsbook_total_line": 218.5}'
```

### 3️⃣ Run Learning After the Game

Once the game finishes with status "Final":

```bash
curl -X POST https://your-app.railway.app/api/run-learning \
  -H "Content-Type: application/json" \
  -d '{"game_id": "0022500263"}'
```

**You'll get back:**
```json
{
  "success": true,
  "actual_total": 220.0,
  "pred_total": 215.7,
  "sportsbook_line": 218.5,
  "model_error": 4.3,
  "line_error": 1.5,
  "model_beat_line": false,
  "total_bias_update": {
    "old": 0.0,
    "new": 0.03,
    "adjustment": 0.03
  }
}
```

---

## 📊 Check Your Performance

After 10+ games, query your stats:

```bash
sqlite3 api/data/predictions.db "
SELECT
    COUNT(*) as games,
    ROUND(AVG(model_abs_error), 2) as avg_model_error,
    ROUND(AVG(line_abs_error), 2) as avg_line_error,
    ROUND(SUM(CASE WHEN model_beat_line = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as model_win_rate
FROM game_predictions
WHERE learning_completed_at IS NOT NULL;
"
```

---

## 🔗 Getting Game IDs

To get today's games and their IDs:

```bash
curl -s https://your-app.railway.app/api/games | python3 -m json.tool | grep -E "(game_id|home_team|away_team)"
```

---

## 📁 Where Is Everything?

- **Database**: `api/data/predictions.db`
- **Model**: `api/data/model.json`
- **Full Guide**: `SELF_LEARNING_GUIDE.md`
- **API Docs**: `API_REFERENCE.md`
- **Summary**: `IMPLEMENTATION_SUMMARY.md`

---

## 🎯 What to Expect

| After | Avg Error | Win Rate vs Line |
|-------|-----------|------------------|
| 10 games | 10-15 pts | 30-40% |
| 50 games | 7-10 pts | 40-48% |
| 200 games | 5-7 pts | 48-52% |

**Goal**: Get your model to beat the closing line 50%+ of the time over hundreds of games.

---

## ❓ Troubleshooting

**"No prediction found"**
→ Did you save the prediction first? (Step 1)

**"Game is not finished yet"**
→ Wait for game status = "Final" before running learning

**GitHub commit failed**
→ Normal without `GH_TOKEN` - model still updates locally

---

## 🚢 Deploy to Railway

```bash
git add .
git commit -m "Add self-learning prediction feature"
git push
```

Railway will automatically deploy. Your SQLite database will persist across restarts.

---

## 📞 Need Help?

- **Usage Guide**: See `SELF_LEARNING_GUIDE.md`
- **API Reference**: See `API_REFERENCE.md`
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`

---

**That's it! Start learning from your predictions today.** 🎉
