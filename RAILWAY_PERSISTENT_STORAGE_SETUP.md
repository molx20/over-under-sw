# Railway Persistent Storage Setup Guide

## Problem
Currently, your game predictions database (`api/data/predictions.db`) is stored in ephemeral storage, which means:
- ❌ All game history is **lost on every deployment**
- ❌ Container restarts wipe your data
- ❌ You can only see games saved since the last deploy

## Solution: Railway Volumes
Railway Volumes provide persistent storage that survives deployments and restarts.

---

## Step-by-Step Setup Instructions

### 1. Create a Volume in Railway Dashboard

1. **Open your Railway project** in the dashboard
2. **Open the Command Palette**:
   - Press `⌘K` (Mac) or `Ctrl+K` (Windows/Linux)
   - OR right-click on the project canvas
3. **Select "New Volume"** from the menu
4. **Choose your service** when prompted (your web service)

### 2. Configure the Volume Mount Path

When prompted for the mount path, enter:
```
/app/api/data
```

**Why `/app/api/data`?**
- Railway's Nixpacks buildpack places your application code in `/app`
- Your database files are in the `api/data/` directory relative to your app root
- So the absolute path becomes `/app/api/data`

### 3. Name Your Volume (Optional)

You can name it something descriptive like:
```
nba-predictions-db
```

### 4. Save and Deploy

- Click **Create** or **Save**
- Railway will **automatically restart your service** to mount the volume
- This restart is normal and required

---

## What This Does

**Before Volumes:**
```
Deployment 1: Save 10 games → Database has 10 games
    ↓ [New deployment]
Deployment 2: Database resets → 0 games (all lost!)
```

**After Volumes:**
```
Deployment 1: Save 10 games → Database has 10 games
    ↓ [New deployment]
Deployment 2: Database persists → Still 10 games ✅
    ↓ [Save 5 more games]
Deployment 3: Database persists → Now 15 games ✅
```

---

## Verification Steps

After setting up the volume:

### 1. Check Environment Variables
Your Railway service will automatically have these environment variables:
```bash
RAILWAY_VOLUME_NAME=<your-volume-id>
RAILWAY_VOLUME_MOUNT_PATH=/app/api/data
```

### 2. Test Persistence
1. Save a prediction in your app
2. Go to Railway dashboard and manually restart the service
3. Check the history tab - the prediction should still be there ✅

### 3. Test Across Deployments
1. Save a prediction
2. Make any code change and push to git (triggers new deployment)
3. After deployment completes, check history - prediction should persist ✅

---

## Important Notes

### ⚠️ Volume Mount Timing
- Volumes are mounted **at runtime**, not during build time
- Don't worry - your app writes to the database at runtime (when saving predictions), so this works perfectly!

### 📦 Volume Size
- Free tier: 1 GB (more than enough for thousands of game predictions)
- Pro tier: Can increase up to 250 GB if needed

### 🔒 Backup Recommendation
Even with persistent volumes, it's good practice to occasionally backup your database:
```bash
# Download from Railway (using Railway CLI)
railway run sqlite3 api/data/predictions.db ".backup /tmp/backup.db"
```

---

## Troubleshooting

### Volume Not Mounting
- Check Railway logs for mount errors
- Verify mount path is exactly `/app/api/data`
- Ensure service was restarted after adding volume

### Data Still Disappearing
- Verify volume is connected to the correct service
- Check that `RAILWAY_VOLUME_MOUNT_PATH` environment variable exists
- Ensure database writes are happening at runtime (not build time)

### Permission Issues
If you see permission errors, add this environment variable in Railway:
```
RAILWAY_RUN_UID=0
```

---

## Summary

**What You Need to Do:**
1. Open Railway dashboard
2. Press `⌘K` (or `Ctrl+K`)
3. Select "New Volume"
4. Choose your web service
5. Enter mount path: `/app/api/data`
6. Create the volume
7. Wait for automatic restart

**Result:**
✅ Game predictions persist across deployments
✅ History tab shows all saved games
✅ No more data loss!

---

## After Setup

Once the volume is created and your service restarts:
- Your history tab will initially be empty (fresh start)
- All new predictions you save will **persist forever**
- Future deployments won't lose your data
- You can safely make code changes and deploy without losing game history

Ready to save predictions that actually stick around! 🎯
