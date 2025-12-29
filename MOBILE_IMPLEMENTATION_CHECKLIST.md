# Mobile-First Implementation Checklist
## Step-by-Step Refactoring Guide

---

## Phase 1: Foundation (Week 1)

### ✅ Setup & Infrastructure

- [ ] **Add mobile-first.css to project**
  ```bash
  # Copy to src/styles/
  # Import in src/index.jsx or App.jsx
  import './styles/mobile-first.css'
  ```

- [ ] **Update Tailwind config** (if using Tailwind)
  ```js
  // tailwind.config.js
  module.exports = {
    theme: {
      screens: {
        'sm': '640px',   // Tablet
        'md': '768px',   // Tablet landscape
        'lg': '1024px',  // Desktop
        'xl': '1280px',  // Large desktop
      },
      extend: {
        fontSize: {
          'fluid-xs': 'clamp(0.75rem, 0.7rem + 0.25vw, 0.875rem)',
          'fluid-sm': 'clamp(0.875rem, 0.8rem + 0.375vw, 1rem)',
          'fluid-base': 'clamp(1rem, 0.95rem + 0.25vw, 1.125rem)',
          'fluid-lg': 'clamp(1.125rem, 1rem + 0.625vw, 1.5rem)',
          'fluid-xl': 'clamp(1.5rem, 1.3rem + 1vw, 2.25rem)',
        },
        minHeight: {
          'touch': '44px',
          'touch-comfortable': '48px',
          'touch-large': '56px',
        }
      }
    }
  }
  ```

- [ ] **Add viewport meta tag** (if missing)
  ```html
  <!-- public/index.html -->
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes">
  ```

- [ ] **Test on actual devices** (not just Chrome DevTools)
  - iPhone SE (375px)
  - iPhone 14 (390px)
  - iPhone 14 Pro Max (430px)

---

## Phase 2: Core Pages (Week 2)

### ✅ Home Page Refactor

- [ ] **Replace Home.jsx** with mobile-optimized version
  ```bash
  # Backup current version
  mv src/pages/Home.jsx src/pages/Home.jsx.backup

  # Copy mobile-optimized version
  mv src/pages/Home.mobile-optimized.jsx src/pages/Home.jsx
  ```

- [ ] **Update GameCard component**
  ```bash
  mv src/components/GameCard.jsx src/components/GameCard.jsx.backup
  mv src/components/GameCard.mobile-optimized.jsx src/components/GameCard.jsx
  ```

- [ ] **Test Home page**
  - [ ] No horizontal scroll at 375px
  - [ ] All buttons ≥ 44px tap target
  - [ ] Date picker full-width
  - [ ] Sort dropdown full-width
  - [ ] Cards stack vertically
  - [ ] Refresh button accessible (top-right)
  - [ ] Loading state clear and centered

---

### ✅ War Room Page Refactor

- [ ] **Replace WarRoom.jsx** with mobile-optimized version
  ```bash
  mv src/pages/WarRoom.jsx src/pages/WarRoom.jsx.backup
  mv src/pages/WarRoom.mobile-optimized.jsx src/pages/WarRoom.jsx
  ```

- [ ] **Implement Collapsible Sections**
  - [ ] Extract `<CollapsibleSection>` component
  - [ ] Add to all major analysis modules
  - [ ] Default: Prediction expanded, others collapsed
  - [ ] Smooth 200ms transitions

- [ ] **Simplify Hero Section**
  - [ ] Remove unnecessary badges
  - [ ] Focus on team matchup + prediction
  - [ ] Gradient background (brand colors)
  - [ ] White text for contrast

- [ ] **Test War Room**
  - [ ] Back button works (top-left)
  - [ ] Sections collapse/expand smoothly
  - [ ] Stats readable without zooming
  - [ ] No content cutoff on small screens
  - [ ] CTAs full-width

---

## Phase 3: Components (Week 3)

### ✅ Refactor Existing Components

For each component, apply these rules:

#### **MatchupIndicators.jsx**
- [ ] Stack vertically on mobile
- [ ] Increase icon sizes (32px min)
- [ ] Labels: 14px minimum
- [ ] Remove multi-column layouts

#### **EmptyPossessionsGauge.jsx**
- [ ] Simplify gauge (maybe just number + bar)
- [ ] Remove complex SVG if too small
- [ ] Focus on key metric only
- [ ] Add "Learn More" collapse

#### **VolatilityProfile.jsx**
- [ ] Chart: Max 10 data points
- [ ] Touch targets: 8px radius
- [ ] Legend below chart (not floating)
- [ ] Tap to show values

#### **Last5GamesPanel.jsx**
- [ ] Game cards: Simplified layout
- [ ] W/L: Large, bold
- [ ] Score: Secondary
- [ ] Details: Collapsed by default

#### **SimilarOpponentBoxScores.jsx**
- [ ] Accordion pattern (one team at a time)
- [ ] Stats: Key metrics only (3-5 max)
- [ ] Full stats: "View More" button

---

## Phase 4: Navigation & Chrome (Week 4)

### ✅ Global Navigation

- [ ] **Create mobile-first navigation**
  ```
  Option A: Bottom Tab Bar (Recommended)
    - Home (🏠)
    - War Room (⚔️)
    - Settings (⚙️)
    - Fixed position bottom
    - 56px height (thumb-friendly)

  Option B: Hamburger Menu
    - Icon: Top-left
    - Slide-in drawer
    - Overlay backdrop
  ```

- [ ] **Sticky Header Component**
  ```jsx
  // src/components/MobileHeader.jsx
  <header className="sticky top-0 z-50 bg-white dark:bg-gray-800 border-b">
    <div className="mobile-container py-3">
      <div className="flex items-center justify-between">
        {/* Title or Back Button */}
        {/* Action Button (Refresh, etc.) */}
      </div>
    </div>
  </header>
  ```

- [ ] **Test navigation**
  - [ ] Bottom nav stays fixed
  - [ ] Active state clear
  - [ ] Icons labeled (accessibility)
  - [ ] Smooth transitions

---

## Phase 5: Polish & Optimization (Week 5)

### ✅ Typography Audit

- [ ] **Replace all text sizes**
  ```jsx
  // BEFORE (Bad)
  className="text-xs"  // 12px - too small

  // AFTER (Good)
  className="text-sm"  // 14px minimum
  ```

- [ ] **Scan entire codebase**
  ```bash
  # Find instances of small text
  grep -r "text-xs" src/
  grep -r "text-\[10px\]" src/
  grep -r "text-\[11px\]" src/

  # Replace with minimum 14px
  ```

---

### ✅ Spacing Audit

- [ ] **Replace padding/margin values**
  ```jsx
  // BEFORE
  className="p-2"  // 8px - too cramped

  // AFTER
  className="p-4 sm:p-6"  // 16px mobile, 24px desktop
  ```

- [ ] **Check all tap targets**
  ```bash
  # Search for buttons without min-height
  grep -r "<button" src/ | grep -v "min-h"
  ```

---

### ✅ Performance Optimization

- [ ] **Code Splitting**
  ```jsx
  // src/App.jsx
  const WarRoom = lazy(() => import('./pages/WarRoom'))
  const GamePage = lazy(() => import('./pages/GamePage'))
  ```

- [ ] **Image Optimization**
  - [ ] Convert PNGs to WebP
  - [ ] Add `loading="lazy"` to below-fold images
  - [ ] Compress to <50KB each

- [ ] **Bundle Analysis**
  ```bash
  npm run build
  npx webpack-bundle-analyzer build/static/js/*.js

  # Target: <100KB initial bundle
  ```

---

## Phase 6: Testing & QA (Week 6)

### ✅ Device Testing

- [ ] **iPhone SE (375px)**
  - [ ] All pages render correctly
  - [ ] No horizontal scroll
  - [ ] Text readable without zoom
  - [ ] Buttons easy to tap

- [ ] **iPhone 12/13/14 (390px)**
  - [ ] Layout uses full width
  - [ ] Spacing feels balanced
  - [ ] Images load correctly

- [ ] **iPhone 14 Pro Max (430px)**
  - [ ] Not too spacious
  - [ ] Content centered
  - [ ] Still feels mobile-optimized

- [ ] **iPad Mini (768px)**
  - [ ] Transitions to tablet layout
  - [ ] Uses available space well
  - [ ] Not just stretched mobile view

---

### ✅ Accessibility Testing

- [ ] **VoiceOver (iOS)**
  ```
  Settings → Accessibility → VoiceOver → On

  Test:
  - Navigate with swipe gestures
  - All buttons have labels
  - Images have alt text
  - Forms have labels
  ```

- [ ] **Dynamic Type**
  ```
  Settings → Accessibility → Display & Text Size → Larger Text

  Test:
  - Layout doesn't break
  - Text scales appropriately
  - Min/max sizes respected
  ```

- [ ] **Color Contrast**
  - [ ] Use WebAIM Contrast Checker
  - [ ] All text: 4.5:1 ratio minimum
  - [ ] Large text (18px+): 3:1 ratio

---

### ✅ Performance Testing

- [ ] **Lighthouse (Mobile)**
  ```bash
  # Run in Chrome DevTools
  # Target Scores:
  - Performance: 90+
  - Accessibility: 95+
  - Best Practices: 95+
  - SEO: 100
  ```

- [ ] **Network Throttling**
  - [ ] Test on 3G (Chrome DevTools)
  - [ ] Loading states visible
  - [ ] No layout shift
  - [ ] Graceful degradation

---

## Phase 7: Launch Preparation (Week 7)

### ✅ Documentation

- [ ] **Update README**
  - [ ] Add mobile-first approach
  - [ ] List supported devices
  - [ ] Include screenshots

- [ ] **Team Training**
  - [ ] Share MOBILE_DESIGN_GUIDE.md
  - [ ] Conduct design review
  - [ ] Set mobile-first as default

---

### ✅ Analytics Setup

- [ ] **Track Mobile Metrics**
  ```js
  // Add to analytics
  - Screen width on page load
  - Device type (mobile/tablet/desktop)
  - Touch vs mouse events
  - Scroll depth
  - Button tap success rate
  ```

---

### ✅ Rollout Strategy

- [ ] **A/B Test (Optional)**
  - 50% users: Old layout
  - 50% users: Mobile-first layout
  - Track: Bounce rate, time on site, conversions

- [ ] **Gradual Rollout**
  - Week 1: 10% of users
  - Week 2: 50% of users
  - Week 3: 100% of users

- [ ] **Monitoring**
  - [ ] Watch error logs
  - [ ] Check mobile analytics
  - [ ] Gather user feedback

---

## 🎯 Success Criteria

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Lighthouse Mobile Score | ? | 90+ | ⏳ |
| Horizontal Scroll Issues | ? | 0 | ⏳ |
| Tap Target Pass Rate | ? | 100% | ⏳ |
| Min Body Text Size | 12-14px | 16px | ⏳ |
| Mobile Bounce Rate | ? | <25% | ⏳ |
| Average Session Duration | ? | +50% | ⏳ |

---

## 🚨 Common Pitfalls to Avoid

1. **Testing only in Chrome DevTools**
   → Always test on real devices

2. **Forgetting landscape mode**
   → Test both portrait and landscape

3. **Ignoring safe area insets**
   → Add padding for iPhone notch

4. **Using hover states**
   → Replace with `:active` or remove

5. **Small tap targets**
   → Audit every interactive element

6. **Horizontal scroll**
   → Set `max-width: 100vw` globally

7. **Tiny text**
   → Minimum 14px, prefer 16px

8. **Complex layouts**
   → Single column on mobile, always

---

## 📞 Support Resources

- **Design System**: See `MOBILE_DESIGN_GUIDE.md`
- **CSS Framework**: See `src/styles/mobile-first.css`
- **Component Examples**: See `.mobile-optimized.jsx` files
- **Questions**: Contact design team

---

**Start Date**: ___________
**Target Launch**: ___________ (7 weeks from start)
**Status**: 🟡 In Progress
