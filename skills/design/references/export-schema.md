# DESIGN.md Export Schema

## Structure

Every DESIGN.md MUST follow this schema:

```markdown
# Design Specification

> Generated: YYYY-MM-DD
> Version: X.Y.Z

## Background
- Type: <gradient|solid|pattern|neural|image>
- <type-specific properties>

## Typography
- Font: <font-family>
- Base Size: <px>
- Scale: <ratio> (<name>)
- Weights: <comma-separated>

## Cards
- Style: <bordered|shadow|glass|flat>
- <style-specific properties>

## Colors
- Primary: <hex>
- Accent: <hex>
- Surface: <hex>
- Surface Alt: <hex>
- Text: <hex>
- Text Muted: <hex>
- Border: <hex>

## Spacing
- Scale: <compact|standard|relaxed>
- Base: <px>
- Density: <compact|standard|relaxed>

## Animations
- Duration: <ms> (<descriptor>)
- Easing: <easing-function>
- Transitions: <comma-separated>

## Icons
- Style: <outline|filled|duotone>
- Set: <icon-set-name>
- Size: <px>

## Layout
- Type: <grid|sidebar|dashboard|list>
- <type-specific properties>
```

## Example Output

```markdown
# Design Specification

> Generated: 2026-04-14
> Version: 1.0.0

## Background
- Type: gradient
- Colors: #0a0a0a → #1a1a2e
- Direction: 135deg
- Type: linear

## Typography
- Font: Inter
- Base Size: 14px
- Scale: 1.25 (major third)
- Weights: 400, 600, 700

## Cards
- Style: glass
- Border Radius: 12px
- Blur: 10px
- Background Opacity: 0.8
- Border: 1px solid rgba(255,255,255,0.1)

## Colors
- Primary: #3b82f6
- Accent: #8b5cf6
- Surface: #1e1e2e
- Surface Alt: #2a2a3e
- Text: #e4e4e7
- Text Muted: #a1a1aa
- Border: #3f3f46

## Spacing
- Scale: standard
- Base: 8px
- Density: standard

## Animations
- Duration: 200ms (standard)
- Easing: ease-out
- Transitions: hover-scale, fade-in

## Icons
- Style: outline
- Set: Lucide
- Size: 20px

## Layout
- Type: grid
- Columns: 3
- Gap: 16px
- Responsive Breakpoints: 768px, 1024px
```

## Validation Rules

1. ALL 8 sections MUST be present
2. Colors MUST be valid hex (#RRGGBB)
3. Font MUST be available (Google Fonts or system)
4. Scale ratios MUST be one of: 1.125, 1.25, 1.333, 1.5
5. Durations MUST be: 100ms, 200ms, 300ms, or 500ms
