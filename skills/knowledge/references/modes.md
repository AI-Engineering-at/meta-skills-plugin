# knowledge — Mode Workflows

## Mode: LOG (record new error or learning)

When user says "document error", "new error", "record learning":

### Record Error:
1. Read last E-number:
   ```bash
   grep -oP "E\d+" .claude/knowledge/ERRORS.md | sort -t'E' -k1 -n | tail -1
   ```
2. Assign next E-number (E+1)
3. Append entry to `ERRORS.md` — format:
   ```
   ### E{NNN} — {Short title}
   **What:** {What happened}
   **Why:** {Root cause}
   **Fix:** {What to do}
   **Session:** {Date}
   ```
4. Check if this error belongs in the top-10 checklist:
   - Is it frequent? (>2x occurrences)
   - Is it expensive? (>30min time loss)
   - If yes: append one-liner to `08-checkliste.md`

### Record Learning:
1. Read last L-number:
   ```bash
   grep -oP "L\d+" .claude/knowledge/LEARNINGS.md | sort -t'L' -k1 -n | tail -1
   ```
2. Assign next L-number (L+1)
3. Append entry to `LEARNINGS.md` — format:
   ```
   ### L{NNN} — {Short title}
   **What:** {Pattern description}
   **Right:** {What to do}
   **Wrong:** {What to avoid}
   **Session:** {Date}
   ```

## Mode: SEARCH (retrieve knowledge)

When user says "what do we know about X", "has this happened before", "knowledge search":

### Search chain (in this order):
1. **open-notebook RAG** (fastest semantic search):
   ```bash
   curl -s -X POST "${OPEN_NOTEBOOK_URL:-http://localhost:5055}/api/search" \
     -H "Content-Type: application/json" \
     -d "{\"query\":\"SEARCH_TERM\",\"type\":\"text\",\"limit\":5}"
   ```
2. **Local search** (if open-notebook offline):
   ```bash
   grep -rn "SEARCH_TERM" .claude/knowledge/ERRORS.md .claude/knowledge/LEARNINGS.md
   ```
3. **Honcho search** (session-specific context):
   ```bash
   curl -s -X POST "${HONCHO_URL:-http://localhost:8055}/v3/workspaces/ai-engineering/peers/claude-phi/search" \
     -H "Content-Type: application/json" \
     -d "{\"query\":\"SEARCH_TERM\",\"limit\":5}"
   ```

Present results as table: Source | Match | Relevance

> **Note:** On Windows, use `findstr` instead of `grep`, or use Git Bash/WSL.

## Mode: SYNC (synchronize files to open-notebook)

When user says "knowledge sync", "sync knowledge":

1. Create/update ERRORS.md as open-notebook source:
   ```bash
   curl -s -X POST "${OPEN_NOTEBOOK_URL:-http://localhost:5055}/api/sources/json" \
     -H "Content-Type: application/json" \
     -d "{\"type\":\"text\",\"title\":\"Error Registry — $(date +%Y-%m-%d)\",\"content\":\"$(cat .claude/knowledge/ERRORS.md)\",\"notebooks\":[\"notebook:zkxy9fiwelrolgbr2upc\"],\"embed\":true}"
   ```
2. Create/update LEARNINGS.md as open-notebook source
3. Record last sync date in `self-improving/heartbeat-state.md`

## Mode: AUDIT (check consistency)

When user says "knowledge audit", "check knowledge":

1. Check: Are E-numbers in ERRORS.md consistent? (no gaps, no duplicates)
2. Check: Are L-numbers in LEARNINGS.md consistent?
3. Check: Do all entries in 08-checkliste.md reference existing E/L numbers?
4. Check: When was the last open-notebook sync? (heartbeat-state.md)
5. Report: What is inconsistent, what is missing
