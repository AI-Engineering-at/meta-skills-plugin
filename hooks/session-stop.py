#!/usr/bin/env python3
"""Hook: Stop Validator v2 (Stop event)

Leitpfad-Approach: hilft bei Dokumentation statt nur zu erinnern.

1. Generates session summary from git changes (today's commits + uncommitted).
2. Writes meaningful summary to Honcho (not just "session ended").
3. Offers to create open-notebook source if changes are knowledge-relevant.
4. Reminds about ERPNext task update.

Exit 0 + additionalContext = context shown to Claude.
Never hard-blocks — Joe can always end a session.

v2 changes (2026-04-09):
- Direct HTTP via lib/services.py
- Auto-generates session summary from git diff
- Writes rich summary to Honcho (not just one-liner)
- Suggests open-notebook source creation for knowledge-relevant changes
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- Add hooks dir to path for lib import ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.services import (
    HonchoClient,
    OpenNotebookClient,
    detect_peer_id,
    detect_project_name,
    get_git_changes_summary,
    log_error,
)

HOOK_NAME = "stop_validator"
STATE_DIR = Path(os.environ.get(
    "CLAUDE_PLUGIN_DATA",
    Path.home() / ".claude" / "plugins" / "data" / "meta-skills"
))

# Keywords that suggest knowledge-relevant changes
KNOWLEDGE_KEYWORDS = [
    "CLAUDE.md", "rules/", "knowledge/", "LEARNINGS", "ERRORS",
    "STATUS.md", "docs/", "README", "ARCHITECTURE", "AUDIT",
    "services", "deploy", "migration", "config", "infrastructure",
]


def is_knowledge_relevant(summary: str) -> bool:
    """Check if git changes contain knowledge-relevant files."""
    summary_lower = summary.lower()
    return any(kw.lower() in summary_lower for kw in KNOWLEDGE_KEYWORDS)


def main():
    # --- Read stdin ---
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    session_id = data.get("session_id", "unknown")
    cwd = os.getcwd()
    peer_id = detect_peer_id(cwd)
    project = detect_project_name(cwd)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # --- Generate session summary from git ---
    git_summary = get_git_changes_summary(max_lines=15)

    # --- Build rich Honcho message ---
    honcho_content_parts = [
        f"Session {session_id[:12]}... ended.",
        f"Project: {project} | CWD: {cwd}",
        f"Time: {now}",
    ]
    if git_summary:
        honcho_content_parts.append(f"Git changes:\n{git_summary}")

    honcho_message = "\n".join(honcho_content_parts)

    # --- Write to Honcho ---
    honcho_written = False
    try:
        honcho = HonchoClient(timeout=10.0)
        if honcho.is_healthy():
            # Ensure session exists
            honcho.create_session(
                session_id=session_id,
                peer_id=peer_id,
                metadata={"event": "stop", "project": project},
            )
            honcho_written = honcho.add_message(
                session_id=session_id,
                peer_id=peer_id,
                content=honcho_message,
            )
    except Exception as e:
        log_error(HOOK_NAME, f"Honcho write failed: {e}", f"session={session_id}")

    # --- Auto-regenerate network diagram if infra changed ---
    infra_changed = git_summary and any(
        kw in git_summary.lower()
        for kw in ["03-infrastructure", "03b-services", "vault", "swarm", "node"]
    )
    if infra_changed:
        try:
            import subprocess as _sp
            diagram_script = Path(os.getcwd()) / "tools" / "generate-network-diagram.py"
            if diagram_script.exists():
                _sp.run(
                    [sys.executable, str(diagram_script)],
                    capture_output=True, timeout=15, cwd=os.getcwd(),
                )
        except Exception:
            pass  # Diagram generation is optional

    # --- Check if open-notebook source should be suggested ---
    suggest_notebook = False
    if git_summary and is_knowledge_relevant(git_summary):
        suggest_notebook = True

    # --- Verification checks (addresses Buggy Code + Premature Success) ---
    verification_warnings = []

    # Check for uncommitted changes
    try:
        import subprocess as _sp_verify
        diff_result = _sp_verify.run(
            ["git", "diff", "--stat"], capture_output=True, text=True,
            timeout=5, cwd=cwd,
        )
        staged_result = _sp_verify.run(
            ["git", "diff", "--cached", "--stat"], capture_output=True, text=True,
            timeout=5, cwd=cwd,
        )
        has_uncommitted = bool(diff_result.stdout.strip())
        has_staged = bool(staged_result.stdout.strip())
        if has_uncommitted or has_staged:
            verification_warnings.append(
                "UNCOMMITTED CHANGES detected! Commit before ending session?"
            )
    except Exception:
        pass

    # Check if lint was run for changed file types
    try:
        if git_summary:
            py_changed = any(f.endswith(".py") for f in git_summary.split("\n"))
            ts_changed = any(f.endswith((".ts", ".tsx", ".js")) for f in git_summary.split("\n"))

            # Read audit log to check if lint commands were run
            audit_log = STATE_DIR / "token-audit.jsonl"
            lint_ran = False
            if audit_log.exists():
                try:
                    # Read last 50 lines efficiently
                    lines = audit_log.read_text(encoding="utf-8").strip().split("\n")[-50:]
                    for line in lines:
                        entry = json.loads(line)
                        cmd = entry.get("command", "")
                        if "ruff" in cmd or "eslint" in cmd or "npm run lint" in cmd:
                            lint_ran = True
                            break
                except Exception:
                    pass

            if (py_changed or ts_changed) and not lint_ran:
                if py_changed:
                    verification_warnings.append(
                        "Python files changed but no `ruff check` this session. "
                        "Rule 05: lint REQUIRED before commit."
                    )
                if ts_changed:
                    verification_warnings.append(
                        "TypeScript/JS files changed but no lint this session. "
                        "Rule 05: `npm run lint` REQUIRED before commit."
                    )
    except Exception:
        pass

    # --- Build additionalContext for Claude ---
    ctx_parts = ["Session endet. Dokumentation:"]

    # Add verification warnings first (most important)
    if verification_warnings:
        ctx_parts.append("VERIFICATION: " + " | ".join(verification_warnings))

    if honcho_written:
        ctx_parts.append(
            f"Honcho: session summary written ({peer_id}). "
            "Next session has this context automatically."
        )
    else:
        ctx_parts.append("Honcho: OFFLINE — Summary nicht geschrieben.")

    ctx_parts.append(
        "Check: (1) Git — all changes committed? "
        "(2) ERPNext — task updated?"
    )

    if suggest_notebook:
        ctx_parts.append(
            "RECOMMENDATION: Changes affect knowledge-relevant files. "
            "Erstelle eine open-notebook Source mit: "
            "curl -s -X POST 'http://10.40.10.82:5055/api/sources/json' "
            "-H 'Content-Type: application/json' "
            "-d '{\"type\":\"text\",\"title\":\"Session YYYY-MM-DD — Thema\","
            "\"content\":\"...\",\"notebooks\":[\"notebook:zkxy9fiwelrolgbr2upc\"],"
            "\"embed\":true}'"
        )

    if git_summary:
        # Show Claude what happened so it can help document
        ctx_parts.append(f"Git-Zusammenfassung dieser Session:\n{git_summary[:400]}")

    # --- P7: Write session state for context recovery ---
    try:
        state_file = STATE_DIR / f".session-state-{session_id}.json"
        prompt_counter_file = STATE_DIR / f".prompt-counter-{session_id}"
        prompt_count = 0
        if prompt_counter_file.exists():
            try:
                prompt_count = int(prompt_counter_file.read_text(encoding="utf-8").strip())
            except (ValueError, OSError):
                pass

        state_data = {
            "session_id": session_id,
            "project": project,
            "cwd": cwd,
            "timestamp": now,
            "prompt_count": prompt_count,
            "git_summary": git_summary[:500] if git_summary else "",
            "uncommitted": bool(verification_warnings),
            "lint_status": "unknown",
            "open_items": ", ".join(verification_warnings) if verification_warnings else "none",
        }
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_file.write_text(
            json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8",
        )

        # Cleanup old state files (keep last 5)
        state_files = sorted(STATE_DIR.glob(".session-state-*.json"), key=lambda f: f.stat().st_mtime)
        for f in state_files[:-5]:
            f.unlink(missing_ok=True)
    except Exception:
        pass

    # --- Output ---
    print(json.dumps({
        "additionalContext": " ".join(ctx_parts),
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
