"""Pure formatters and parsers extracted from statusline.py.

Extracted for unit testability. statusline.py imports from here.
No ANSI codes, no subprocess. File I/O limited to reading .git/HEAD.
"""

import re
from pathlib import Path

MODEL_RE = re.compile(r"(opus|sonnet|haiku|fable)-(\d+)(?:-(\d+))?")


def fk(n):
    """Format token count: k -> M -> B -> T scale.

    Numbers that would round up to the next tier (e.g. 999_950 showing as
    '1000.0k') are promoted to the next tier so we never render an ambiguous
    '1000X' unit.
    """
    if n >= 1_000_000_000_000:
        return f"{n / 1_000_000_000_000:.1f}T"
    if n >= 1_000_000_000:
        v = n / 1_000_000_000
        return f"{n / 1_000_000_000_000:.1f}T" if v >= 999.95 else f"{v:.1f}B"
    if n >= 1_000_000:
        v = n / 1_000_000
        return f"{n / 1_000_000_000:.1f}B" if v >= 999.95 else f"{v:.1f}M"
    if n >= 1_000:
        v = n / 1_000
        # fk uses :.0f for k → round-up promotion threshold is 999.5
        return f"{n / 1_000_000:.1f}M" if v >= 999.5 else f"{v:.0f}k"
    return str(int(n)) if isinstance(n, float) and n.is_integer() else str(n)


def fcost(c):
    """Format cost: k -> M -> B -> T scale. Below $1k keeps cents.

    Boundary-safe: values that would round up into the next tier's unit
    (e.g. $999_999.99 showing as '$1000k') are promoted to the next tier.
    """
    if c >= 1_000_000_000_000:
        return f"${c / 1_000_000_000_000:.1f}T"
    if c >= 1_000_000_000:
        v = c / 1_000_000_000
        return f"${c / 1_000_000_000_000:.1f}T" if v >= 999.95 else f"${v:.1f}B"
    if c >= 1_000_000:
        v = c / 1_000_000
        return f"${c / 1_000_000_000:.1f}B" if v >= 999.95 else f"${v:.1f}M"
    if c >= 1_000:
        v = c / 1_000
        # fcost uses :.0f for k → promotion threshold at 999.5
        return f"${c / 1_000_000:.1f}M" if v >= 999.5 else f"${v:.0f}k"
    return f"${c:.2f}"


def parse_model_id(model_id):
    """Parse Claude model ID into (short_label, family).

    Returns tuple of (label, family) where family in
    {'opus','sonnet','haiku','fable',None}.

    Covers both the legacy two-number scheme (opus-4-7) and the Claude 5
    family's single-number IDs (sonnet-5, opus-5, fable-5 — no minor digit).

    Examples:
        'claude-opus-4-7'             -> ('O4.7', 'opus')
        'claude-sonnet-4-6'           -> ('S4.6', 'sonnet')
        'claude-haiku-4-5-20251001'   -> ('H4.5', 'haiku')
        'claude-opus-5-0'             -> ('O5.0', 'opus')
        'claude-sonnet-5'             -> ('S5', 'sonnet')
        'claude-opus-5'               -> ('O5', 'opus')
        'claude-fable-5'              -> ('F5', 'fable')
        'claude-opus-unknown'         -> ('Opus', 'opus')   # family fallback
        'unknown'                     -> ('unknow', None)
        ''                            -> ('?', None)
        None                          -> ('?', None)
    """
    if not model_id:
        return ("?", None)
    lower = str(model_id).lower()
    m = MODEL_RE.search(lower)
    if m:
        family, maj, minor = m.group(1), m.group(2), m.group(3)
        label = f"{family[0].upper()}{maj}" if minor is None else f"{family[0].upper()}{maj}.{minor}"
        return (label, family)
    for fam in ("opus", "sonnet", "haiku", "fable"):
        if fam in lower:
            return (fam.capitalize()[:4], fam)
    return (lower[:6], None)


def parse_rate_limit_tier(tier: str | None) -> str | None:
    """Map ``oauthAccount.organizationRateLimitTier`` to a short plan label.

    Returns None when the string is missing or has no recognized keyword,
    so the caller can fall back to a heuristic rather than show a wrong
    label (e.g. ``"default_claude_max_20x"`` -> ``"Max"``).
    """
    if not tier:
        return None
    t = str(tier).lower()
    for keyword, label in (
        ("enterprise", "Enterprise"),
        ("team", "Team"),
        ("max", "Max"),
        ("pro", "Pro"),
        ("free", "Free"),
    ):
        if keyword in t:
            return label
    return None


def read_account_created_ts(config_path) -> float | None:
    """Read oauthAccount.accountCreatedAt from the Claude Code account config
    and return it as an epoch timestamp, or None on any failure.

    Deliberately reads the account-level file (same on every machine logged
    into this account), not a per-machine cache — this is what lets the
    dynamic baseline below work identically on a second PC/terminal with no
    manual setup (found 2026-07-26: a manually-seeded baseline in
    statusline-alltime.json only existed on the one Mac it was written on).
    """
    import json as _json

    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = _json.load(f)
        raw = (cfg.get("oauthAccount") or {}).get("accountCreatedAt")
        if not raw:
            return None
        from datetime import datetime

        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


MIN_RATE_BASIS_DAYS = 3.0

# Verified 2026-07-26 via llm_bridge/claude_code_usage.py's monthly_history
# (the properly-deduped, complete reader — replaces an earlier, less
# rigorous manual estimate that undercounted by ~50-100%, found when the
# CLI's and Bridge's numbers were compared and disagreed). Real measured
# span 2026-05-20..07-26 (67 days): $10,415.83 cost, 95,102,422 tokens
# (in+out). This is a point-in-time snapshot, not a live sync -- the Bridge
# recomputes this fresh from real transcripts every time (its measured
# window always extends to "now"), so this constant will drift stale again
# as more real days accumulate. Recalibrate periodically by rerunning the
# Bridge reader, not by guessing; do not hand-edit without a fresh number.
AUDITED_DAILY_RATE_COST = 10415.83 / 67.0
AUDITED_DAILY_RATE_TOKENS = 95_102_422 / 67.0


def read_user_confirmed_continuous_usage(config_path) -> bool:
    """Read an explicit user confirmation that overrides MIN_RATE_BASIS_DAYS.

    This is NOT a heuristic and NOT auto-detected — it's set only when the
    account holder has explicitly and directly stated (repeatedly, in this
    case) that usage has been continuous since account creation. That is a
    real fact about their own account, not a guess from too little data, so
    it's allowed to bypass the automatic minimum-data guard. Absence of the
    file means no confirmation was given — falls back to the automatic
    threshold, never assumes confirmation (KEIN-MOCK).
    """
    import json as _json

    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = _json.load(f)
        return bool(cfg.get("confirmed_continuous_usage_since_account_creation"))
    except Exception:
        return False


def compute_dynamic_baseline(
    all_stats: dict, account_created_ts: float | None, now_ts: float, user_confirmed: bool = False
) -> tuple[float, float]:
    """Compute a NOT-persisted (cost, tokens) estimate for the gap between
    account creation and the earliest locally-tracked real session.

    Recomputed fresh on every invocation from whatever real local data
    currently exists — never written back to disk, so it stays in sync as
    more real sessions accumulate and works identically on any machine
    logged into the same account (no manual per-machine seeding).

    ``user_confirmed`` bypasses the MIN_RATE_BASIS_DAYS guard below — see
    read_user_confirmed_continuous_usage. Without it, returns (0.0, 0.0) —
    never a fabricated number — when there isn't yet
    enough real local data to establish a rate (fewer than
    MIN_RATE_BASIS_DAYS elapsed since the earliest real session — e.g. on
    the day the statusbar is first activated, 2 sessions an hour apart would
    otherwise look like "a day's rate" and get extrapolated across the whole
    gap, producing a wildly inflated number; found 2026-07-26), or no
    account creation date is available (KEIN-MOCK: a real anchor date AND a
    real, sufficiently-measured rate are both required, or nothing shown).
    """
    real_entries = [s for k, s in all_stats.items() if not k.startswith(BASELINE_PREFIX)]
    if not real_entries or account_created_ts is None:
        return 0.0, 0.0
    timestamps = [s.get("ts", now_ts) for s in real_entries]
    earliest_real_ts = min(timestamps)
    if account_created_ts >= earliest_real_ts:
        return 0.0, 0.0
    real_span_days = (now_ts - earliest_real_ts) / 86400.0
    gap_days = (earliest_real_ts - account_created_ts) / 86400.0

    if real_span_days < MIN_RATE_BASIS_DAYS:
        if not user_confirmed:
            return 0.0, 0.0
        # Confirmed, but today's live sample (possibly a single unusually
        # heavy/light session) is too small to trust as "the daily rate" —
        # extrapolating IT across ~9 months would repeat the exact class of
        # bug this guard exists for, just with permission. Use the rate from
        # a full 67-day transcript audit instead (2026-05-20..07-26, verified
        # directly against ~/.claude/projects/**/*.jsonl, not a guess) —
        # a real, stable, multi-week rate rather than a few hours of noise.
        daily_cost = AUDITED_DAILY_RATE_COST
        daily_tokens = AUDITED_DAILY_RATE_TOKENS
        return daily_cost * gap_days, daily_tokens * gap_days

    real_cost = sum((s.get("cost") or 0) for s in real_entries)
    real_tokens = sum((s.get("tokens") or 0) for s in real_entries)
    return (real_cost / real_span_days) * gap_days, (real_tokens / real_span_days) * gap_days


BASELINE_PREFIX = "baseline-"
BASELINE_KEY = "baseline-backfill"


def prune_stats(stats: dict, cutoff_ts: float) -> dict:
    """Drop entries older than cutoff_ts. baseline-* keys always survive.

    Contract: never mutates the input dict. The ``baseline-`` prefix is the
    opt-out for pre-plugin history (cf. statusline.py backfill design).
    """
    return {
        k: v
        for k, v in stats.items()
        if k.startswith(BASELINE_PREFIX) or (v.get("ts", 0) or 0) > cutoff_ts
    }


def compute_sigma(stats: dict) -> tuple[float, int, int]:
    """Return (total_cost, total_tokens, session_count) across all entries.

    Every non-baseline entry counts as one session. A ``baseline-backfill``
    entry may declare a larger ``sessions`` count representing pre-plugin
    history; that declared count replaces the +1 the entry would otherwise
    contribute.
    """
    cost = sum((s.get("cost") or 0) for s in stats.values())
    tokens = sum((s.get("tokens") or 0) for s in stats.values())
    baseline = stats.get(BASELINE_KEY) or {}
    real_sessions = len(stats) - (1 if baseline else 0)
    declared_baseline = baseline.get("sessions", 0) if baseline else 0
    return cost, tokens, real_sessions + declared_baseline


# ═══════════════════════════════════════════════════════════════
# GIT BRANCH DETECTION (C-BRANCH01 soft-signal, replaces branch-guard)
# ═══════════════════════════════════════════════════════════════
MAIN_BRANCHES = {"main", "master"}


def _find_git_head(start: Path) -> Path | None:
    """Walk up from start to find .git/HEAD. Returns path or None.

    Handles both regular repos (.git is a dir) and submodules (.git is a
    file with "gitdir: <path>" pointing to the real .git dir in the
    superproject's .git/modules/.
    """
    try:
        p = start.resolve() if start and str(start) else Path.cwd()
    except Exception:  # noqa: BLE001
        return None
    for parent in (p, *p.parents):
        head = parent / ".git" / "HEAD"
        if head.is_file():
            return head
        gitfile = parent / ".git"
        if gitfile.is_file():
            try:
                txt = gitfile.read_text(encoding="utf-8").strip()
            except OSError:
                continue
            if txt.startswith("gitdir:"):
                try:
                    gd = (parent / txt.split(":", 1)[1].strip()).resolve()
                except Exception:  # noqa: BLE001
                    continue
                alt = gd / "HEAD"
                if alt.is_file():
                    return alt
    return None


def current_branch(cwd_str: str) -> tuple[str | None, str]:
    """Read current git branch from .git/HEAD without invoking git subprocess.

    Returns ``(branch_name, severity)``:
      * ``severity == "main"``     — on main/master (statusline uses dim color)
      * ``severity == "feature"``  — on any non-main branch (yellow warning)
      * ``severity == "detached"`` — detached HEAD state (red warning, name is ``@<shortsha>``)
      * ``severity == "none"``     — no git repo detected, ``branch_name`` is None

    cwd_str of ``""`` falls back to ``Path.cwd()``. Any filesystem or parse
    error returns ``(None, "none")`` — the caller should treat that as
    "hide the branch chip".
    """
    try:
        start = Path(cwd_str) if cwd_str else Path.cwd()
    except Exception:  # noqa: BLE001
        return None, "none"
    head = _find_git_head(start)
    if head is None:
        return None, "none"
    try:
        txt = head.read_text(encoding="utf-8").strip()
    except OSError:
        return None, "none"
    if not txt:
        return None, "none"
    if txt.startswith("ref:"):
        ref = txt[4:].strip()
        # ref: refs/heads/<branch> — branch may contain slashes (feat/area/sub)
        if ref.startswith("refs/heads/"):
            name = ref[len("refs/heads/") :]
            sev = "main" if name in MAIN_BRANCHES else "feature"
            return name, sev
        # Non-heads ref (e.g. refs/tags/X) — treat as detached-like
        return ref, "detached"
    # Detached HEAD — plain SHA
    return f"@{txt[:7]}", "detached"


def current_worktree_task(cwd_str: str) -> dict | None:
    """Detect if cwd is inside an agent-worktree (TASK-2026-00629 worktree pattern).

    Walks up from cwd looking for ``.agent-worktree.lock`` (created by
    ``bin/agent-worktree.sh create``). Returns a dict with the lock fields
    (task_id, slug, branch, base_ref, created_at, ...) or ``None`` when no
    lock file is found within the parent chain.

    Read-only and silent on errors — every caller treats ``None`` as "not in
    a worktree, hide worktree chip".

    Lock file format (key=value lines, written by agent-worktree.sh::cmd_create):
        task_id=TASK-2026-00629
        slug=phase-b-integration
        branch=chore/TASK-2026-00629-phase-b-integration
        base_ref=origin/main
        created_at=2026-04-25T21:23:00Z
        created_by=joe
        pid=12345
    """
    try:
        start = Path(cwd_str) if cwd_str else Path.cwd()
    except Exception:  # noqa: BLE001
        return None
    cur = start
    for _ in range(40):  # bounded — same depth used by _find_git_head
        lock = cur / ".agent-worktree.lock"
        if lock.is_file():
            try:
                txt = lock.read_text(encoding="utf-8")
            except OSError:
                return None
            fields: dict[str, str] = {}
            for line in txt.splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    fields[k.strip()] = v.strip()
            if "task_id" in fields and fields["task_id"]:
                return fields
            return None
        if cur.parent == cur:
            return None
        cur = cur.parent
    return None
