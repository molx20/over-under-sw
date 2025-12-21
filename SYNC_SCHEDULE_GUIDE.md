# Sync Schedule Configuration

## Current Setup
The NBA data sync runs via the `/api/admin/sync` endpoint, which must be triggered externally.

## Changing Sync Time from 12pm MT to 9am MT

### Option 1: Railway Cron Jobs (Recommended)

1. Go to your Railway project dashboard
2. Click on your service
3. Go to "Settings" → "Cron Jobs"
4. Update the cron expression:

**Current (12pm MT = 7pm UTC = 2pm ET):**
```
0 19 * * *  # 12pm MT / 7pm UTC
```

**New (9am MT = 4pm UTC = 11am ET):**
```
0 16 * * *  # 9am MT / 4pm UTC
```

5. Set the endpoint: `POST /api/admin/sync`
6. Add header: `Authorization: Bearer YOUR_ADMIN_SECRET`
7. Request body:
```json
{
  "sync_type": "full",
  "season": "2025-26"
}
```

### Option 2: External Cron Service (cron-job.org, EasyCron, etc.)

1. Log into your cron service
2. Find the existing job that calls your sync endpoint
3. Update the schedule to: **9:00 AM Mountain Time**
   - In UTC: **4:00 PM (16:00)**
   - In Eastern: **11:00 AM**

4. Ensure the job is calling:
   - URL: `https://your-app.railway.app/api/admin/sync`
   - Method: `POST`
   - Headers: `Authorization: Bearer YOUR_ADMIN_SECRET`
   - Body: `{"sync_type": "full", "season": "2025-26"}`

### Option 3: Add In-App Scheduler (APScheduler)

If you want the app to handle scheduling internally, add APScheduler:

1. Install: `pip install apscheduler`
2. Add to `server.py`:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from api.utils.sync_nba_data import sync_all
import pytz

# Create scheduler
scheduler = BackgroundScheduler()

# Mountain Time zone
mt_tz = pytz.timezone('America/Denver')

# Schedule daily sync at 9:00 AM MT
scheduler.add_job(
    func=lambda: sync_all('2025-26', triggered_by='scheduled'),
    trigger=CronTrigger(hour=9, minute=0, timezone=mt_tz),
    id='daily_nba_sync',
    name='Sync NBA data at 9am MT',
    replace_existing=True
)

# Start scheduler
scheduler.start()
print("[scheduler] Scheduled daily sync at 9:00 AM MT")
```

### Time Zone Reference

| Time Zone | 9am MT Sync |
|-----------|-------------|
| Mountain (MT) | 9:00 AM |
| Pacific (PT) | 8:00 AM |
| Central (CT) | 10:00 AM |
| Eastern (ET) | 11:00 AM |
| UTC | 4:00 PM (16:00) |

### Testing the Sync

You can manually trigger a sync anytime:

```bash
curl -X POST https://your-app.railway.app/api/admin/sync \
  -H "Authorization: Bearer YOUR_ADMIN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"sync_type": "full", "season": "2025-26"}'
```

### Why 9am MT?

- NBA games typically start at 5pm PT / 7pm MT earliest
- Syncing at 9am MT ensures:
  - Previous night's game results are available
  - Today's game schedule is loaded
  - 8+ hours before first games tip off
  - Users see fresh data throughout the day
