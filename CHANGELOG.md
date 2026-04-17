# Changelog

## v4.1.0 — 2026-04-17

Hardening pass + Opus 4.7 statusline support. PR #1 merged.

### Added
- **Opus 4.7 model detection** in statusline via regex
  (`scripts/statusline_lib.py:parse_model_id`). Future-proof for 5.x — no
  hardcoded labels.
- **T-scale (trillion)** for token + cost formatters; cost gains `$k`
  formatting at >= $1k, `$M` at >= $1M, `$B` and `$T` for headroom.
- **Boundary promotion**: `fcost(999_999.99)` now returns `$1.0M` instead
  of the ambiguous `$1000k`. Same logic at every k->M->B->T transition.
- **`scripts/hardening-run.py`**: runs all 8 SCAN checks from
  `skills/harden/references/scan-checks.md`, captures per-check log files
  to `oversight/hardening-<date>/`, generates a markdown report that
  links to every evidence file. Path-sanitized.
- **`tests/test_statusline_formatters.py`**: 25 boundary tests for fk,
  fcost, parse_model_id (incl. dot/dash separator handling, unknown IDs).
- **`scripts/statusline_lib.py`**: pure formatters extracted from
  statusline.py for unit testability. No I/O, no ANSI, no side-effects.
- **`oversight/cleanup-log.md`**: ledger of untracked file deletions
  (Windows shell-redirect leftovers etc.) since git cannot record those.
- **`.github/workflows/ci.yml`**: standalone CI for the public repo with
  7 jobs (syntax, json, hooks, skills, format-tests, hardening-evidence,
  harden-scan).
- **Stats-file backfill** support in statusline.py: `baseline-backfill`
  entries declare a representative `sessions` count and survive the
  90-day prune.
- **`oversight/ci-gates-proposal.patch`** and matching `.md` for landing
  the equivalent CI jobs in the internal phantom-ai workflow.

### Fixed
- `hooks/quality-gate.py`: missing `import subprocess` (F821 latent bug
  in the gh-run-status code path).
- 148 ruff `--fix` auto-fixes + 30 unsafe-fixes across hooks/ and
  scripts/. 5 `# noqa: E402` for intentional sys.path manipulation
  before sibling imports. 1 `# noqa: F401` for psutil availability probe.
- `scripts/statusline.py`: silent revert from commit 9acece0 reverted via
  cherry-pick of 9d7d826's content + intended docstring sanitization.

### Changed
- `scripts/validate.py`: `claude-opus-4-7` added to `VALID_MODELS`
  (4-6 retained for backwards compat).
- Statusline span format: now shows days up to 365 (was: months after 30),
  then years.
- `hooks/lib/config.py`, `hooks/lib/services.py`, `hooks/session-stop.py`,
  `scripts/plugin-setup.py`, `scripts/session-end-sync.py`: replaced
  hardcoded internal IPs (`10.40.10.82`) with `.local` placeholders +
  env-var/vault overrides. Vault-first lookup semantics preserved.
- Path examples in docstrings: `C:/Users/Legion/...` -> `${CLAUDE_PLUGIN_ROOT}/...`
  or `~/...`.

### Removed
- `oversight/hardening-2026-04-17/` log subdirs and similar future runs:
  gitignored (uploaded as CI artifacts on each run instead).
- `self-improving/corrections.md`: per-user state, gitignored. Template at
  `self-improving/corrections.md.example`.

### Docs
- `oversight/hardening-2026-04-16.md`: audit-caveat header, links to
  cleanup-log + 2026-04-17 sanitized report.
- `oversight/hardening-2026-04-17.md`: regenerated with sanitized paths
  (no absolute home/user references). Reproduction section uses
  `<plugin_root>` placeholders.
- `plans/HANDOVER-2026-04-17.md`: state at end of session 2026-04-16/17,
  blocker analysis, next-session quickstart.
- `plans/ROADMAP-v4.1-no-compromises.md`: 5-phase roadmap with atomic
  deliverables, verification, rollback per phase.
- `self-improving/corrections.md.example`: lessons C-SCOPE01, C-CALC01,
  C-STOP01, C-INTERP01, C-PROJ01, C-TRUST01, C-CLAIM01, C-CLAIM02 +
  guardrails.

### Notes
- Stats file `~/.claude/statusline-alltime.json` migrated for live use to
  carry a baseline-backfill entry projecting 6.6 months of usage based on
  `/usage` data (82.9M tok/month, 580 sessions/month, $3.8k/month derived
  from Anthropic list pricing × the Models breakdown). Plugin continues to
  sum real per-session data on top.
- Settings hint: point `~/.claude/settings.json -> statusLine.command` at
  `~/.claude/plugins/cache/meta-skills-local/meta-skills/<version>/scripts/statusline.py`
  rather than a working-tree copy that could be auto-synced away.
