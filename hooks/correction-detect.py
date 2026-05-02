#!/usr/bin/env python3
"""Hook: Escalation Tracker v2 (UserPromptSubmit)

Detects correction patterns in Joe's messages and injects context
to help Claude handle corrections properly.

Detection patterns:
- Explicit corrections: "nein", "falsch", "nicht so", "stopp", "stop"
- Redirection: "ich meinte", "ich will", "das stimmt nicht"
- Frustration: "schon wieder", "immer noch", "wie oft noch"

When detected: injects reminder to STOP, acknowledge correction,
re-read relevant rules, and present new plan.

Also tracks consecutive corrections per session for S10 compliance
(2 corrections = pause and review).

Exit 0 + additionalContext. Never blocks.

v2 (2026-04-09): Replaces stub with real correction detection.
"""

import json
import re
import sys
from pathlib import Path

# --- Add hooks dir to path for lib import ---
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.state import SessionState

HOOK_NAME = "escalation_tracker"

# --- Correction patterns (German + English) ---
# Each tuple: (compiled_regex, severity: "correction" | "frustration" | "stop")
PATTERNS = [
    # Hard stop signals
    (re.compile(r"\b(stopp?|halt|abbruch)\b", re.IGNORECASE), "stop"),
    # Explicit corrections — German
    (
        re.compile(r"\b(nein|falsch|nicht\s+so|das\s+stimmt\s+nicht)\b", re.IGNORECASE),
        "correction",
    ),
    (
        re.compile(
            r"\b(ich\s+meinte?|ich\s+will|ich\s+wollte|das\s+war\s+nicht)\b",
            re.IGNORECASE,
        ),
        "correction",
    ),
    (
        re.compile(r"\b(andersrum|umgekehrt|genau\s+das\s+gegenteil)\b", re.IGNORECASE),
        "correction",
    ),
    (
        re.compile(r"\b(nicht\s+das|das\s+andere|der\s+andere)\b", re.IGNORECASE),
        "correction",
    ),
    # Explicit corrections — English
    (
        re.compile(
            r"\b(wrong|no,?\s+that'?s\s+not|not\s+what\s+I\s+asked)\b", re.IGNORECASE
        ),
        "correction",
    ),
    (
        re.compile(r"\b(I\s+said|I\s+meant|different\s+approach)\b", re.IGNORECASE),
        "correction",
    ),
    (
        re.compile(
            r"\b(you'?re\s+doing\s+it\s+wrong|that'?s\s+incorrect|incorrect)\b",
            re.IGNORECASE,
        ),
        "correction",
    ),
    # Scope corrections — German + English
    (
        re.compile(
            r"\b(bleib\s+beim\s+thema|nicht\s+abschweifen|fokus)\b", re.IGNORECASE
        ),
        "correction",
    ),
    (
        re.compile(
            r"\b(focus\s+on|only\s+do|one\s+thing\s+at\s+a\s+time)\b", re.IGNORECASE
        ),
        "correction",
    ),
    # Frustration / repeated errors — German
    (
        re.compile(
            r"\b(schon\s+wieder|immer\s+noch|wie\s+oft\s+noch|zum\s+x-?ten\s+mal)\b",
            re.IGNORECASE,
        ),
        "frustration",
    ),
    (
        re.compile(
            r"\b(hab\s+ich\s+(schon|bereits)\s+gesagt|hab\s+ich\s+dir\s+gesagt)\b",
            re.IGNORECASE,
        ),
        "frustration",
    ),
    # Frustration / repeated errors — English
    (
        re.compile(
            r"\b(again|already\s+told\s+you|how\s+many\s+times)\b", re.IGNORECASE
        ),
        "frustration",
    ),
    (
        re.compile(
            r"\b(still\s+not\s+working|same\s+problem|keeps\s+happening)\b",
            re.IGNORECASE,
        ),
        "frustration",
    ),
]

# Messages that are NOT corrections even if they contain trigger words
FALSE_POSITIVE_PATTERNS = [
    re.compile(
        r"(?:ja\s+)?nein[\s,]+(danke|thanks|thx|passt|gut)", re.IGNORECASE
    ),  # "nein danke/thanks" = polite decline (incl. DE+EN mix)
    re.compile(
        r"(?:oder|entweder).*\bnein\b", re.IGNORECASE
    ),  # "ja oder nein" = question
    re.compile(
        r"\bnicht\s+so\s+(?:schlimm|wichtig|dringend)\b", re.IGNORECASE
    ),  # "nicht so schlimm"
    re.compile(r".*\?\s*$"),  # Questions ending with ? are usually not corrections
    re.compile(
        r"\b(is\s+(?:this|that)\s+wrong|was\s+ist\s+falsch)\b", re.IGNORECASE
    ),  # Asking about wrongness
    re.compile(
        r"\b(what'?s\s+wrong|was\s+stimmt\s+nicht\s+mit)\b", re.IGNORECASE
    ),  # Diagnostic questions
]


def load_state(session_id: str) -> dict:
    """Load escalation state via centralized SessionState."""
    session_state = SessionState(session_id)
    return session_state.get("correction_detect"), session_state


def save_state(session_state, state: dict) -> None:
    """Persist escalation state via centralized SessionState."""
    session_state.set("correction_detect", state)
    session_state.save()


def detect_correction(prompt: str) -> tuple:
    """Detect correction patterns in user prompt.

    Returns (severity, matched_pattern) or (None, None).
    """
    if not prompt or len(prompt) < 3:
        return None, None

    # Check false positives first
    for fp in FALSE_POSITIVE_PATTERNS:
        if fp.search(prompt):
            return None, None

    # Check correction patterns
    for regex, severity in PATTERNS:
        match = regex.search(prompt)
        if match:
            return severity, match.group(0)

    return None, None


def main():
    # --- Read stdin ---
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    prompt = data.get("prompt", "")
    session_id = data.get("session_id", "unknown")

    if not prompt:
        sys.exit(0)

    # --- Detect correction ---
    severity, matched = detect_correction(prompt)

    if severity is None:
        sys.exit(0)

    # --- Update state ---
    state, session_state = load_state(session_id)
    state["correction_count"] += 1
    state["last_severity"] = severity
    save_state(session_state, state)

    count = state["correction_count"]

    # --- Build response based on severity ---
    if severity == "stop":
        context = (
            f"JOE SAID STOP ('{matched}'). "
            "IMMEDIATELY stop all actions. "
            "Repeat correction in one sentence: 'You mean: [X]'. "
            "Derive new plan from corrected facts. "
            "Show plan to Joe. Only continue after 'yes'."
        )
    elif severity == "frustration":
        context = (
            f"FRUSTRATION DETECTED ('{matched}', correction #{count} this session). "
            "PAUSE. List errors: what went wrong, which rule was relevant. "
            "Name corrected assumption: 'I assumed [X], correct is [Y]'. "
            "Formulate new plan and show Joe."
        )
    else:  # correction
        context = (
            f"CORRECTION DETECTED ('{matched}'). "
            "Stop current action. "
            "Repeat correction: 'You mean: [X]'. "
            "Derive new plan. Show Joe."
        )

    # S10 compliance: 2 corrections = mandatory pause
    if count >= 2:
        context += (
            f" WARNING: {count} corrections this session (S10). "
            "Usage report: 55 friction events in 31 sessions. "
            "Corrections correlate with Wrong-Approach (43x) and Buggy-Code (37x). "
            "PAUSE. Identify root cause instead of rushing ahead. "
            "List all errors. Only continue after Joe's approval."
        )

    print(json.dumps({"additionalContext": context}))
    sys.exit(0)


if __name__ == "__main__":
    main()
