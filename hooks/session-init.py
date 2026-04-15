#!/usr/bin/env python3
"""Hook: Session Init v3 (UserPromptSubmit — First-Prompt-Detection)

Runs on UserPromptSubmit. Uses a state file to detect the first prompt
of a session. On first prompt: full init (Honcho, open-notebook, watcher).
On subsequent prompts: exits immediately (< 1ms).

1. Creates/resumes Honcho session with peer detection.
2. Loads Honcho peer context (derived summary from all past sessions).
3. Searches open-notebook for project-relevant knowledge.
4. Injects structured context as systemMessage.
5. Spawns session watcher if available.

Exit 0 + JSON systemMessage. Never blocks, never crashes.

v3 changes (2026-04-10):
- Migrated from SessionStart (invalid event) to UserPromptSubmit
- First-prompt detection via state file (PID-based)
- Exits immediately on subsequent prompts
"""
import json
import os
import sys
from pathlib import Path

# --- Add hooks dir to path for lib import ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HOOK_NAME = "session_init"

# --- Add hooks dir to path for lib import ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.state import SessionState

# Read stdin early to get session_id
try:
    _raw_stdin = sys.stdin.read()
    _stdin_data = json.loads(_raw_stdin) if _raw_stdin.strip() else {}
except Exception:
    _stdin_data = {}
    _raw_stdin = ""

session_id = _stdin_data.get("session_id", "unknown")

# --- Centralized state for first-prompt detection + prompt counter ---
_session_state = SessionState(session_id)
current_count = _session_state.prompt_count + 1
_session_state.prompt_count = current_count

# --- P7: Context recovery detection (after compaction, prompt gap > 10) ---
recovery_context = ""
if _session_state.is_initialized and current_count > 0:
    # Session already initialized — check for context loss
    try:
        meta = _session_state.get("session_meta")
        saved_count = meta.get("prompt_count_at_save", 0) if isinstance(meta, dict) else 0
        gap = current_count - saved_count
        if gap > 10 and saved_count > 0:
            recovery_context = (
                f"CONTEXT RECOVERY: {gap} prompts since last state save. "
                f"Project: {meta.get('project', '?')}. "
                f"Last changes: {meta.get('git_summary', 'unknown')[:200]}. "
                f"Open items: {meta.get('open_items', 'none')}."
            )
    except Exception:
        pass

    _session_state.save()

    if not recovery_context:
        # Normal subsequent prompt �� exit fast
        sys.exit(0)
    else:
        # Context lost — inject recovery and continue to CI check
        pass

# Mark as initialized BEFORE doing work (prevents re-entry on first prompt)
_session_state.is_initialized = True
_session_state.save()

# Clean up old state files (keep last 5)
SessionState.cleanup_stale(keep=5)
SessionState.cleanup_legacy()

# --- Now import heavy deps only on first prompt ---
from lib.services import (
    HonchoClient,
    OpenNotebookClient,
    detect_peer_id,
    detect_project_name,
    log_error,
)


def main():
    # stdin already read at top level for first-prompt detection
    data = _stdin_data

    cwd = os.getcwd()
    peer_id = detect_peer_id(cwd)
    project = detect_project_name(cwd)

    # --- Base message (compact — rules are in CLAUDE.md, not here) ---
    parts = []

    # --- Honcho: create session + load context ---
    honcho_ok = False
    try:
        honcho = HonchoClient(timeout=10.0)
        if honcho.is_healthy():
            honcho_ok = True
            # Create/resume session
            honcho.create_session(
                session_id=session_id,
                peer_id=peer_id,
                metadata={"source": "first-prompt", "cwd": cwd, "project": project},
            )

            # Get derived peer context (Honcho's AI-generated summary)
            context = honcho.get_peer_context(peer_id)
            if context and len(context) > 20:
                parts.append(f"HONCHO KONTEXT ({peer_id}): {context[:800]}")

            # Search for recent relevant findings (filter out raw commands)
            search_results = honcho.search_peer(
                peer_id=peer_id,
                query=f"session summary {project}",
                limit=5,
            )
            if search_results:
                # Filter: skip raw bash commands, keep human-readable summaries
                relevant = [
                    r for r in search_results
                    if len(r) > 30
                    and not r.strip().startswith(("cd ", "python ", "curl ", "docker ", "git ", "ls ", "cat ", "grep ", "find ", "ssh ", "scp "))
                    and "&&" not in r[:50]
                ]
                if relevant:
                    combined = " | ".join(relevant[:2])
                    parts.append(f"SESSIONS: {combined[:300]}")
    except Exception as e:
        log_error(HOOK_NAME, f"Honcho failed: {e}", f"peer={peer_id}")

    # --- open-notebook: search for project knowledge ---
    try:
        notebook = OpenNotebookClient(timeout=10.0)
        if notebook.is_healthy():
            results = notebook.search_text(
                query=f"{project} aktueller stand",
                limit=3,
            )
            if results:
                titles = [r.get("title", "?") for r in results if r.get("title")]
                if titles:
                    parts.append(
                        f"OPEN-NOTEBOOK ({len(titles)} relevant): "
                        + " | ".join(titles[:3])
                    )
    except Exception as e:
        log_error(HOOK_NAME, f"open-notebook failed: {e}", f"project={project}")

    # --- Service status line ---
    status_parts = []
    if honcho_ok:
        status_parts.append("Honcho OK")
    else:
        status_parts.append("Honcho OFFLINE")
    status_parts.append(f"Peer: {peer_id}")
    status_parts.append(f"Project: {project}")
    parts.append(f"[{' | '.join(status_parts)}]")

    # --- Shared paths (used by setup check + watcher) ---
    import subprocess
    import platform
    plugin_root = Path(os.path.dirname(os.path.abspath(__file__))).parent

    # --- First-run setup check ---
    try:
        from lib.state import STATE_DIR as plugin_data
        setup_marker = plugin_data / ".setup-done-v2"
        setup_script = plugin_root / "scripts" / "plugin-setup.py"

        if not setup_marker.exists() and setup_script.exists():
            r = subprocess.run(
                [sys.executable, str(setup_script), "--auto"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip():
                try:
                    setup_result = json.loads(r.stdout.strip())
                    parts.append(setup_result.get("summary", "Meta-Skills Setup: done"))
                except (json.JSONDecodeError, ValueError):
                    parts.append("Meta-Skills: First-run setup completed")
    except Exception:
        pass

    # --- Load plugin config for feature toggles ---
    try:
        from lib.config import load_config as _load_config
        plugin_config = _load_config()
    except Exception:
        plugin_config = {}

    watcher_enabled = plugin_config.get("features", {}).get("watcher", True)

    # --- CI/CD Status Check (only on first prompt, only if in git repo) ---
    try:
        is_windows = platform.system() == "Windows"
        # Check if we're in a git repo first
        git_check = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=3,
            shell=is_windows, cwd=cwd,
        )
        if git_check.returncode == 0:
            ci_result = subprocess.run(
                ["gh", "run", "list", "--limit", "1",
                 "--json", "conclusion,name,url,headBranch"],
                capture_output=True, text=True, timeout=5,
                shell=is_windows, cwd=cwd,
            )
            if ci_result.returncode == 0 and ci_result.stdout.strip():
                ci_runs = json.loads(ci_result.stdout)
                if ci_runs and ci_runs[0].get("conclusion") == "failure":
                    ci_name = ci_runs[0].get("name", "?")
                    ci_branch = ci_runs[0].get("headBranch", "?")
                    ci_url = ci_runs[0].get("url", "")
                    parts.append(
                        f"CI FAILURE: Last run '{ci_name}' on {ci_branch} FAILED. "
                        f"Fix before pushing. Check: /meta-ci --last-failure"
                    )
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    except Exception:
        pass

    # --- Spawn session watcher (detached, if enabled) ---
    try:
        watcher = plugin_root / "scripts" / "session-watcher.py"
        if watcher.exists() and watcher_enabled:
            parent_pid = os.getppid()
            if platform.system() == "Windows":
                flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
                subprocess.Popen(
                    [sys.executable, str(watcher), "--parent-pid", str(parent_pid)],
                    creationflags=flags,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    [sys.executable, str(watcher), "--parent-pid", str(parent_pid)],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
    except Exception:
        pass  # Watcher is optional

    # --- Output: additionalContext for important warnings ---
    # CI failures, context recovery, critical issues
    actionable = [p for p in parts if "CI FAILURE" in p or "CRITICAL" in p]

    # P7: Add recovery context if detected
    if recovery_context:
        actionable.insert(0, recovery_context)

    if actionable:
        print(json.dumps({"additionalContext": " | ".join(actionable)}))
    sys.exit(0)


if __name__ == "__main__":
    main()
