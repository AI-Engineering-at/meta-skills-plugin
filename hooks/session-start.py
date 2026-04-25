#!/usr/bin/env python3
"""Hook: Session Start (SessionStart event)

Runs once when a session begins. Handles all first-prompt initialization
that was previously hacked into session-init.py via state file detection.

1. Creates/resumes Honcho session with peer detection.
2. Loads Honcho peer context (derived summary from past sessions).
3. Searches open-notebook for project-relevant knowledge.
4. Checks CI/CD status for failures.
5. Runs first-run setup if needed.
6. Spawns session watcher if enabled.
7. Cleans up stale state files.

Exit 0 + additionalContext. Never blocks, never crashes.
"""
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

# --- Add hooks dir to path for lib import ---
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.services import (
    HonchoClient,
    OpenNotebookClient,
    detect_peer_id,
    detect_project_name,
    log_error,
)
from lib.state import SessionState

HOOK_NAME = "session_start"


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    session_id = data.get("session_id", "unknown")
    cwd = str(Path.cwd())
    peer_id = detect_peer_id(cwd)
    project = detect_project_name(cwd)

    # --- Initialize session state ---
    state = SessionState(session_id)
    state.is_initialized = True
    state.save()

    # --- Clean up legacy state files from pre-v4.0 ---
    SessionState.cleanup_legacy()
    SessionState.cleanup_stale(keep=5)

    parts = []

    # --- Worktree context (TASK-2026-00629 pattern) ---
    # If cwd is inside a worktree created by bin/agent-worktree.sh, surface the
    # task-id + branch so the assistant knows it's in an isolated WIP and can
    # bump the heartbeat lock. Read-only — never raises.
    try:
        from datetime import UTC, datetime

        wt_lock = Path(cwd) / ".agent-worktree.lock"
        if not wt_lock.is_file():
            # Walk up to 8 parents — handles cwd = subdir of worktree
            for ancestor in list(Path(cwd).parents)[:8]:
                cand = ancestor / ".agent-worktree.lock"
                if cand.is_file():
                    wt_lock = cand
                    break
        if wt_lock.is_file():
            wt_fields: dict[str, str] = {}
            for line in wt_lock.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    wt_fields[k.strip()] = v.strip()
            task_id = wt_fields.get("task_id")
            if task_id:
                wt_msg = f"WORKTREE: {task_id}"
                branch = wt_fields.get("branch")
                if branch:
                    wt_msg += f" (branch: {branch})"
                created = wt_fields.get("created_at")
                if created:
                    try:
                        dt = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
                        age_h = int((datetime.now(UTC) - dt).total_seconds() // 3600)
                        wt_msg += f" — age {age_h}h"
                    except (ValueError, TypeError):
                        pass
                wt_msg += ". Bump heartbeat: touch .agent-worktree.lock"
                parts.append(wt_msg)
    except Exception as e:  # noqa: BLE001
        log_error(HOOK_NAME, f"worktree-detect failed: {e}", f"cwd={cwd}")

    # --- Honcho: create session + load context ---
    honcho_ok = False
    try:
        honcho = HonchoClient(timeout=10.0)
        if honcho.is_healthy():
            honcho_ok = True
            honcho.create_session(
                session_id=session_id,
                peer_id=peer_id,
                metadata={"source": "session-start", "cwd": cwd, "project": project},
            )
            context = honcho.get_peer_context(peer_id)
            if context and len(context) > 20:
                parts.append(f"HONCHO CONTEXT ({peer_id}): {context[:800]}")

            search_results = honcho.search_peer(
                peer_id=peer_id,
                query=f"session summary {project}",
                limit=5,
            )
            if search_results:
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
                query=f"{project} current status",
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

    # --- Plugin paths ---
    plugin_root = Path(__file__).resolve().parent.parent

    # --- First-run setup check ---
    try:
        from lib.state import STATE_DIR
        setup_marker = STATE_DIR / ".setup-done-v2"
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

    # --- CI/CD Status Check ---
    try:
        is_windows = platform.system() == "Windows"
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
                    parts.append(
                        f"CI FAILURE: Last run '{ci_name}' on {ci_branch} FAILED. "
                        f"Fix before pushing. Check: /meta-ci --last-failure"
                    )
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
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
        pass

    # --- Output: CI failures and critical warnings as additionalContext ---
    actionable = [p for p in parts if "CI FAILURE" in p or "CRITICAL" in p]
    if actionable:
        print(json.dumps({"additionalContext": " | ".join(actionable)}))

    sys.exit(0)


if __name__ == "__main__":
    main()
