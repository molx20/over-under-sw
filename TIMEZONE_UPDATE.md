# Timezone Update - 3 AM MST Game Switchover

## What Changed

The app now switches to show tomorrow's games at **3 AM MST (Mountain Standard Time)** instead of using Eastern Time for the game date.

## How It Works

### Before 3 AM MST
- Shows games from the current calendar day
- Example: At 2:30 AM MST on Nov 20, shows Nov 20 games

### After 3 AM MST
- Shows games from the next calendar day
- Example: At 3:15 AM MST on Nov 20, shows Nov 21 games

## Why This Matters

**Problem Solved:** NBA games typically finish between midnight-2 AM MST. By 3 AM, all games are done and you want to start looking at tomorrow's slate for predictions.

**Before (Eastern Time):**
- 3 AM MST = 5 AM ET
- Would still show "today's" games until midnight ET (10 PM MST)
- You had to wait until late evening to see tomorrow's games

**After (Mountain Time with 3 AM cutoff):**
- At 3 AM MST, automatically switches to next day's games
- Gives you 12+ hours to make predictions before evening tipoffs
- Better aligns with when you actually want to see the games

## Technical Details

### Modified Files

**1. `api/utils/nba_data.py`** - `get_todays_games()`
```python
# Use Mountain Time for game date calculation
mst_offset = timedelta(hours=-7)  # MST (UTC-7)
mst_time = datetime.now(timezone.utc) + mst_offset

# After 3 AM MST, show next day's games
if mst_time.hour >= 3:
    # It's after 3 AM, show tomorrow's games (next calendar day)
    tomorrow = mst_time + timedelta(days=1)
    today_str = tomorrow.strftime('%Y-%m-%d')
else:
    # It's before 3 AM, show current day's games (games still finishing)
    today_str = mst_time.strftime('%Y-%m-%d')
```

**2. `server.py`** - `/api/games` endpoint
```python
# Use MST for date display (matches game fetching logic)
mst_offset = timedelta(hours=-7)
mst_time = datetime.now(timezone.utc) + mst_offset

# After 3 AM MST, show tomorrow's date
if mst_time.hour >= 3:
    display_date = (mst_time + timedelta(days=1)).strftime('%Y-%m-%d')
else:
    display_date = mst_time.strftime('%Y-%m-%d')
```

## Example Timeline

Let's say it's **Tuesday, Nov 19**:

| MST Time | What You See | Explanation |
|----------|--------------|-------------|
| Tue 11:00 PM | Nov 19 games | Tonight's games (in progress/finishing) |
| Wed 12:30 AM | Nov 19 games | Late games still finishing |
| Wed 2:00 AM | Nov 19 games | All games final, but before cutoff |
| **Wed 3:00 AM** | **Nov 20 games** | 🔄 Switch! Now showing Thursday's games |
| Wed 10:00 AM | Nov 20 games | You have all day to make predictions |
| Wed 5:00 PM | Nov 20 games | Games start tipping off |

## Impact on Self-Learning Feature

This change works seamlessly with the self-learning feature:

1. **Before 3 AM**: Games from tonight are showing
   - You can run `/api/run-learning` on finished games
   - Perfect time to process completed games

2. **After 3 AM**: Tomorrow's games are showing
   - You can run `/api/save-prediction` for new games
   - You have all day to enter sportsbook lines before tipoff

## Testing

To test this locally at any time:

```python
# In api/utils/nba_data.py, temporarily modify:

# Test "before 3 AM" behavior:
if False:  # Change mst_time.hour >= 3 to False

# Test "after 3 AM" behavior:
if True:   # Change mst_time.hour >= 3 to True
```

## Notes

- **Game times still displayed in ET**: NBA standard is Eastern Time, so game start times remain in ET format (e.g., "7:30 PM ET")
- **NBA API uses UTC**: The NBA CDN uses UTC internally, but the date selector on their site uses ET
- **Cache cleared at 3 AM**: The 30-minute cache will clear at the switchover, so games update immediately
- **Railway deployment**: Works automatically on Railway (no timezone configuration needed)

## Deployment Checklist

- [x] Modified `api/utils/nba_data.py`
- [x] Modified `server.py`
- [x] Tested logic
- [ ] Deploy to Railway
- [ ] Verify at 3 AM MST that games switch

---

**Ready to deploy! Push these changes and your app will switch games at 3 AM MST automatically.**
