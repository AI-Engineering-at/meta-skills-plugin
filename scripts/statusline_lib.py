"""Pure formatters and parsers extracted from statusline.py.

Extracted for unit testability. statusline.py imports from here.
No ANSI codes, no subprocess. File I/O limited to reading .git/HEAD.
"""
from __future__ import annotations


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


# ═══════════════════════════════════════════════════════════════
# ALL-TIME AGGREGAT
# ═══════════════════════════════════════════════════════════════
# Bis 2026-07-26 standen hier zwei handgesetzte Konstanten
# (AUDITED_DAILY_RATE_COST/_TOKENS) plus eine Heuristik, die unter
# MIN_RATE_BASIS_DAYS auf sie zurückfiel. Beide sind entfernt. Warum:
#
#   * Eine Konstante mit Pflege-Auflage ("recalibrate periodically") wird
#     nicht gepflegt. Sie war zweimal gesetzt und zweimal falsch.
#   * Die Σ-Token-Zahl war um Faktor ~110 zu klein, weil sie nur in+out
#     summierte — 96 % des echten Volumens sind Cache-Token.
#   * Der MIN_RATE_BASIS_DAYS-Zweig hätte nach 3 Tagen still die Basis
#     gewechselt (Konstante → Live-Rate aus einer 90-Tage-geprunten Datei)
#     und die Σ-Werte ohne Warnung springen lassen.
#
# Stattdessen rechnet ``scripts/usage_aggregate.py`` das Aggregat aus den
# echten Transkripten (dedupliziert, Cache eingerechnet, gegen Anthropics
# eigenen cost.total_cost_usd kalibriert) und legt es hier ab. Die Leiste
# liest nur — der Vollscan gehört nicht in einen 1-Sekunden-Render.
USAGE_AGG_FILE = "~/.claude/statusline-usage-agg.json"


def read_usage_agg(agg_path) -> dict | None:
    """Aggregat lesen, oder ``None`` wenn es fehlt/kaputt/leer ist.

    ``None`` heißt für die Anzeige: **keine Σ-Werte zeigen**, nicht "null
    Verbrauch". Eine fehlende Datei darf nie als 0 erscheinen (A33).
    """
    import json as _json

    try:
        with open(agg_path, encoding="utf-8") as f:
            agg = _json.load(f)
    except Exception:
        return None
    if not isinstance(agg, dict) or not agg.get("stand"):
        return None
    alltime = agg.get("alltime")
    if not isinstance(alltime, dict) or not alltime.get("tokens_all"):
        return None
    return agg


def assumption(agg: dict | None, key: str, default=None):
    """Einen Annahmewert aus dem Aggregat holen.

    Die Annahmen liegen im Aggregat mit ``stand`` + ``quelle``; Einträge ohne
    Herkunft hat ``usage_aggregate.load_assumptions`` bereits verworfen. Hier
    kommt also nur an, was dokumentiert ist.
    """
    if not agg:
        return default
    entry = (agg.get("assumptions") or {}).get(key)
    if isinstance(entry, dict) and "value" in entry:
        return entry["value"]
    return default


def money(usd: float, agg: dict | None) -> tuple[float, str]:
    """→ ``(betrag, symbol)``. Rechnet nach EUR um, **wenn** ein dokumentierter
    Kurs vorliegt; sonst bleibt es USD.

    Kein stilles Umlabeln: ohne ``usd_eur_rate`` im Annahmen-Register zeigt die
    Leiste ``$``, statt einen Dollarbetrag als ``€`` auszugeben.
    """
    rate = assumption(agg, "usd_eur_rate")
    if isinstance(rate, (int, float)) and rate > 0:
        return usd * float(rate), "€"
    return usd, "$"


# ═══════════════════════════════════════════════════════════════
# SESSION-TOKEN AUS DEM TRANSKRIPT (ersetzt den Kontextfenster-Snapshot)
# ═══════════════════════════════════════════════════════════════
# ``context_window.total_input/output_tokens`` aus dem Hook-JSON ist ein
# Schnappschuss des AKTUELLEN Kontextfensters und resettet bei /compact —
# daher die absurden ``out:129`` / ``out:1k`` bei einer 3-Stunden-Session.
# Das Transkript hat die Wahrheit, inklusive der Cache-Felder, die das
# Hook-JSON überhaupt nicht liefert.
#
# Inkrementell: Sidecar hält pro Datei ``offset`` plus die deduplizierte
# ``requestId -> usage``-Abbildung. Pro Render werden nur die angehängten
# Bytes gelesen. Ohne das würde die Leiste jede Sekunde ein mehrere MB
# großes JSONL neu parsen.
SESSION_CACHE_DIR = "~/.claude/statusline-session-cache"


def read_session_usage(session_id: str, projects_dir=None, cache_dir=None) -> dict | None:
    """Kumulative Token dieser Session aus ihrem Transkript.

    → ``{"input","output","cache_read","cache_write","cache_hit_ratio","records"}``
    oder ``None``, wenn kein Transkript gefunden wurde. ``None`` heißt „unbekannt",
    nicht „null" — der Aufrufer zeigt dann ``—`` statt einer erfundenen 0.
    """
    import json as _json

    if not session_id or session_id == "unknown":
        return None
    projects = Path(projects_dir) if projects_dir else Path("~/.claude/projects").expanduser()
    cdir = Path(cache_dir) if cache_dir else Path(SESSION_CACHE_DIR).expanduser()
    side = cdir / f"{session_id}.json"

    state = {}
    try:
        with side.open(encoding="utf-8") as f:
            loaded = _json.load(f)
        if isinstance(loaded, dict):
            state = loaded
    except Exception:
        state = {}

    files = []
    try:
        for main in projects.glob(f"**/{session_id}.jsonl"):
            files.append(main)
            files.extend(sorted((main.parent / session_id).glob("**/*.jsonl")))
    except OSError:
        return None
    if not files:
        return None

    changed = False
    for path in files:
        key = str(path)
        entry = state.get(key) if isinstance(state.get(key), dict) else {}
        offset = int(entry.get("offset") or 0)
        per_key = entry.get("per_key") if isinstance(entry.get("per_key"), dict) else {}
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size < offset:  # Datei wurde ersetzt/gekürzt → von vorn
            offset, per_key = 0, {}
        if size == offset and per_key:
            state[key] = {"offset": offset, "per_key": per_key}
            continue
        try:
            fh = path.open("r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            try:
                fh.seek(offset)
            except (OSError, ValueError):
                fh.seek(0)
                per_key = {}
            for line in fh:
                if '"type":"assistant"' not in line and '"type": "assistant"' not in line:
                    continue
                try:
                    obj = _json.loads(line)
                except Exception:
                    continue
                if obj.get("type") != "assistant":
                    continue
                msg = obj.get("message")
                if not isinstance(msg, dict):
                    continue
                usage = msg.get("usage")
                if not isinstance(usage, dict):
                    continue
                dedup_key = obj.get("requestId") or msg.get("id") or obj.get("uuid")
                if dedup_key is None:
                    continue
                creation = usage.get("cache_creation")
                if isinstance(creation, dict) and creation:
                    write = int(creation.get("ephemeral_5m_input_tokens") or 0) + int(
                        creation.get("ephemeral_1h_input_tokens") or 0
                    )
                else:
                    write = int(usage.get("cache_creation_input_tokens") or 0)
                # letzte Zeile gewinnt — die Zeilen sind Streaming-Schnappschüsse
                per_key[str(dedup_key)] = [
                    int(usage.get("input_tokens") or 0),
                    int(usage.get("output_tokens") or 0),
                    int(usage.get("cache_read_input_tokens") or 0),
                    write,
                ]
            try:
                offset = fh.tell()
            except OSError:
                offset = size
        state[key] = {"offset": offset, "per_key": per_key}
        changed = True

    inp = out = cread = cwrite = recs = 0
    for entry in state.values():
        if not isinstance(entry, dict):
            continue
        for vals in (entry.get("per_key") or {}).values():
            if not isinstance(vals, list) or len(vals) != 4:
                continue
            inp += vals[0]
            out += vals[1]
            cread += vals[2]
            cwrite += vals[3]
            recs += 1

    if changed:
        try:
            cdir.mkdir(parents=True, exist_ok=True)
            tmp = side.with_suffix(f".{__import__('os').getpid()}.tmp")
            with tmp.open("w", encoding="utf-8") as f:
                _json.dump(state, f, separators=(",", ":"))
            tmp.replace(side)
        except Exception:
            pass

    denom = inp + cread + cwrite
    return {
        "input": inp,
        "output": out,
        "cache_read": cread,
        "cache_write": cwrite,
        "records": recs,
        "cache_hit_ratio": (cread / denom) if denom else None,
    }


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
