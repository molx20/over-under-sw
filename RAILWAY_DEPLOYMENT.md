# Railway Deployment Guide

## Prerequisites

1. A [Railway](https://railway.app) account
2. Your code pushed to a GitHub repository
3. Railway CLI installed (optional): `npm i -g @railway/cli`

## Quick Deploy

### Option 1: Deploy from GitHub (Recommended)

1. Go to [Railway](https://railway.app) and sign in
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will automatically detect the configuration and deploy

### Option 2: Deploy using Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Deploy
railway up
```

## Configuration

Railway will automatically:
- Install Python dependencies from `requirements.txt`
- Install Node.js dependencies from `package.json`
- Build the frontend with `npm run build`
- Start the server with `gunicorn server:app`

The configuration is defined in:
- `Procfile` - Defines the start command
- `nixpacks.toml` - Defines build phases
- `railway.json` - Railway-specific configuration
- `runtime.txt` - Python version

## Environment Variables

No environment variables are required for basic deployment, but you can optionally set:

- `PORT` - Railway sets this automatically
- Any custom environment variables your app needs

## Frontend Configuration

After deployment, you'll need to update your frontend to point to the Railway backend:

1. Get your Railway deployment URL (e.g., `https://your-app-name.railway.app`)
2. For local development, create `.env.local`:
   ```
   VITE_API_URL=https://your-app-name.railway.app/api
   ```
3. For production builds, the frontend will automatically use `/api` (relative path)

## Deployment Structure

Your app is deployed as a **monorepo**:
- Backend: Flask server (`server.py`) serves the API at `/api/*`
- Frontend: React app built to `dist/` folder, served at `/`
- Single Railway service handles both backend and frontend

## Important Files

```
.
├── server.py              # Flask application (main entry point)
├── Procfile              # Tells Railway how to start the app
├── nixpacks.toml         # Build configuration
├── railway.json          # Railway deployment settings
├── runtime.txt           # Python version
├── requirements.txt      # Python dependencies
├── package.json          # Node dependencies + build script
├── api/                  # Python API modules
│   └── utils/           # NBA data fetching and prediction logic
└── dist/                # Built React app (generated)
```

## Monitoring

After deployment:
1. View logs: Click on your service → "Deployments" → "View Logs"
2. Check metrics: View CPU, Memory, and Network usage
3. Set up alerts: Configure notifications for errors

## Troubleshooting

### Build fails
- Check that all dependencies are in `requirements.txt` and `package.json`
- Verify Python version in `runtime.txt` matches your local version
- Check build logs in Railway dashboard

### API requests fail
- Verify the Railway URL is correct
- Check CORS settings in `server.py`
- Review server logs for errors

### Frontend shows blank page
- Ensure `npm run build` completed successfully
- Check that `dist/` folder is created
- Verify static file serving in `server.py`

### Slow responses
- NBA API can be slow, especially for stats
- First request may take longer (cold start)
- Subsequent requests use in-memory cache

## Scaling

Railway automatically:
- Restarts on crashes (up to 10 retries)
- Provides HTTPS
- Gives you a custom domain
- Handles load balancing

For better performance:
- Upgrade to Railway Pro for dedicated resources
- Add a custom domain
- Consider adding Redis for persistent caching (optional)

## Cost

- **Hobby Plan**: $5/month (500 hours of usage)
- **Pro Plan**: $20/month (unlimited)
- **Free Trial**: Available for new accounts

## Next Steps

1. Deploy to Railway
2. Get your deployment URL
3. Test the API endpoints:
   - `https://your-app.railway.app/api/health`
   - `https://your-app.railway.app/api/games`
4. Share your app!

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- GitHub Issues: Report issues in your repository
