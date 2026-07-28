#!/usr/bin/env python3
"""statusline.py — Meta-Skills Statusbar for Claude Code.

Part of the meta-skills universe. Shows context, model, cost, tokens,
rate limits, and all-time Σ stats with rainbow separators and severity colors.

All cost values are REAL from Claude Code (cost.total_cost_usd).
Σ values persist across sessions in ~/.claude/statusline-alltime.json.

Usage in settings.json:
  "statusLine": {
    "type": "command",
    "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/statusline.py"
  }
  (or absolute path to your meta-skills checkout)

Standalone test:
  echo '{"model":{"id":"claude-opus-4-7"},...}' | python3 statusline.py
"""

import colorsys
import contextlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone

# Python 3.9 (macOS-Systeminterpreter) kennt `datetime.UTC` nicht — das gibt es erst
# ab 3.11. Ohne diesen Umweg stirbt der Hook beim Import, endet mit 0, und schreibt nie.
UTC = timezone.utc
from pathlib import Path

# Pure formatters + model parser live in a sibling module for testability.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from statusline_lib import (
    USAGE_AGG_FILE,
    compute_sigma,
    current_branch,
    current_worktree_task,
    fcost,
    fk,
    money,
    parse_model_id,
    parse_rate_limit_tier,
    prune_stats,
    read_account_created_ts,
    read_session_usage,
    read_usage_agg,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = sys.stdin.read()
try:
    data = json.loads(raw)
except Exception:
    print("\033[2m◆ ...\033[0m")
    sys.exit(0)

# ═══════════════════════════════════════════════════════════════
# DATA EXTRACTION
# ═══════════════════════════════════════════════════════════════
ctx = data.get("context_window") or {}
cost_data = data.get("cost") or {}
model_data = data.get("model") or {}
workspace = data.get("workspace") or {}
rate = data.get("rate_limits") or {}
session_id = data.get("session_id") or "unknown"

used_pct = ctx.get("used_percentage") or 0
total_ctx = ctx.get("context_window_size") or 1_000_000
total_in = ctx.get("total_input_tokens") or 0
total_out = ctx.get("total_output_tokens") or 0

cost_usd = cost_data.get("total_cost_usd") or 0
duration_ms = cost_data.get("total_duration_ms") or 0
lines_added = cost_data.get("total_lines_added") or 0
lines_removed = cost_data.get("total_lines_removed") or 0

_raw_model = (
    model_data.get("id")
    or (data.get("model") if isinstance(data.get("model"), str) else None)
    or "unknown"
)
model_id = str(_raw_model).lower()
cwd = workspace.get("current_dir") or data.get("cwd") or ""

r5h = rate.get("five_hour") or {}
r7d = rate.get("seven_day") or {}
r5h_pct = r5h.get("used_percentage")
r7d_pct = r7d.get("used_percentage")
r5h_resets = r5h.get("resets_at")
r7d_resets = r7d.get("resets_at")

session_tok = total_in + total_out

# ═══════════════════════════════════════════════════════════════
# Σ PERSISTENT ALL-TIME STATS
# ═══════════════════════════════════════════════════════════════
STATS_FILE = Path("~/.claude/statusline-alltime.json").expanduser()

# Read-path: differentiate "missing file" from "exists-but-unreadable" so we
# never silently overwrite valid state (esp. baseline-backfill). A corrupted
# JSON read would otherwise reset all_stats to {} and the write-path below
# would permanently erase the baseline.
if STATS_FILE.exists():
    try:
        with STATS_FILE.open(encoding="utf-8") as f:
            all_stats = json.load(f)
        _stats_write_ok = True
    except Exception:
        all_stats = {}
        _stats_write_ok = False
else:
    all_stats = {}
    _stats_write_ok = True

# Prune entries older than 90 days. Baseline-* keys survive (pre-plugin backfill).
all_stats = prune_stats(all_stats, time.time() - (90 * 86400))

# session_tok is a snapshot of the CURRENT context window (ctx.total_input/
# output_tokens), not cumulative session throughput — Claude Code docs confirm
# it resets on /compact. Naively overwriting "tokens" each invocation with this
# raw snapshot silently loses everything before the last reset (found in the
# 2026-07-26 token-usage audit: statusline-alltime.json undercounted real
# transcript totals). Reconstruct a true cumulative value client-side: treat
# session_tok as a monotonic counter and detect wraparound (new < previous
# raw) as a reset, folding the pre-reset peak into a running baseline.
_prev = all_stats.get(session_id) or {}
_prev_raw = _prev.get("tokens_raw", _prev.get("tokens", 0))
_baseline = _prev.get("tokens_baseline", 0)
if session_tok < _prev_raw:
    _baseline += _prev_raw
cumulative_tok = _baseline + session_tok

all_stats[session_id] = {
    "cost": cost_usd,
    "tokens": cumulative_tok,
    "tokens_raw": session_tok,
    "tokens_baseline": _baseline,
    "time_ms": duration_ms,
    "model": model_id,
    "ts": time.time(),
}

if _stats_write_ok:
    tmp = STATS_FILE.with_suffix(STATS_FILE.suffix + f".{os.getpid()}.tmp")
    try:
        # Per-PID tmp name: with 10+ concurrent claude.exe processes all invoking
        # this script, a shared ".tmp" path caused mid-flush interleave → trailing
        # garbage in the final JSON (observed 2026-04-17/18). Per-PID tmp keeps
        # writes isolated; os.replace is atomic per-file so the merge is race-free.
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(all_stats, f, separators=(",", ":"))
        tmp.replace(STATS_FILE)
    except Exception:
        # On Windows, os.replace can raise PermissionError if the target is
        # momentarily open by another claude.exe process reading the file.
        # Clean up the orphaned tmp so we don't litter ~/.claude with
        # statusline-alltime.json.<pid>.tmp files on every failure.
        with contextlib.suppress(Exception):
            tmp.unlink()

# ── All-Time aus dem Aggregat ──────────────────────────────────
# Vorher: zwei handgesetzte Tagesraten plus eine Heuristik, die nach 3 Tagen
# still die Basis gewechselt hätte. Jetzt: scripts/usage_aggregate.py rechnet
# das Aggregat aus den echten Transkripten (dedupliziert, Cache eingerechnet,
# gegen Anthropics cost.total_cost_usd kalibriert); die Leiste liest nur.
# Fehlt das Aggregat, werden KEINE Σ-Werte gezeigt — nicht "0" (A33).
_agg = read_usage_agg(Path(USAGE_AGG_FILE).expanduser())
_alltime = (_agg or {}).get("alltime") or {}
sigma_tokens = int(_alltime.get("tokens_all") or 0)
sigma_saved_usd = float(_alltime.get("saved_usd") or 0)
span_days = float(_alltime.get("days") or 0)

# statusline-alltime.json wird weiter fortgeschrieben (oben) — nicht für die
# Anzeige, sondern weil dort Anthropics echte Session-Kosten landen. Sie sind
# die einzige Referenz, gegen die das Aggregat kalibriert. Die Datei ist damit
# Cache und Kalibrier-Quelle, aber keine Wahrheit über Σ.
_, _, sigma_sessions = compute_sigma(all_stats)

# Aggregat veraltet → Refresh abgekoppelt anstoßen. Der Vollscan (~6 s beim
# ersten Mal, ~0,3 s inkrementell) darf einen 1-Sekunden-Render nie blockieren.
# Marker verhindert, dass jeder Render einen neuen Prozess startet.
_AGG_MAX_AGE_H = 6.0
_agg_stale = _agg is None
if _agg is not None:
    try:
        _stand = datetime.fromisoformat(_agg["stand"])
        _agg_stale = (datetime.now(UTC) - _stand).total_seconds() / 3600.0 > _AGG_MAX_AGE_H
    except Exception:
        _agg_stale = True
if _agg_stale:
    _marker = Path("~/.claude/.statusline-agg-refreshing").expanduser()
    try:
        _fresh_marker = _marker.exists() and (time.time() - _marker.stat().st_mtime) < 600
    except OSError:
        _fresh_marker = False
    if not _fresh_marker:
        with contextlib.suppress(Exception):
            _marker.parent.mkdir(parents=True, exist_ok=True)
            _marker.write_text(str(time.time()), encoding="utf-8")
            import subprocess

            subprocess.Popen(  # noqa: S603
                [sys.executable, str(Path(__file__).resolve().parent / "usage_aggregate.py"),
                 "--force", "--quiet"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

# ═══════════════════════════════════════════════════════════════
# ANSI COLORS
# ═══════════════════════════════════════════════════════════════
R = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def rgb(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"


PURPLE = rgb(114, 102, 234)
CYAN = rgb(86, 182, 194)
MAGENTA = rgb(200, 120, 221)
WHITE = rgb(251, 241, 199)
GREEN = rgb(46, 204, 113)
YELLOW = rgb(241, 196, 15)
ORANGE = rgb(239, 161, 24)
RED = rgb(211, 66, 50)

GRAD = [
    rgb(46, 204, 113),
    rgb(86, 199, 96),
    rgb(116, 195, 89),
    rgb(186, 186, 64),
    rgb(241, 196, 15),
    rgb(239, 161, 24),
    rgb(236, 126, 34),
    rgb(233, 101, 44),
    rgb(211, 66, 50),
    rgb(192, 57, 43),
]

# ═══════════════════════════════════════════════════════════════
# RAINBOW ENGINE
# ═══════════════════════════════════════════════════════════════
phase = time.time() * 0.3  # color shift speed


def rbow_char(ch, idx=0, sat=0.85, val=1.0):
    hue = (idx * 0.08 + phase) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return f"\033[38;2;{int(r * 255)};{int(g * 255)};{int(b * 255)}m{ch}{R}"


def rbow_text(text, start=0, sat=0.8, val=1.0):
    out = ""
    ci = start
    for ch in text:
        if ch == " ":
            out += ch
            continue
        hue = (ci * 0.08 + phase) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
        out += f"\033[38;2;{int(r * 255)};{int(g * 255)};{int(b * 255)}m{ch}"
        ci += 1
    return out + R


# Rainbow separator — each │ gets a different hue
_sep_idx = [0]


def sep():
    _sep_idx[0] += 1
    return f" {rbow_char('│', _sep_idx[0])} "


# Legacy alias — older call sites use SEP().
SEP = sep


# ═══════════════════════════════════════════════════════════════
# FORMATTERS (fk + fcost + parse_model_id live in statusline_lib)
# ═══════════════════════════════════════════════════════════════
def fmoney(v, cur="$"):
    """Betrag mit Währungssymbol. ``fcost`` formatiert die Skala (k/M/B) und
    setzt ein ``$`` davor; hier wird nur das Symbol getauscht, damit die
    Skalen-Logik nicht zweimal existiert."""
    return fcost(v) if cur == "$" else cur + fcost(v)[1:]


def severity_cost(c, cur="$"):
    """Color cost by severity. Values are REAL from Claude Code."""
    if c < 0.01:
        return f"{DIM}<{cur}0.01{R}"
    s = fmoney(c, cur)
    if c < 5:
        return f"{GREEN}{s}{R}"
    if c < 20:
        return f"{YELLOW}{s}{R}"
    if c < 100:
        return f"{ORANGE}{s}{R}"
    return f"{RED}{s}{R}"


# `fmoney`/`severity_cost` stehen absichtlich VOR dem Ausgabe-Aufbau — sie
# werden dort benutzt. `math` ist entfallen, seit die Abo-Rechnung in
# usage_aggregate.py liegt.


def severity_tokens(n, label_color):
    s = fk(n)
    if n < 100_000:
        return f"{label_color}{s}{R}"
    if n < 500_000:
        return f"{YELLOW}{s}{R}"
    if n < 1_000_000:
        return f"{ORANGE}{s}{R}"
    return f"{RED}{s}{R}"


def fdur(ms):
    s = int(ms / 1000)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h}h{m:02d}m"
    d, h = divmod(h, 24)
    return f"{d}d{h}h"


def ftime(epoch):
    if not epoch:
        return ""
    try:
        diff = int(epoch - datetime.now(UTC).timestamp())
        if diff <= 0:
            return "now"
        h, rem = divmod(diff, 3600)
        m, _ = divmod(rem, 60)
        return f"{h}h{m:02d}m" if h > 0 else f"{m}m"
    except Exception:
        return ""


def used_color(pct):
    """Used % — green=low usage, red=high usage (like Claude dashboard)."""
    if pct is None:
        return f"{DIM}--{R}"
    p = round(pct)
    if p < 30:
        c = GREEN
    elif p < 60:
        c = YELLOW
    elif p < 85:
        c = ORANGE
    else:
        c = RED
    return f"{c}{p}%{R}"


def gbar(pct, w=12):
    filled = int(pct / 100 * w)
    b = ""
    for i in range(w):
        slot = min(9, int(i / w * 10))
        if i < filled:
            b += f"{GRAD[slot]}█"
        else:
            b += f"{R}{DIM}░"
    return b + R


# ═══════════════════════════════════════════════════════════════
# MODEL + PLAN
# ═══════════════════════════════════════════════════════════════
mshort, _family = parse_model_id(model_id)
_family_colors = {
    "opus": rgb(192, 132, 252),
    "sonnet": rgb(96, 165, 250),
    "haiku": rgb(134, 239, 172),
    "fable": rgb(45, 212, 191),
}
mcol = _family_colors.get(_family, WHITE)

# Plan label: prefer the real account tier (~/.claude.json oauthAccount.
# organizationRateLimitTier) over guessing from context_window_size — that
# heuristic has no documented link to subscription tier and can mislabel
# (found 2026-07-26, token-usage audit).
_account_plan = None
try:
    with Path("~/.claude.json").expanduser().open(encoding="utf-8") as f:
        _account_plan = parse_rate_limit_tier(
            (json.load(f).get("oauthAccount") or {}).get("organizationRateLimitTier")
        )
except Exception:
    pass
plan = _account_plan or ("Max" if total_ctx >= 1_000_000 else "Pro")
ctx_label = "1M" if total_ctx >= 1_000_000 else f"{total_ctx // 1000}k"
pct = round(used_pct)

# Effort level from settings.json
effort = "med"
try:
    settings_path = Path("~/.claude/settings.json").expanduser()
    with settings_path.open() as f:
        settings = json.load(f)
    e = settings.get("effortLevel", "medium").lower()
    effort_map = {"low": "L", "medium": "M", "high": "H", "min": "L", "max": "H"}
    effort = effort_map.get(e, e[0].upper())
except Exception:
    pass

EFFORT_COLORS = {"L": GREEN, "M": YELLOW, "H": RED}
effort_col = EFFORT_COLORS.get(effort, YELLOW)

# Die Abo-Vergleichsrechnung (Monate seit Account-Anlage × $200) liegt jetzt in
# usage_aggregate.py — dort, wo auch der Zeitraum und die Kosten herkommen.
# Sie hier zu wiederholen war der Anfang von zwei Quellen für eine Zahl.

# ═══════════════════════════════════════════════════════════════
# BUILD OUTPUT
# ═══════════════════════════════════════════════════════════════
parts = []

# ◆ Model(context/effort)
parts.append(
    f"{rbow_char('◆', 0)} {mcol}{BOLD}{mshort}{R}{DIM}({ctx_label}){R} {effort_col}{effort}{R}"
)

# ⎇ Git branch (C-BRANCH01 soft signal — main-first default, colored warning off-main)
_branch, _branch_sev = current_branch(cwd)
if _branch is not None:
    if _branch_sev == "main":
        parts.append(f"{DIM}⎇ {_branch}{R}")
    elif _branch_sev == "feature":
        parts.append(f"{YELLOW}⎇ {_branch}{R}")
    else:  # detached
        parts.append(f"{RED}⎇ {_branch}{R}")

# 🔧 Worktree task-id (TASK-2026-00629 worktree pattern via bin/agent-worktree.sh)
_wt = current_worktree_task(cwd)
if _wt and _wt.get("task_id"):
    parts.append(f"{CYAN}🔧 {_wt['task_id']}{R}")

# Progress bar + %
parts.append(f"{gbar(pct)} {GRAD[min(9, pct // 10)]}{pct}%{R}")

# Session-Kosten (Anthropics eigener Wert) — in der Währung des Annahmen-Registers
_sess_val, _cur = money(cost_usd, _agg)
parts.append(severity_cost(_sess_val, _cur))

# I:/O:/C: aus dem Session-Transkript, nicht aus dem Kontextfenster-Snapshot.
# Der Snapshot resettet bei /compact und lieferte deshalb Werte wie out:1k für
# eine 3-Stunden-Session. C: = Anteil der input-seitigen Token aus dem Cache —
# das Hook-JSON hat diese Felder gar nicht.
_su = read_session_usage(session_id)
if _su:
    # I: = GESAMTE Input-Seite (ungecacht + Cache-Read + Cache-Write). Nur
    # `input_tokens` zu zeigen wäre der alte Fehler in klein: bei 99 %
    # Cache-Quote stünde dort eine dreistellige Zahl, obwohl hunderte
    # Millionen Token in das Modell gegangen sind. C: sagt, wieviel davon
    # aus dem Cache kam.
    _in_side = _su["input"] + _su["cache_read"] + _su["cache_write"]
    _io = (
        f"{CYAN}I:{R}{severity_tokens(_in_side, CYAN)} "
        f"{MAGENTA}O:{R}{severity_tokens(_su['output'], MAGENTA)}"
    )
    _hit = _su.get("cache_hit_ratio")
    if _hit is not None:
        _io += f" {DIM}C:{R}{CYAN}{_hit * 100:.0f}%{R}"
    parts.append(_io)
else:
    # Kein Transkript gefunden → ehrlich unbekannt, keine erfundene 0.
    parts.append(f"{CYAN}I:{R}{DIM}—{R} {MAGENTA}O:{R}{DIM}—{R}")

# Duration (severity: >1h yellow, >4h orange)
dur_color = (
    DIM if duration_ms < 3600000 else (YELLOW if duration_ms < 14400000 else ORANGE)
)
parts.append(f"{dur_color}{fdur(duration_ms)}{R}")

# Σ seit Account-Anlage: Token → Tage → Ersparnis.
# Ein Geldwert, nicht zwei: vorher standen hier Σ-Gesamtkosten UND
# "Max(+$X saved)" — dieselbe Zahl minus dem Abo-Preis, zweimal angezeigt.
# Die Session-Anzahl entfällt: "275d(3)" behauptete 275 Tage aus 3 Sessions.
if sigma_tokens:
    _saved_val, _saved_cur = money(sigma_saved_usd, _agg)
    _span = f"{int(span_days)}d" if span_days < 365 else f"{span_days / 365:.1f}y"
    parts.append(
        f"{rbow_text('Σ', 3)}{severity_tokens(sigma_tokens, WHITE)} "
        f"{rbow_text('Σ', 5)}{DIM}{_span}{R} "
        f"{rbow_text('Σ', 7)}{GREEN}{fmoney(_saved_val, _saved_cur)}{R}"
    )

# Rate limits (used %, like Claude dashboard)
rl_parts = []
if r5h_pct is not None:
    t = ftime(r5h_resets)
    rl_parts.append(f"{DIM}5h:{R}{used_color(r5h_pct)}{f'({t})' if t else ''}")
if r7d_pct is not None:
    t = ftime(r7d_resets)
    rl_parts.append(f"{DIM}7d:{R}{used_color(r7d_pct)}{f'({t})' if t else ''}")
if rl_parts:
    parts.append(" ".join(rl_parts))

# Abo-Tier, nackt. Die Ersparnis steht im Σ-Block — hier stand sie doppelt.
parts.append(f"{mcol}{plan}{R}")

# Join with rainbow separators
try:
    print(SEP().join(parts))
except Exception:
    print("\033[2m◆ meta-skills OK\033[0m")
