#!/usr/bin/env python3
"""Hook: Scope Tracker (UserPromptSubmit)

Tracks topic drift across a session. When user switches to unrelated
topics after 3+ distinct tasks, injects advisory context suggesting
a new session.

Addresses: Multi-Task Drift (19/31 sessions were multi-task with worst outcomes).

Exit 0 + additionalContext. Never blocks.
"""
import json
import os
import re
import sys
from pathlib import Path

HOOK_NAME = "scope_tracker"
STATE_DIR = Path(os.environ.get(
    "CLAUDE_PLUGIN_DATA",
    Path.home() / ".claude" / "plugins" / "data" / "meta-skills"
))

# --- Domain keyword sets for topic detection ---
DOMAIN_KEYWORDS = {
    "infra": {"ssh", "docker", "swarm", "proxmox", "pve", "vm", "container",
              "deploy", "server", "node", "cluster", "port", "service",
              "network", "raft", "haproxy", "nginx", "systemd"},
    "code": {"refactor", "function", "class", "module", "import", "test",
             "lint", "ruff", "eslint", "typescript", "python", "rust",
             "compile", "build", "npm", "pip", "cargo"},
    "docs": {"claude.md", "documentation", "readme", "wiki", "doku",
             "dokumentation", "skill.md", "rules", "guide"},
    "product": {"shop", "landing", "gumroad", "stripe", "product", "price",
                "customer", "marketing", "seo", "content", "social"},
    "agent": {"echo_log", "mattermost", "agent", "bot", "bridge",
              "delegation", "workflow", "n8n", "automation"},
    "plugin": {"plugin", "hook", "skill", "meta-skills", "meta-skill",
               "command", "slash", "frontmatter"},
    "research": {"benchmark", "research", "compare", "analyse", "analyze",
                 "evaluate", "whitepaper", "paper", "study"},
    "design": {"design", "ui", "ux", "layout", "theme", "css", "html",
               "electron", "dashboard", "frontend"},
}

# --- Topic transition signals ---
TRANSITION_SIGNALS = re.compile(
    r"\b(jetzt|nun|als\s+naechstes|next|switch\s+to|wechsel|"
    r"anderes\s+thema|other\s+topic|btw|uebrigens|by\s+the\s+way)\b",
    re.IGNORECASE
)


def extract_domains(text: str) -> set:
    """Extract domain matches from text."""
    text_lower = text.lower()
    matched = set()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                matched.add(domain)
                break
    return matched


def load_state(session_id: str) -> dict:
    """Load scope tracking state."""
    state_file = STATE_DIR / f".scope-tracker-{session_id}.json"
    try:
        if state_file.exists():
            return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "session_id": session_id,
        "initial_domains": [],
        "seen_domains": [],
        "prompt_count": 0,
        "task_switches": 0,
        "warned": False,
    }


def save_state(session_id: str, state: dict) -> None:
    """Persist state."""
    state_file = STATE_DIR / f".scope-tracker-{session_id}.json"
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    prompt = data.get("prompt", "")
    session_id = data.get("session_id", "unknown")

    if not prompt or len(prompt) < 10:
        sys.exit(0)

    state = load_state(session_id)
    state["prompt_count"] += 1
    current_domains = extract_domains(prompt)

    # --- First prompt: establish baseline ---
    if state["prompt_count"] == 1:
        state["initial_domains"] = list(current_domains)
        state["seen_domains"] = list(current_domains)
        save_state(session_id, state)
        sys.exit(0)

    # --- Detect new domains ---
    seen = set(state["seen_domains"])
    initial = set(state["initial_domains"])
    new_domains = current_domains - seen

    if new_domains:
        state["seen_domains"] = list(seen | new_domains)

        # Check if it's genuinely a different topic (not just expanding scope)
        has_transition = bool(TRANSITION_SIGNALS.search(prompt))
        is_new_topic = not new_domains.intersection(initial) and len(new_domains) > 0

        if is_new_topic or has_transition:
            state["task_switches"] += 1

    save_state(session_id, state)

    # --- Advisory after 3+ topic switches ---
    if state["task_switches"] >= 3 and not state["warned"]:
        state["warned"] = True
        save_state(session_id, state)

        context = (
            f"SCOPE DRIFT DETECTED ({state['task_switches']} topic switches this session). "
            "Usage report: multi-task sessions have the worst outcomes "
            "(19/31 sessions, most friction). "
            "Single-task sessions = best results. "
            "Suggestion: finish current task first, then start new session."
        )
        print(json.dumps({"additionalContext": context}))

    sys.exit(0)


if __name__ == "__main__":
    main()
