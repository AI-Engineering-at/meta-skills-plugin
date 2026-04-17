"""Pure formatters and parsers extracted from statusline.py.

Extracted for unit testability. statusline.py imports from here.
No I/O, no side-effects, no ANSI codes — pure string transforms only.
"""
import re

MODEL_RE = re.compile(r"(opus|sonnet|haiku)-(\d+)-(\d+)")


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

    Returns tuple of (label, family) where family in {'opus','sonnet','haiku',None}.

    Examples:
        'claude-opus-4-7'             -> ('O4.7', 'opus')
        'claude-sonnet-4-6'           -> ('S4.6', 'sonnet')
        'claude-haiku-4-5-20251001'   -> ('H4.5', 'haiku')
        'claude-opus-5-0'             -> ('O5.0', 'opus')
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
        return (f"{family[0].upper()}{maj}.{minor}", family)
    for fam in ("opus", "sonnet", "haiku"):
        if fam in lower:
            return (fam.capitalize()[:4], fam)
    return (lower[:6], None)
