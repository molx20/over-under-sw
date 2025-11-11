# NBA API Setup & Testing Guide

This guide will help you set up and test the nba_api integration.

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `nba_api==1.4.1` - NBA statistics API
- `pandas==2.1.0` - Data manipulation
- `Flask==3.0.0` - Web framework
- `Flask-Cors==4.0.0` - CORS support
- Other dependencies

### 2. Verify Installation

```bash
python -c "from nba_api.stats.static import teams; print('nba_api installed successfully!')"
```

## Testing the NBA API Integration

### Quick Test

Run the comprehensive test suite:

```bash
python api/test_nba_api.py
```

This will test:
1. ✓ Get all NBA teams
2. ✓ Get team IDs by name
3. ✓ Get team traditional stats (PPG, FG%, etc.)
4. ✓ Get advanced stats (ORTG, DRTG, PACE)
5. ✓ Get opponent stats
6. ✓ Get recent games
7. ✓ Get today's games
8. ✓ Get full matchup data
9. ✓ Verify caching works

### Manual Testing

#### Test 1: Get All Teams

```python
from api.utils.nba_data import get_all_teams

teams = get_all_teams()
print(f"Found {len(teams)} teams")
print(teams[:3])  # First 3 teams
```

#### Test 2: Get Team Stats

```python
from api.utils.nba_data import get_team_id, get_team_stats

# Get Lakers stats
lakers_id = get_team_id('Lakers')
stats = get_team_stats(lakers_id)

print(f"Lakers PPG: {stats['overall']['PTS']}")
print(f"Home PPG: {stats['home']['PTS']}")
print(f"Away PPG: {stats['away']['PTS']}")
```

#### Test 3: Get Today's Games

```python
from api.utils.nba_data import get_todays_games

games = get_todays_games()
print(f"Games today: {len(games)}")

for game in games:
    print(f"{game['away_team_name']} @ {game['home_team_name']}")
```

#### Test 4: Generate Prediction

```python
from api.utils.nba_data import get_team_id, get_matchup_data
from api.utils.prediction_engine import predict_game_total

# Get matchup data
nets_id = get_team_id('Nets')
knicks_id = get_team_id('Knicks')
matchup = get_matchup_data(nets_id, knicks_id)

# Generate prediction
prediction = predict_game_total(matchup['home'], matchup['away'], betting_line=220.5)

print(f"Predicted Total: {prediction['predicted_total']}")
print(f"Recommendation: {prediction['recommendation']}")
print(f"Confidence: {prediction['confidence']}%")
```

## Testing the API Endpoints

### Start the Flask Development Server

```bash
python api/games.py
```

The server will start on `http://localhost:5000`

### Test Endpoints with curl

#### 1. Get Today's Games with Predictions

```bash
curl http://localhost:5000/api/games
```

Response:
```json
{
  "success": true,
  "date": "2024-11-09",
  "games": [
    {
      "game_id": "0022400001",
      "home_team": {...},
      "away_team": {...},
      "prediction": {
        "predicted_total": 225.3,
        "betting_line": 220.5,
        "recommendation": "OVER",
        "confidence": 72,
        ...
      }
    }
  ],
  "count": 10,
  "last_updated": "2024-11-09T18:30:00"
}
```

#### 2. Get Detailed Game Analysis

```bash
curl "http://localhost:5001/api/game_detail?home_team_id=1610612751&away_team_id=1610612752&betting_line=220.5"
```

## Common Team IDs

For quick testing, here are some common team IDs:

```python
TEAM_IDS = {
    'Lakers': 1610612747,
    'Warriors': 1610612744,
    'Celtics': 1610612738,
    'Heat': 1610612748,
    'Nets': 1610612751,
    'Knicks': 1610612752,
    '76ers': 1610612755,
    'Bucks': 1610612749,
    'Bulls': 1610612741,
    'Mavericks': 1610612742,
    'Nuggets': 1610612743,
    'Rockets': 1610612745,
    'Clippers': 1610612746,
    'Suns': 1610612756,
    'Raptors': 1610612761,
}
```

## Caching

The system includes automatic caching:

- **Team Stats**: Cached for 1 hour (3600 seconds)
- **Advanced Stats**: Cached for 1 hour
- **Today's Games**: Cached for 30 minutes (1800 seconds)
- **Recent Games**: Cached for 30 minutes

### Clear Cache

```python
from api.utils.nba_data import clear_cache

clear_cache()
print("Cache cleared!")
```

### View Cache Info

```python
from api.utils.nba_data import get_cache_info

info = get_cache_info()
print(f"Cached items: {info['cached_items']}")
```

## Rate Limiting

The NBA API has rate limits. Our implementation includes:

- **600ms delay** between API calls (via `@safe_api_call` decorator)
- **Automatic caching** to minimize repeated calls
- **Error handling** to gracefully handle rate limit errors

## Troubleshooting

### Issue: "No games found today"

**Solution**: This is normal on off-days when no NBA games are scheduled. Try testing with a date that has games, or use the test suite with known team matchups.

### Issue: "API Error: 429 Too Many Requests"

**Solution**: You've hit the rate limit. Wait a minute and try again. The caching should prevent this in normal usage.

### Issue: "ModuleNotFoundError: No module named 'nba_api'"

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: Stats showing as None or 0

**Solution**: The app is configured for the 2025-26 NBA season. If the season hasn't started yet, you may see empty data. Once the season begins, all stats will populate automatically.

## Data Structure Reference

### Team Stats Object

```python
{
    'overall': {
        'GP': 10,              # Games Played
        'W': 7,                # Wins
        'L': 3,                # Losses
        'PTS': 115.2,          # Points Per Game
        'FG_PCT': 0.478,       # Field Goal %
        'FG3_PCT': 0.365,      # 3-Point %
        'FT_PCT': 0.812,       # Free Throw %
        ...
    },
    'home': {...},  # Same stats for home games
    'away': {...}   # Same stats for away games
}
```

### Advanced Stats Object

```python
{
    'OFF_RATING': 116.5,   # Offensive Rating
    'DEF_RATING': 110.2,   # Defensive Rating
    'NET_RATING': 6.3,     # Net Rating
    'PACE': 101.2,         # Pace (possessions per 48 min)
    'TS_PCT': 0.582,       # True Shooting %
    ...
}
```

### Prediction Object

```python
{
    'predicted_total': 225.3,
    'betting_line': 220.5,
    'recommendation': 'OVER',  # or 'UNDER' or 'NO BET'
    'confidence': 72,           # 0-100
    'breakdown': {
        'home_projected': 115.8,
        'away_projected': 109.5,
        'game_pace': 102.3,
        'difference': 4.8,
        'home_form_adjustment': 2.1,
        'away_form_adjustment': -1.3
    },
    'factors': {
        'home_ppg': 116.2,
        'away_ppg': 108.5,
        'home_ortg': 117.5,
        'away_ortg': 113.2,
        'home_pace': 103.1,
        'away_pace': 101.5,
        'game_pace': 102.3,
        'pace_variance': 6.2
    }
}
```

## Next Steps

1. **Test the API**: Run `python api/test_nba_api.py`
2. **Start Development Server**: Run `python api/games.py`
3. **Test Frontend**: Run `npm run dev` and view at `http://localhost:5173`
4. **Deploy to Vercel**: Push to GitHub and connect to Vercel

## Resources

- [nba_api Documentation](https://github.com/swar/nba_api)
- [NBA Stats API Endpoints](https://github.com/swar/nba_api/tree/master/docs/nba_api/stats/endpoints)
- [Flask Documentation](https://flask.palletsprojects.com/)

---

**Note**: The nba_api library uses the official NBA.com stats API. No API key is required, but respect rate limits to avoid being blocked.
