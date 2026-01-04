# Quick Start Guide - NBA Over/Under Predictions

## ✅ Setup Complete!

All dependencies have been installed successfully:
- ✅ Node.js packages installed (React, Vite, Tailwind CSS)
- ✅ Python packages installed (nba_api, Flask, pandas)
- ✅ NBA API integration tested and working

## 🚀 Running the Application

### Option 1: Development Mode (Recommended)

**Start the frontend:**
```bash
npm run dev
```

The app will open at **http://localhost:5173**

**Note:** The frontend includes a proxy to handle API calls, so you don't need to run a separate backend server during development.

### Option 2: Testing API Directly

**Start the Flask API server:**
```bash
python3 api/games.py
```

The API will run at **http://localhost:5000**

**Test the API:**
```bash
# Get today's games (may be empty during offseason)
curl http://localhost:5000/api/games

# Get detailed matchup (Nets vs Lakers)
curl "http://localhost:5000/api/game_detail?home_team_id=1610612751&away_team_id=1610612747&betting_line=220.5"
```

## 📝 Important Notes

### Season Data
The app is configured for the **2025-26 NBA season**. All data will be pulled from this season once games begin.

### Today's Games
If you see "No games today", this is normal when:
- The 2025-26 season hasn't started yet
- It's an off-day with no scheduled games
- It's the NBA offseason (typically April-October)

The app will automatically show live games once the season starts!

### Rate Limiting
The NBA API has rate limits. The app includes:
- 600ms delay between API calls
- Automatic caching (1 hour for stats)
- Error handling

## 🧪 Testing

### Quick Test (Verify API Works)
```bash
python3 api/quick_test.py
```

### Full Test Suite (9 tests)
```bash
python3 api/test_nba_api.py
```

## 📊 How to Use

### 1. View Today's Games
- Open http://localhost:5173
- See all NBA games with predictions
- Sort by confidence, time, or alphabetically
- Filter by minimum confidence level

### 2. View Game Details
- Click any game card
- See detailed statistical breakdown
- View team stats comparison
- Check recent game history
- Analyze prediction factors

### 3. Understand Predictions
- **OVER** = Predicted total > betting line by 4+ points
- **UNDER** = Predicted total < betting line by 4+ points
- **NO BET** = Within 4 points of the line
- **Confidence** = 40-95% based on multiple factors

## 🎨 Features

- ✅ Real-time NBA data from nba_api
- ✅ Advanced prediction algorithm (pace, efficiency, form)
- ✅ Dark mode toggle
- ✅ Mobile responsive design
- ✅ Auto-refresh every 30 minutes
- ✅ Confidence ratings
- ✅ Detailed game breakdowns

## 🔧 Troubleshooting

### "No games today"
**Solution:** Normal during offseason. Try testing with specific team matchups using the game detail API:
```bash
curl "http://localhost:5000/api/game_detail?home_team_id=1610612751&away_team_id=1610612747"
```

### API errors
**Solution:** The NBA API has rate limits. Wait 60 seconds and try again. Caching prevents most issues.

### "pip: command not found"
**Solution:** Use `pip3` instead of `pip` on Mac:
```bash
pip3 install -r requirements.txt
```

### Port already in use
**Solution:** Kill the process using the port:
```bash
lsof -ti:5173 | xargs kill  # Frontend
lsof -ti:5000 | xargs kill  # Backend
```

## 📚 Common Team IDs

For testing predictions:
```
Lakers: 1610612747
Warriors: 1610612744
Celtics: 1610612738
Nets: 1610612751
Knicks: 1610612752
Heat: 1610612748
76ers: 1610612755
Bucks: 1610612749
Bulls: 1610612741
Mavericks: 1610612742
```

## 🚀 Deploy to Production

### Railway Deployment

1. **Push to GitHub:**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

2. **Deploy on Railway:**
- Go to [railway.app](https://railway.app)
- Click "New Project"
- Import your GitHub repo
- Configure environment variables
- Deploy

Railway will automatically build and deploy your backend!

## 📖 Documentation

- **README.md** - Complete project documentation
- **NBA_API_SETUP.md** - Detailed API setup guide
- **QUICKSTART.md** - 5-minute quick start

## 💡 Next Steps

1. **Run the app:** `npm run dev`
2. **Explore the interface**
3. **Test predictions** with different teams
4. **Customize the algorithm** in `api/utils/prediction_engine.py`
5. **Deploy to Railway** for backend hosting

---

**Need Help?**
- Check the main README.md for detailed docs
- Review NBA_API_SETUP.md for API details
- Run `python3 api/quick_test.py` to verify setup

**Enjoy predicting NBA game totals! 🏀**
