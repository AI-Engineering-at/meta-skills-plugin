# doc-updater — Execution Flow

## Step 1: Parse Arguments

Determine preset from `$ARGUMENTS` or Smart-Route.

## Step 2: Gather Source-of-Truth Values

```bash
grep 'version' pyproject.toml
find voice-gateway/plugins -maxdepth 1 -type d | tail -n +2 | wc -l
grep -c "  - name:" voice-gateway/plugins/*/plugin.yaml 2>/dev/null | awk -F: '{s+=$NF} END {print s}'
find voice-gateway/tests -name "test_*.py" | wc -l
```

> **Windows note:** These commands require Git Bash, WSL, or PowerShell equivalents. `grep`, `find`, `awk`, `wc` are not available in cmd.exe.

## Step 3: Dispatch Scanners (parallel)

See `references/scanner-prompts.md` for exact prompts.

Dispatch via Agent tool, all scanners run **in parallel**. Model: haiku.

## Step 4: Collect and Merge Findings

Merge JSON arrays from all scanners. If all empty → "All docs current" → stop.

## Step 5: Dispatch Editor

See `references/editor-prompt.md`. Model: sonnet. Apply fixes from merged findings.

## Step 6: Commit

```bash
git add docs/ CLAUDE.md INDEX.md README.md .claude/ agents/ voice-gateway/agent.md voice-gateway/persona/ MEMORY.md
git commit -m "docs: sync to v$(grep -oP 'version = \"\K[^\"]+' pyproject.toml)"
```

> **Windows note:** `grep -oP` requires PCRE support. On Windows, use Git Bash or PowerShell's `Select-String`.

## Step 7: Dispatch Auditor (full only)

See `references/auditor-prompt.md`. Model: opus. Run GAP analysis.
