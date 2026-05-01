# Changelog

## v4.4.0 — 2026-05-01

Opus 4.7 friction mitigation — 4 new hooks addressing audit-2 trends
(+21% Wrong-Approach, +28% Buggy-Code, +22% Misunderstood-Request after
4.6→4.7 swap). Builds on the audit-2026-05-01 / Inkohärenz-Behebung work.

### Added — 4 New Hooks (12 → 16, +4 hooks across 4 events)

- **`hooks/false-positive-guard.py`** (UserPromptSubmit + PreToolUse Edit):
  Detects Edit-tool invocations without bug-evidence in recent context.
  UserPromptSubmit branch scans prompt for bug-keywords (DE+EN), stores
  timestamp. PreToolUse Edit branch checks 10-min window; emits advisory
  if no recent evidence. Mitigates 4.7's "false-positive bug invention"
  pattern (audit-2 NEU). DoS-guard for 100KB+ inputs. 47 tests passed.

- **`hooks/org-naming-pre-push.py`** (PreToolUse Bash, matcher: git push):
  Reads cwd's .git/config, parses GitHub org from origin URL, classifies
  against allowlist (AI-Engineering-at, LEEI1337, FoxLabs-ai). Warns on
  typo-org `AI-Engineerings-at` (server-redirected, but local URLs need
  `git remote set-url`). Default mode: advisory only. 40 tests passed.

- **`hooks/ahead-of-remote-warning.py`** (SessionStart):
  Iterates a watch-list (default: phantom-ai, nomos, zeroth, Playbook01,
  wiki) and runs `git rev-list --count origin/<branch>..HEAD` (no fetch,
  pure local). Emits advisory if any repo is ≥5 ahead, critical at ≥20.
  Addresses nomos-97-unpushed pattern from today's audit. 13 tests passed.

- **`hooks/working-set-watch.py`** (SessionStart):
  Scans `~/Downloads/` and `~/Documents/Downloads/` for strategy files
  (Action_Plan*, DEC-*, *_Concept_*, Compliance_*, Lineage_*, M0*) older
  than 7 days (warn) / 30 days (critical). Emits migration advisory
  pointing at `zeroth/decisions/` or `zeroth/concepts/`. Addresses the
  "Action Plan v1.0 lived unversioned in Downloads/" pattern. 20 tests
  passed.

### Changed

- `hooks/hooks.json`: 13 → 18 hook commands (4 new files registered).
  H1 false-positive-guard registered twice (UserPromptSubmit + PreToolUse
  Edit). H2-H4 each register once.
- `.claude-plugin/plugin.json`: version 4.3.0 → 4.4.0.

### Tests

- 120 new tests across 4 hooks (47+40+13+20).
- All hooks ruff-clean (format + check).
- Pattern-Compliance review (Judge A): 7/9, blocker fixed before commit.
- Security/Performance review (Judge B): 3 critical findings (path-traversal,
  race-condition in lib/state.py — separately filed; DoS-guard added in H1).

### Filed for Follow-up (out-of-scope, lib/state.py-wide)

- Path-Traversal: session_id not validated, allows `../etc/passwd`-style
  escape from STATE_DIR. Affects all hooks. Filed in ERPNext.
- Race-Condition: concurrent `state.save()` in different hooks may
  produce last-write-wins data loss. Filed in ERPNext.

### References

- Audit reports: `Documents/audit-2026-05-01/`
- Master fix list: `audit-2026-05-01/MASTER-FIX-EXECUTION.md`
- Plan: `~/.claude/plans/jaundder-plan-hashed-tiger.md`

---

## v4.3.0 — 2026-04-17/18

Hook-layer test coverage (+99 tests, 127→226) + session lessons +
multi-level audit with sub-agents.

### Added
- **`tests/test_hook_wrapper.py`** (20 tests): `safe_hook` decorator
  exit-code guarantee, log rotation at MAX_LOG_SIZE, error log format
  (timestamp + hook name + traceback), `get_recent_errors` parsing,
  subprocess integration with real hook scripts. 94% coverage of
  `hooks/lib/hook_wrapper.py`.
- **`tests/test_correction_detect.py`** (57 tests): DE+EN correction
  patterns (stop/correction/frustration severities), false-positive
  guards ("nein danke", "ja oder nein?", diagnostic questions), S10
  escalation at count>=2, subprocess integration with stdin JSON.
- **`tests/test_session_state.py`** (22 tests): `SessionState`
  roundtrip, defaults merging (deep-copy isolation across instances),
  prompt_count + is_initialized properties, corruption recovery
  (malformed JSON + missing files), cleanup_stale/cleanup_legacy.
  92% coverage of `hooks/lib/state.py`.
- **`plans/HANDOVER-2026-04-18.md`** — session handover with state
  snapshot, PR #12 + #14 status, track completion notes, post-session
  audit findings.
- **`self-improving/corrections.md.example`** (+3 C-claims):
  - **C-CLAIM03** — silent baseline-backfill wipe during mechanical
    refactor (read-path hardening + tests/test_statusline_stats.py
    prevention).
  - **C-BRANCH01** — committed on wrong branch twice this session
    (branch-name as part of commit contract).
  - **C-MSYS01** — gh api paths rewritten by Git Bash on Windows
    (`MSYS_NO_PATHCONV=1` or `repos/...` form).

### Changed
- **`.claude-plugin/plugin.json`** version 4.2.0 → 4.3.0. Description
  updated: "127-test coverage" → "226-test coverage incl. hook layer
  (wrapper 94%, state 92%)".

### Notes
- **PR #12 (plugins-ci.yml submodule-aware)** — CI blocked on
  GitHub Actions Org-Quota for AI-Engineering-at. All runners fail in
  2–3s without step logs. Repo was made public to eliminate the
  private-submodule auth barrier (verified: no credentials in history,
  only 5 doc-refs to RFC1918 LAN IPs).
- **PR #14 (services/comfyui-build submodule registration)** — same
  CI quota blocker. Created private repo
  `AI-Engineering-at/comfyui-build`, pushed 3 existing commits,
  registered in phantom-ai's `.gitmodules`, absorbed inner `.git/` via
  `git submodule absorbgitdirs`.
- **Audit (4 sub-agents in parallel)** — Security: GO (public-switch
  was safe). Test-Quality: 7.7/10 (S10-escalation test asserts output,
  not state-file — fix deferred to next session). Architecture: 3×P1
  items (main's orphan gitlink, .99/.210 private-repo access, Rule 24
  coverage gap). Documentation: 3×P1 fixed (test count 127→226 in
  plugin.json + HANDOVER, new v4.3.0 CHANGELOG entry).

---

## v4.2.0 — 2026-04-17

Session 2: Auto-sync architecture fix + test coverage expansion +
pathlib migration + phantom-ai CI gates.

### Added
- **Git submodule architecture**: `phantom-ai/meta-skills` is now a git
  submodule pointing at `github.com/AI-Engineering-at/meta-skills-plugin`.
  phantom-ai tracks only the SHA pointer; auto-sync (`git pull --ff-only`)
  no longer overwrites local meta-skills edits. Root-cause fix for
  C-CLAIM02 from session 2026-04-16/17.
- **`phantom-ai/.claude/rules/24-meta-skills-sync.md`** — workflow +
  bump procedure + multi-machine setup + rollback documentation.
- **`tests/test_hardening_run.py`** — 45 tests for scripts/hardening-run.py:
  `CheckResult`, `parse_ruff`/`validate`/`eval`/`pycompile`/`json_schema`,
  `_sanitize` PII substitutions (plugin_root, repo_root, home, python),
  `run_check` subprocess (success, nonzero rc, FileNotFoundError, timeout,
  cwd Path-vs-str), `write_log`. Subprocess coverage guards the pathlib
  migration.
- **`tests/test_validate.py`** — 34 tests for scripts/validate.py:
  `parse_frontmatter` (no FM, missing end marker, multiline description,
  JSON arrays, fallback split, colon-in-value), `VALID_MODELS`
  parametrized (9 accepted incl. opus-4-7, 6 rejected incl. gpt-4),
  `VALID_COMPLEXITY`, `validate_component` (missing fields,
  location-specific rules, team consistency).
- **`tests/test_statusline_stats.py`** — 23 tests for the newly-extracted
  `prune_stats` + `compute_sigma` in statusline_lib: boundary semantics
  (> vs >= at cutoff_ts), baseline-* prefix survival, None-ts handling,
  input mutation safety, declared-sessions replacement, empty + mixed
  state edge cases.
- **`scripts/statusline_lib.py`**: `prune_stats()` + `compute_sigma()` +
  `BASELINE_PREFIX` + `BASELINE_KEY` constants. Extracted from inline
  statusline.py logic so the stats-file handling is unit-testable.
  Strict superset of old inline behavior (None-ts now graceful instead
  of TypeError).
- **Read-path hardening in `scripts/statusline.py`**: differentiates
  "missing file" from "exists-but-corrupt". A corrupt JSON read no
  longer silently wipes the baseline-backfill entry.

### Fixed
- **All 103 ruff lint errors → 0** across 35 files (hooks/, hooks/lib/,
  scripts/). Every ruff rule in default config now passes.
- **Pathlib migration (PTH* rules)**:
  `os.path.dirname(os.path.abspath(__file__))` → `Path(__file__).resolve().parent`
  (9 hook sys.path.insert blocks); `os.getcwd()` → `Path.cwd()`
  (11 sites); `os.path.basename()` → `Path().name` (3);
  `os.path.expanduser()` → `Path().expanduser()` (3);
  `os.path.exists()` → `Path().exists()`; `os.makedirs()` →
  `Path().mkdir(parents=True)`; `os.replace()` → `Path().replace()`;
  `open(path)` → `Path(path).open()` (21 sites).
- **Style migrations**: E701 one-line colons expanded (13 sites);
  E741 `l` → `ln` (6); SIM102 nested ifs → single `and` (7);
  SIM105 try/except/pass → contextlib.suppress; SIM115 bare open →
  context-manager; N806 UPPERCASE constants in functions: noqa
  documented; N802 `SEP()` → `sep()` + legacy alias; RUF013 implicit
  Optional → `str | None`; RUF034 useless ternary simplified;
  F401 unused os + psutil-probe documented.
- **`.github/workflows/plugins-ci.yml`** (via phantom-ai PR #12): adds
  `format-tests` job (pytest boundary tests) + `hardening-evidence`
  job (artifact capture). Submodule-aware checkout: all 7 jobs run
  `git submodule update --init meta-skills` after the shallow clone
  (avoids recursive init tripping over phantom-ai's pre-existing
  services/comfyui-build orphan).

### Changed
- **`phantom-ai` repo structure**: `meta-skills/` converted from regular
  directory (174 tracked files) to git submodule pointer (1 line in
  `.gitmodules`, 1 gitlink). Working tree contents identical; pointer
  now pins exact SHA.
- **Phase ordering of B/D**: test coverage (D) landed first as a safety
  net, then pathlib migration (B) used those tests to guard against
  mechanical regressions during the 35-file sweep. Zero pytest
  regressions across the entire B diff.
- **Plugin.json version** bumped to 4.2.0 to reflect the expanded
  quality surface (127 tests, lint-clean, pathlib-native).

### Notes
- PR #12 in phantom-ai lands the CI gates; waits on final CI + review.
- Multi-machine rollout of the submodule conversion is documented in
  `phantom-ai/.claude/rules/24-meta-skills-sync.md` §"Erstmaliger Setup".
- The pre-existing `services/comfyui-build` orphan in phantom-ai is
  noted but left for a separate cleanup PR.

---

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
