---
name: design
description: >
  Visual DESIGN.md generator — interactive web configurator for design decisions.
  Exports machine-readable DESIGN.md for Claude Code, Cursor, Codex.
  Trigger: design skill, design system, DESIGN.md, visual design, meta design
model: sonnet
allowed-tools: [Read, Bash]
user-invocable: true
version: 0.1.0
type: meta
cooperative: true
token-budget: 3000
category: meta
platforms: [claude, cursor]
---

# meta:design — Visual DESIGN.md Generator

> Design is cooperation, not description-to-generation.
> The user SEES options and CHOOSES. The AI doesn't decide.

## How It Works

meta:design is a web-based configurator. The user opens it in a browser,
goes through design categories (Background, Typography, Cards, Colors, etc.),
and exports a DESIGN.md file that any AI coding tool can read.

## Starting the Design Tool

```bash
cd "${CLAUDE_PLUGIN_ROOT}/../../vg-dashboard" && npm run dev
```

Or if deployed: open the configured URL.

The tool runs at `http://localhost:3000` and provides:
- 8 interactive design categories
- Live preview for every option
- Export button that downloads DESIGN.md

## After Export

Once the user has a DESIGN.md:
1. Read the exported file
2. Use it as design specification for building the UI
3. Every design decision is documented — no guessing

## Current Status

Phase 1: Standalone Next.js app (vg-dashboard/)
Phase 2: Plugin command starts dev server (this version)
Phase 3: MCP server for direct browser integration (future)
