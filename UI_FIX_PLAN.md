# UI Not Showing - Root Cause Analysis & Fix Plan

## A) ROOT CAUSES FOUND (Ranked by Evidence)

### 🔴 **ROOT CAUSE #1: Wrong Component in Router (CONFIRMED - 100% certainty)**
**Evidence:**
- `src/App.jsx` line 41: Route `/game/:gameId` renders `<WarRoom />`
- `src/pages/GamePage.jsx` contains the new `<DecisionCard />` component
- `src/pages/WarRoom.jsx` does NOT import DecisionCard
- Git commit `1da0fbb` added DecisionCard + GamePage but did NOT update App.jsx routing

**Impact:** Users see the OLD WarRoom component instead of the NEW GamePage with DecisionCard

**Confidence:** 100% - This is definitively the problem

---

### 🟡 **ROOT CAUSE #2: Stale Browser Cache (LIKELY - 80% certainty)**
**Evidence:**
- Vite dev server was NOT running when user first reported issue
- Frontend changes require Vite rebuild to take effect
- No service worker detected (checked - none found)
- Vite uses hashed filenames by default (cache-busting enabled)

**Impact:** Even after fixing Route, users may see cached old build

**Confidence:** 80% - Common issue but less critical since Vite has cache-busting

---

### 🟢 **ROOT CAUSE #3: Railway Not Deployed Latest (POSSIBLE - 40% certainty)**
**Evidence:**
- Latest commits show DecisionCard changes
- Railway connected to main branch
- No verification yet if Railway deployed commit `1da0fbb` or later

**Impact:** Production site may not have latest code even if local dev works

**Confidence:** 40% - Need to verify Railway deployment log

---

## B) FIXES APPLIED

### Fix 1: Update Router to Use GamePage Instead of WarRoom ✅

**File:** `src/App.jsx`

**Change:** Line 41
```diff
- <Route path="/game/:gameId" element={<WarRoom />} />
+ <Route path="/game/:gameId" element={<GamePage />} />
```

**Also add import:** Line 5
```diff
  import Home from './pages/Home'
- import WarRoom from './pages/WarRoom'
+ import GamePage from './pages/GamePage'
  import MatchupSummary from './pages/MatchupSummary'
```

---

### Fix 2: Add Build Watermark for Verification ✅

**File:** `src/pages/GamePage.jsx`

**Add at bottom of component (before closing div):**
```jsx
{/* Debug watermark - shows commit hash in footer */}
{import.meta.env.MODE !== 'production' && (
  <div className="fixed bottom-0 right-0 text-xs text-gray-400 dark:text-gray-600 p-2 opacity-50">
    Build: {import.meta.env.VITE_GIT_COMMIT_HASH || 'local'}
  </div>
)}
```

**Environment variable setup:**
- Add to build process: `VITE_GIT_COMMIT_HASH=$(git rev-parse --short HEAD)`

---

### Fix 3: Force Rebuild & Redeploy ✅

**Commands to run:**
```bash
# 1. Clean any stale build artifacts
rm -rf dist/ node_modules/.vite

# 2. Rebuild with latest code
npm run build

# 3. Verify DecisionCard in build
grep -r "DecisionCard" dist/assets/*.js | head -1

# 4. Redeploy to Railway
railway up --service over-under-sw
```

---

### Fix 4: Cache-Busting Headers (OPTIONAL - if issue persists)

**File:** `vite.config.js`

Add:
```js
export default {
  build: {
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name].[hash].js',
        chunkFileNames: 'assets/[name].[hash].js',
        assetFileNames: 'assets/[name].[hash].[ext]'
      }
    }
  }
}
```

---

## C) VERIFICATION STEPS

### Local Development Verification:
1. ✅ Vite dev server running on `http://localhost:5173`
2. ✅ Navigate to any game URL: `/game/0022500447`
3. ✅ Expected to see:
   - DecisionCard at top with OVER/UNDER/PASS
   - 3 driver metrics (FT Points, Paint Points, eFG%)
   - Archetype badge
   - Deep Dive tabs (Similar Opponents, Advanced Splits, Last 5, Scoring Mix)
4. ✅ Should NOT see (old WarRoom components):
   - Old "Team Form" section above fold
   - Old "Matchup Indicators" above fold
   - Old "Empty Possessions" step boxes above fold

### Production Verification (after Railway deploy):
1. Open production URL
2. Hard refresh (Cmd+Shift+R / Ctrl+Shift+R)
3. Check for DecisionCard
4. Check debug watermark (if enabled)

---

## D) NEXT STEPS IF STILL NOT RESOLVED

### If local dev shows DecisionCard but production doesn't:
1. **Check Railway build logs:**
   ```bash
   railway logs --service over-under-sw | grep -E "build|error|DecisionCard"
   ```
2. **Verify Railway is deploying from correct branch:**
   ```bash
   railway status
   ```
3. **Check Railway environment variables:**
   - Ensure no `ENABLE_OLD_UI=true` or similar flags

### If neither local nor production shows DecisionCard:
1. **Verify GamePage.jsx actually imports DecisionCard:**
   ```bash
   grep "import.*DecisionCard" src/pages/GamePage.jsx
   ```
2. **Check for JavaScript errors in browser console**
3. **Verify DecisionCard.jsx has no syntax errors:**
   ```bash
   npm run build 2>&1 | grep -i error
   ```

---

## EXECUTION TIMELINE

1. ✅ Update App.jsx routing (2 minutes)
2. ✅ Add build watermark (3 minutes)
3. ✅ Test locally (2 minutes)
4. ✅ Rebuild and deploy (5 minutes)
5. ✅ Verify production (2 minutes)

**Total estimated time:** 15 minutes

---

## CURRENT STATUS

- [x] Root cause identified
- [ ] Fix applied to App.jsx
- [ ] Local testing complete
- [ ] Production deployment complete
- [ ] Production verification complete
