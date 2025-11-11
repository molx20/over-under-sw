# Quick Start Guide

Get the NBA Over/Under app running in 5 minutes!

## Step 1: Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt
```

## Step 2: Run Locally

```bash
# Start the development server
npm run dev
```

The app will open at `http://localhost:5173`

## Step 3: Test the API (Optional)

To test the Python API functions locally:

```python
# In a Python shell
from api.utils.nba_data import get_todays_games, get_team_stats
from api.utils.prediction_engine import predict_game_total

# Get today's games
games = get_todays_games()
print(f"Found {len(games)} games today")

# Get team stats (example: Lakers - team_id: 1610612747)
lakers_stats = get_team_stats(1610612747)
print(lakers_stats)
```

## Step 4: Deploy to Vercel (FREE)

### First Time Setup

1. **Install Vercel CLI** (optional, but recommended)
   ```bash
   npm i -g vercel
   ```

2. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

3. **Deploy via Vercel Dashboard**
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repo
   - Click "Deploy" (no configuration needed!)

### OR Deploy via CLI

```bash
vercel
# Follow the prompts
# First deployment will ask for configuration - accept defaults
```

## Common Team IDs (for testing)

- Lakers: 1610612747
- Warriors: 1610612744
- Celtics: 1610612738
- Heat: 1610612748
- Nets: 1610612751
- Knicks: 1610612752
- 76ers: 1610612755
- Bucks: 1610612749
- Bulls: 1610612741
- Mavericks: 1610612742

## Troubleshooting

### "Module not found" errors
```bash
rm -rf node_modules package-lock.json
npm install
```

### Python import errors
```bash
pip install --upgrade nba_api flask flask-cors
```

### API rate limiting
The NBA API has rate limits. If you see errors:
- Wait a few seconds between requests
- The app includes built-in delays (0.6s between calls)
- Consider implementing caching for production

### No games showing
- Check if there are NBA games scheduled today
- Try a different date using the date picker (once implemented)
- Check browser console for error messages

## Next Steps

1. **Customize the algorithm**: Edit `api/utils/prediction_engine.py`
2. **Add new features**: Check README.md for enhancement ideas
3. **Improve accuracy**: Incorporate more advanced statistics
4. **Add betting lines**: Integrate with an odds API

## Development Tips

- **Hot Reload**: Changes to React files auto-reload
- **Dark Mode**: Toggle with the button in header
- **Responsive Design**: Test on mobile with browser DevTools
- **API Caching**: Team stats are cached for 1 hour to reduce API calls

## Production Checklist

- [ ] Test all features locally
- [ ] Verify predictions are reasonable
- [ ] Check mobile responsiveness
- [ ] Test dark mode
- [ ] Add error handling
- [ ] Set up analytics (optional)
- [ ] Configure custom domain (optional)
- [ ] Set up monitoring (optional)

## Support

- Check the main [README.md](./README.md) for detailed documentation
- Review [nba_api documentation](https://github.com/swar/nba_api)
- Open an issue on GitHub for bugs

---

**Happy predicting! 🏀**
