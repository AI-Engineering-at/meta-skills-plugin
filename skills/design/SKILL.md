---
name: design
version: 0.2.0
type: meta
category: meta
complexity: skill
description: Visual DESIGN.md generator — interactive web configurator for design decisions. Exports machine-readable DESIGN.md for Claude Code, Cursor, Codex.
trigger: design skill, design system, DESIGN.md, visual design, meta design
model: sonnet
allowed-tools: [Read, Bash]
user-invocable: true
token-budget: 3000
requires: []
produces: [DESIGN.md, design-specification]
cooperative: true
last-audit: 2026-04-14
---

# meta:design — Visual DESIGN.md Generator

> Design is cooperation, not description-to-generation.
> The user SEES options and CHOOSES. The AI doesn't decide.

## Core Principle

Generate a structured DESIGN.md through interactive cooperation. Present categorized options, capture decisions, export machine-readable spec.

## Workflow

1. **Load** — Check for existing DESIGN.md in project root
2. **Present** — Show options per category (see `references/categories.md`)
3. **Capture** — Record each decision with rationale
4. **Export** — Write DESIGN.md following `references/export-schema.md`
5. **Confirm** — User reviews before any implementation begins

## Decision Matrix

8 categories, each with 3-5 predefined options. Present ONE category at a time. User selects or customizes.

Full category definitions, options, and preview specs: `references/categories.md`

## Export Schema

DESIGN.md follows strict schema: header, 8 sections (background, typography, cards, colors, spacing, animations, icons, layout), each with type + properties.

Full schema + example outputs: `references/export-schema.md`

## After Export

- DESIGN.md becomes single source of truth for UI implementation
- Reference in prompts: "Follow DESIGN.md spec"
- No design decisions without explicit user confirmation

## Integration

- `vg-dashboard/` — Next.js app for visual preview (Phase 1)
- `meta:design start` — launches dev server at `http://localhost:3000`
- Phase 3: MCP server for direct browser integration (future)

## Reference Files

- references/categories.md — 8 category definitions with options
- references/export-schema.md — DESIGN.md schema + examples
