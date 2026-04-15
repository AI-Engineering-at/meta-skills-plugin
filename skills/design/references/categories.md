# Design Categories

## 1. Background

| Option | Properties | Preview |
|--------|-----------|---------|
| Gradient | colors[], direction, type (linear/radial) | CSS gradient preview |
| Solid | color, opacity | Single color block |
| Pattern | pattern-type, scale, opacity | Repeating geometric shapes |
| Neural | node-count, connection-opacity, color | Network graph visualization |
| Image | url, position, size, overlay | Background image with overlay |

## 2. Typography

| Option | Properties |
|--------|-----------|
| Sans-Serif | font-family, base-size, scale-ratio, weights[] |
| Serif | font-family, base-size, scale-ratio, weights[] |
| Mono | font-family, base-size, scale-ratio, weights[] |
| Mixed | heading-font, body-font, code-font |

**Size Scale Ratios:** 1.125 (minor third), 1.25 (major third), 1.333 (perfect fourth), 1.5 (perfect fifth)

## 3. Cards

| Option | Properties |
|--------|-----------|
| Bordered | border-radius, border-width, border-color |
| Shadow | border-radius, shadow-sm/md/lg, elevation |
| Glass | blur-amount, background-opacity, border |
| Flat | border-radius, background-color, no-decoration |

## 4. Colors

| Token | Purpose | Example |
|-------|---------|---------|
| primary | Main brand/action color | #3b82f6 (blue) |
| accent | Highlights, secondary actions | #8b5cf6 (purple) |
| surface | Card/container backgrounds | #1e1e2e (dark) |
| surface-alt | Alternate surfaces | #2a2a3e |
| text | Primary text color | #e4e4e7 |
| text-muted | Secondary text | #a1a1aa |
| border | Divider/border color | #3f3f46 |

## 5. Spacing

| Scale | Base | Multiplier | Use |
|-------|------|------------|-----|
| Compact | 6px | 1.5 | Dense dashboards |
| Standard | 8px | 2 | Most applications |
| Relaxed | 12px | 2 | Content-heavy pages |

**Density:** compact (tighter gaps), standard, relaxed (more whitespace)

## 6. Animations

| Property | Values |
|----------|--------|
| Duration | 100ms (snappy), 200ms (standard), 300ms (smooth), 500ms (dramatic) |
| Easing | ease-out (enter), ease-in (exit), ease-in-out (transitions), linear (progress) |
| Transitions | hover-scale, hover-lift, fade-in, slide-in, none |

## 7. Icons

| Style | Sets | Size |
|-------|------|------|
| Outline | Lucide, Heroicons | 16px, 20px, 24px |
| Filled | Material, Fluent | 16px, 20px, 24px |
| Duotone | Heroicons | 20px, 24px |

## 8. Layout

| Type | Structure | Use Case |
|------|-----------|----------|
| Grid | columns, gap, responsive-breakpoints | Card layouts, galleries |
| Sidebar | width, collapsible, position | Navigation, filters |
| Dashboard | widget-grid, responsive, drag | Analytics, admin panels |
| List | density, actions-position, selection | Tables, data lists |
