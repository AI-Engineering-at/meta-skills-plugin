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
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Pure formatters + model parser live in a sibling module for testability.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from statusline_lib import fcost, fk, parse_model_id  # noqa: E402

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

_raw_model = model_data.get("id") or (data.get("model") if isinstance(data.get("model"), str) else None) or "unknown"
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
STATS_FILE = os.path.expanduser("~/.claude/statusline-alltime.json")

try:
    with open(STATS_FILE, encoding="utf-8") as f:
        all_stats = json.load(f)
except Exception:
    all_stats = {}

# Prune entries older than 90 days to prevent unbounded growth.
# Exception: baseline-* keys (historical backfill) are preserved.
cutoff = time.time() - (90 * 86400)
all_stats = {
    k: v for k, v in all_stats.items()
    if k.startswith("baseline-") or v.get("ts", 0) > cutoff
}

all_stats[session_id] = {
    "cost": cost_usd,
    "tokens": session_tok,
    "time_ms": duration_ms,
    "model": model_id,
    "ts": time.time(),
}

try:
    tmp = STATS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(all_stats, f, separators=(",", ":"))
    os.replace(tmp, STATS_FILE)
except Exception:
    pass

sigma_cost = sum(s.get("cost", 0) for s in all_stats.values())
sigma_tokens = sum(s.get("tokens", 0) for s in all_stats.values())
# Baseline-backfill entries optionally declare a `sessions` count for the period
# they represent (pre-plugin history). Otherwise each entry counts as 1 session.
_baseline = all_stats.get("baseline-backfill", {})
sigma_sessions = len(all_stats) - (1 if _baseline else 0) + _baseline.get("sessions", 0 if _baseline else 0)

# Time span since first session. Show days up to 365, then years.
timestamps = [s.get("ts", time.time()) for s in all_stats.values()]
first_ts = min(timestamps) if timestamps else time.time()
span_days = (time.time() - first_ts) / 86400
if span_days < 1:
    sigma_span = "today"
elif span_days < 365:
    sigma_span = f"{int(span_days)}d"
else:
    sigma_span = f"{span_days / 365:.1f}y"

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
    rgb(46, 204, 113), rgb(86, 199, 96), rgb(116, 195, 89),
    rgb(186, 186, 64), rgb(241, 196, 15), rgb(239, 161, 24),
    rgb(236, 126, 34), rgb(233, 101, 44), rgb(211, 66, 50),
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


def SEP():
    _sep_idx[0] += 1
    return f" {rbow_char('│', _sep_idx[0])} "


# ═══════════════════════════════════════════════════════════════
# FORMATTERS (fk + fcost + parse_model_id live in statusline_lib)
# ═══════════════════════════════════════════════════════════════
def severity_cost(c):
    """Color cost by severity. Values are REAL from Claude Code."""
    if c < 0.01:
        return f"{DIM}<$0.01{R}"
    s = fcost(c)
    if c < 5:
        return f"{GREEN}{s}{R}"
    if c < 20:
        return f"{YELLOW}{s}{R}"
    if c < 100:
        return f"{ORANGE}{s}{R}"
    return f"{RED}{s}{R}"


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
}
mcol = _family_colors.get(_family, WHITE)

plan = "Max" if total_ctx >= 1_000_000 else "Pro"
ctx_label = "1M" if total_ctx >= 1_000_000 else f"{total_ctx // 1000}k"
pct = round(used_pct)

# Effort level from settings.json
effort = "med"
try:
    settings_path = os.path.expanduser("~/.claude/settings.json")
    with open(settings_path) as f:
        settings = json.load(f)
    e = settings.get("effortLevel", "medium").lower()
    effort_map = {"low": "L", "medium": "M", "high": "H", "min": "L", "max": "H"}
    effort = effort_map.get(e, e[0].upper())
except Exception:
    pass

EFFORT_COLORS = {"L": GREEN, "M": YELLOW, "H": RED}
effort_col = EFFORT_COLORS.get(effort, YELLOW)

# Subscription comparison (Max = $200/month)
MONTHLY_SUB = 200.0

# ═══════════════════════════════════════════════════════════════
# BUILD OUTPUT
# ═══════════════════════════════════════════════════════════════
parts = []

# ◆ Model(context/effort)
parts.append(f"{rbow_char('◆', 0)} {mcol}{BOLD}{mshort}{R}{DIM}({ctx_label}){R} {effort_col}{effort}{R}")

# Progress bar + %
parts.append(f"{gbar(pct)} {GRAD[min(9, pct // 10)]}{pct}%{R}")

# Session cost (REAL from Claude Code)
parts.append(severity_cost(cost_usd))

# In/Out (cyan=input, magenta=output, severity-scaled)
parts.append(
    f"{CYAN}in:{R}{severity_tokens(total_in, CYAN)} "
    f"{MAGENTA}out:{R}{severity_tokens(total_out, MAGENTA)}"
)

# Duration (severity: >1h yellow, >4h orange)
dur_color = DIM if duration_ms < 3600000 else (YELLOW if duration_ms < 14400000 else ORANGE)
parts.append(f"{dur_color}{fdur(duration_ms)}{R}")

# Σ All-Time: cost + tokens + span(sessions)
parts.append(
    f"{rbow_text('Σ', 3)}{severity_cost(sigma_cost)} "
    f"{rbow_text('Σ', 5)}{severity_tokens(sigma_tokens, WHITE)} "
    f"{rbow_text('Σ', 7)}{DIM}{sigma_span}({sigma_sessions}){R}"
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

# Plan + savings
if sigma_cost > MONTHLY_SUB:
    savings = sigma_cost - MONTHLY_SUB
    parts.append(f"{mcol}{plan}{R}{DIM}({R}{GREEN}+{fcost(savings)}{R}{DIM}saved){R}")
else:
    parts.append(f"{mcol}{plan}{R}")

# Join with rainbow separators
try:
    print(SEP().join(parts))
except Exception:
    print("\033[2m◆ meta-skills OK\033[0m")
