# NBA Over/Under Predictions

A modern web application for predicting NBA game totals (Over/Under) using real-time statistics and advanced analytics. Built with React, Python, and the nba_api library.

## Features

- **Daily Game Predictions**: View all NBA games with Over/Under predictions
- **Advanced Analytics**: Predictions based on pace, efficiency, home/away splits, and recent form
- **Detailed Breakdowns**: Click any game for in-depth statistical analysis
- **AI-Powered Post-Game Analysis**: Upload box score screenshots for automated game reviews using OpenAI Vision API
- **Model Coach**: Daily AI summaries analyzing prediction accuracy and model performance
- **Confidence Ratings**: Each prediction includes a confidence percentage
- **Dark Mode**: Toggle between light and dark themes
- **Mobile Responsive**: Works seamlessly on all devices
- **Auto-Refresh**: Data updates every 30 minutes
- **Filtering & Sorting**: Sort by confidence, time, or alphabetically

## Tech Stack

- **Frontend**: React 18 + Vite
- **Styling**: Tailwind CSS
- **Backend**: Python Flask
- **Data Source**: nba_api library
- **AI**: OpenAI Vision API (gpt-4.1-mini) for screenshot analysis
- **Deployment**: Railway
- **Routing**: React Router
- **Database**: SQLite

## Project Structure

```
nba-over-under/
├── api/                          # Python backend API
│   ├── games.py                  # Endpoint for game list with predictions
│   ├── game_detail.py            # Endpoint for detailed game analysis
│   └── utils/
│       ├── nba_data.py           # NBA API wrapper functions
│       └── prediction_engine.py  # Prediction algorithm
├── src/                          # React frontend
│   ├── components/
│   │   ├── GameCard.jsx          # Game summary card
│   │   ├── Header.jsx            # App header with dark mode
│   │   └── StatsTable.jsx        # Team stats comparison
│   ├── pages/
│   │   ├── Home.jsx              # Main page with game list
│   │   └── GamePage.jsx          # Detailed game analysis
│   ├── utils/
│   │   └── api.js                # API client functions
│   ├── App.jsx                   # Root component
│   ├── main.jsx                  # Entry point
│   └── index.css                 # Global styles
├── package.json                  # Node dependencies
├── requirements.txt              # Python dependencies
├── vercel.json                   # Vercel configuration
└── vite.config.js                # Vite configuration
```

## Local Development

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd nba-over-under
   ```

2. **Install frontend dependencies**
   ```bash
   npm install
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit the `.env` file and add your OpenAI API key:
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   ```

   Get your API key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

### Running Locally

1. **Start the frontend development server**
   ```bash
   npm run dev
   ```
   The app will be available at `http://localhost:5173`

2. **Test Python API functions** (optional)
   ```bash
   # In a Python shell or Jupyter notebook
   from api.utils.nba_data import get_todays_games
   games = get_todays_games()
   print(games)
   ```

## Deployment to Railway

Railway is a modern deployment platform that handles both Python backends and React frontends seamlessly.

#### One-Time Setup

1. **Create a GitHub repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Sign up for Railway**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub

3. **Deploy the project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will automatically detect Python and deploy

4. **Configure environment variables**
   - In your Railway project dashboard
   - Click on "Variables"
   - Add the following variable:
     - `OPENAI_API_KEY`: Your OpenAI API key (get it at [platform.openai.com/api-keys](https://platform.openai.com/api-keys))
   - Redeploy your service after adding the variable

#### Features on Railway

- Automatic deploys on git push
- Free tier includes 500 hours/month
- Built-in database support (if needed)
- Custom domains
- Environment variable management

## How the Prediction Algorithm Works

### Data Sources

The app fetches real-time data from the NBA API:
- Team traditional stats (PPG, FG%, 3P%)
- Advanced metrics (pace, offensive/defensive ratings)
- Home/Away splits
- Recent game results (last 5-10 games)

### Prediction Process

1. **Pace Calculation**
   - Averages the pace of both teams
   - Weights home team slightly higher (52% vs 48%)
   - Determines expected possessions per game

2. **Scoring Projection**
   - Combines team offense with opponent defense
   - Adjusts for pace (normalized to 100 possessions)
   - Adds home court advantage (+2.5 points for home team)

3. **Confidence Score**
   - Based on difference from betting line
   - Factors in recent form consistency
   - Considers pace variance between teams
   - Adjusted for injury impact (when available)

4. **Recommendation**
   - **OVER**: Predicted total > betting line by 3+ points
   - **UNDER**: Predicted total < betting line by 3+ points
   - **NO BET**: Difference < 3 points

## API Endpoints

### GET /api/games
Get all games for a specific date with predictions

**Query Parameters:**
- `date` (optional): Date in YYYY-MM-DD format (defaults to today)

**Response:**
```json
{
  "success": true,
  "date": "2024-01-15",
  "games": [...],
  "count": 10,
  "last_updated": "2024-01-15T18:30:00"
}
```

### GET /api/game_detail
Get detailed analysis for a specific game

**Query Parameters:**
- `home_team_id`: Home team ID (required)
- `away_team_id`: Away team ID (required)
- `betting_line`: Current betting line (optional)

**Response:**
```json
{
  "success": true,
  "prediction": {...},
  "home_stats": {...},
  "away_stats": {...},
  "home_recent_games": [...],
  "away_recent_games": [...]
}
```

## Current Season

This app is configured for the **2025-26 NBA season**. Once the season begins, all live game data and predictions will be available automatically.

## Future Enhancements

- [ ] Integration with live odds APIs (The Odds API, etc.)
- [ ] Historical accuracy tracking and display
- [ ] Player injury impact analysis
- [ ] Live score updates during games
- [ ] Export predictions to CSV
- [ ] User accounts and prediction history
- [ ] Advanced filtering (by team, conference, etc.)
- [ ] Machine learning model for improved predictions
- [ ] Head-to-head matchup history
- [ ] Weather impact (for outdoor games if applicable)

## Rate Limiting & Caching

The NBA API has rate limits. The app implements:
- 0.6-second delay between API calls
- In-memory caching of team stats (1-hour TTL)
- For production, consider using Vercel KV (Redis) for caching

## Customization

### Adjust Prediction Algorithm

Edit `api/utils/prediction_engine.py`:
- Modify home court advantage value
- Adjust pace weighting
- Change confidence thresholds

### Modify UI Theme

Edit `tailwind.config.js`:
- Change primary colors
- Adjust breakpoints
- Add custom utilities

### Add New Statistics

1. Fetch additional data in `api/utils/nba_data.py`
2. Update prediction algorithm in `api/utils/prediction_engine.py`
3. Display new stats in React components

## Troubleshooting

### API Rate Limiting
If you see errors about rate limiting:
- Increase delay between calls in `nba_data.py`
- Implement more aggressive caching
- Consider using Vercel KV for persistent caching

### Build Errors
```bash
# Clear cache and reinstall
rm -rf node_modules dist
npm install
npm run build
```

### Python Dependencies
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - feel free to use this project for personal or commercial purposes.

## Acknowledgments

- [nba_api](https://github.com/swar/nba_api) for NBA statistics
- [Vercel](https://vercel.com) for free hosting
- Inspired by [propsmadness.com](https://propsmadness.com)

## Support

For issues or questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review NBA API documentation

---

**Note**: This app is for entertainment and educational purposes. Always gamble responsibly and within your means. This tool does not guarantee winning predictions.
