# Mobile-First Design Guide
## NBA Over/Under Analysis Platform

**Target Screens**: 375px (iPhone SE) → 430px (iPhone 14 Pro Max)
**Design Philosophy**: Minimal, Premium, VC-Funded Startup Aesthetic

---

## 🎯 Core Design Principles

### 1. **Visual Hierarchy (Mobile-First)**
```
Priority 1: Prediction/Outcome (Largest, Bold)
Priority 2: Team Matchup (Clear, Scannable)
Priority 3: Actions (Full-width CTAs)
Priority 4: Supporting Data (Progressive Disclosure)
Priority 5: Metadata (Timestamps, Labels)
```

### 2. **Spacing System**
- **Minimum tap target**: 44px (iOS HIG standard)
- **Comfortable tap target**: 48px
- **Card padding**: 20px (1.25rem)
- **Section spacing**: 24px (1.5rem)
- **Vertical rhythm**: 16px base unit

### 3. **Typography Scale**

| Element | Mobile | Desktop | Weight | Notes |
|---------|--------|---------|--------|-------|
| Hero Title | 40px | 64px | 800 | Team matchups |
| Section Heading | 24px | 36px | 700 | Module titles |
| Body Text | 16px | 18px | 400 | Never below 16px |
| Supporting Text | 14px | 16px | 400 | Metadata, captions |
| Minimum Text | 12px | 14px | 500 | Labels, badges |

**Font**: System font stack (-apple-system, SF Pro)

---

## 🎨 Component Design Decisions

### Home Page (Game List)

#### Sticky Header
```
Height: 64px (comfortable thumb reach)
Background: White with subtle shadow
Content: Title + Refresh button only
Position: Sticky top-0
```

**Why**: Always accessible, doesn't compete with content

#### Date/Sort Controls
```
Layout: Stacked vertically (not inline)
Input height: 44px minimum
Spacing: 12px gap between controls
Full-width: Always on mobile
```

**Why**: Easier to tap, no horizontal scroll risk

#### Game Cards
```
Padding: 20px
Border-left: 4px accent (brand color)
Teams: Large (20px), bold
CTA: Full-width, 48px height
Shadow: Subtle (elevation 1)
Spacing: 16px between cards
```

**Why**: Touch-friendly, scannable, clear action

### War Room (Analysis Page)

#### Progressive Disclosure Pattern
```
Default: Prediction expanded, others collapsed
Accordion: 56px tap targets
Icons: 24px emoji (universal language)
Expansion: Smooth 200ms transition
```

**Why**: Reduces cognitive load, fast initial load

#### Hero Section (Matchup)
```
Background: Gradient (primary brand)
Text: White (high contrast)
Teams: 32px bold, centered
Prediction: 40px, pill background
Padding: 24px all sides
```

**Why**: Clear focus, premium feel

#### Stat Rows
```
Layout: Label left, Values right (split)
Typography: 14px label, 16px bold values
Divider: 1px, subtle
Spacing: 16px between rows
```

**Why**: Easy to scan, clear comparison

---

## 🚫 What to REMOVE on Mobile

### ❌ Removed Elements

1. **Sidebar Navigation** → Hamburger menu or bottom nav
2. **Multi-column Grids** → Single column always
3. **Hover States** → Use `:active` pseudo-class
4. **Tooltips** → Inline text or expandable sections
5. **Complex Tables** → Simplified cards or lists
6. **Desktop-only Filters** → Essential filters only
7. **Excessive Whitespace** → Tighter vertical spacing
8. **Marketing Fluff** → Data-first approach

### ✅ Kept (But Simplified)

1. **Back Button** → Clear, always top-left
2. **Refresh** → Icon-only, top-right
3. **CTAs** → Full-width, prominent
4. **Stats** → Simplified, progressive disclosure

---

## 📐 Layout Patterns

### Pattern 1: List → Detail (Navigation)
```
[Home] → Tap card → [Game Detail]
         ↓
         Sticky back button (top-left)
```

### Pattern 2: Accordion (Content Organization)
```
[Section Header] ← Always visible
    ↓ (Tap to expand)
[Section Content] ← Conditionally visible
```

### Pattern 3: Sticky Elements
```
Top: Header (navigation)
Bottom: Primary CTA (if needed)
Middle: Scrollable content
```

---

## 🎯 CTA (Call-to-Action) Strategy

### Primary CTA
- **Color**: Gradient (primary-600 → primary-700)
- **Width**: 100% on mobile
- **Height**: 48px minimum
- **Position**: Bottom of card or section
- **Text**: Clear verb ("View Analysis", "See Details")
- **Icon**: Optional, left-aligned

### Secondary Actions
- **Style**: Ghost (outline) or text-only
- **Size**: 44px minimum
- **Color**: Muted (gray-600)
- **Position**: Below primary CTA

### Destructive Actions
- **Color**: Red
- **Confirmation**: Always require (modal or inline)

---

## 🌈 Color Strategy (Mobile Optimizations)

### Light Mode (Default)
```css
Background: #FAFAFA (off-white, reduces eye strain)
Cards: #FFFFFF (pure white)
Text: #1F2937 (near-black, 16:1 contrast)
Accent: #2563EB (blue, professional)
Success: #10B981 (green)
Warning: #F59E0B (amber)
Error: #EF4444 (red)
```

### Dark Mode (AMOLED-Optimized)
```css
Background: #111827 (true black for OLED)
Cards: #1F2937 (gray-800)
Text: #F9FAFB (gray-50)
Accent: #3B82F6 (lighter blue)
Borders: #374151 (gray-700, subtle)
```

**Why Dark Mode**: Battery savings on OLED, premium feel

---

## 🔢 Data Visualization on Mobile

### Charts (Simplification Rules)
1. **Max Data Points**: 10 (readability limit)
2. **Touch Targets**: 8px radius minimum
3. **Labels**: 12px, rotated if needed
4. **Legend**: Below chart, not floating
5. **Tooltips**: Tap to show, dismiss on second tap

### Tables (Mobile Transformation)
```
Desktop: Multi-column table
   ↓
Mobile: Card list with key/value pairs
```

### Numbers (Formatting)
- Large numbers: "125.5" not "125.50000"
- Percentages: "75%" not "75.0%"
- Currency: "$100" not "$100.00"
- Decimals: Max 1 decimal place

---

## ⚡ Performance Optimizations

### Critical Rendering Path
1. **Above-the-fold**: Load first (hero, CTA)
2. **Below-the-fold**: Lazy load
3. **Images**: Defer off-screen images
4. **Fonts**: System fonts (no web fonts = instant render)

### Animation Budget
- **Max animations**: 2 simultaneous
- **Duration**: 150-300ms (fast, snappy)
- **Easing**: `cubic-bezier(0.4, 0, 0.2, 1)` (iOS standard)
- **GPU**: Use `transform` and `opacity` only

### Bundle Size
- **Target**: <100KB initial JS
- **Strategy**: Code splitting by route
- **Images**: WebP format, max 50KB each

---

## 📱 Gestures & Interactions

### Tap
- **Feedback**: Scale down (0.98) on `:active`
- **Delay**: 0ms (instant response)
- **Ripple**: Optional, subtle

### Swipe
- **Use Cases**: Dismiss modals, navigate tabs
- **Direction**: Left/right for next/previous
- **Threshold**: 50px minimum swipe distance

### Long Press
- **Avoid**: iOS triggers context menu (confusing)
- **Alternative**: Use explicit "More" button

### Pull to Refresh
- **Home Screen**: Native browser refresh (rely on it)
- **Custom**: Only if needed, 60px threshold

---

## 🧪 Testing Checklist

### Device Testing
- [ ] iPhone SE (375px width) - Minimum size
- [ ] iPhone 12/13/14 (390px width) - Most common
- [ ] iPhone 14 Pro Max (430px width) - Maximum size
- [ ] iPad Mini (768px) - Tablet breakpoint
- [ ] Landscape mode (all devices)

### Interaction Testing
- [ ] All tap targets ≥ 44px
- [ ] No horizontal scroll (any breakpoint)
- [ ] CTAs reachable with thumb (bottom half of screen)
- [ ] Forms auto-zoom disabled (font-size ≥ 16px)
- [ ] Loading states (3G throttling)
- [ ] Error states (airplane mode)

### Accessibility Testing
- [ ] VoiceOver navigation (iOS)
- [ ] Dynamic Type support (iOS)
- [ ] Color contrast 4.5:1 minimum (WCAG AA)
- [ ] Focus indicators visible
- [ ] Semantic HTML (`<nav>`, `<main>`, `<article>`)

---

## 🚀 Quick Wins (Immediate Impact)

1. **Add `mobile-first.css`** to global styles
2. **Replace grid layouts** with `space-y-4` (Tailwind)
3. **Make all CTAs** full-width on mobile
4. **Increase font sizes** (min 16px body text)
5. **Add sticky header** to all pages
6. **Collapse advanced sections** by default
7. **Remove desktop-only features** from mobile bundle

---

## 📊 Success Metrics

### Before/After Comparison

| Metric | Before | Target |
|--------|--------|--------|
| Tap Target Pass Rate | 40% | 100% |
| Horizontal Scroll Issues | 15+ | 0 |
| Body Text Size | 12-14px | 16px+ |
| Lighthouse Mobile Score | 65 | 90+ |
| First Contentful Paint | 2.5s | <1.5s |
| Bounce Rate (Mobile) | 45% | <25% |

---

## 🎓 Best Practices Summary

### DO ✅
- Start with 375px width
- Use system fonts
- Full-width CTAs on mobile
- Progressive disclosure
- Touch-friendly spacing (44px+)
- Vertical layouts only
- One action per screen
- Clear back navigation

### DON'T ❌
- Assume hover states
- Use small text (<14px)
- Create complex multi-column layouts
- Hide critical actions in menus
- Use custom scrollbars
- Implement horizontal carousels
- Add unnecessary animations
- Rely on tooltips

---

## 📚 Reference Resources

- [iOS Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [Material Design Touch Targets](https://m3.material.io/foundations/interaction/states/state-layers)
- [WCAG 2.1 Accessibility](https://www.w3.org/WAI/WCAG21/quickref/)
- [Tailwind Mobile-First](https://tailwindcss.com/docs/responsive-design)

---

**Last Updated**: December 2025
**Maintained By**: Product Design Team
