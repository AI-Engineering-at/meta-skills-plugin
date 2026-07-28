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

from __future__ import annotations  # `str | None` braucht das unter Python 3.9

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



def _gitea_ci_zustand(basis: str, besitzer: str, repo: str) -> str | None:
    """Commit-Status des Standardzweigs auf Gitea — oder None, wenn nicht ermittelbar.

    Gitea hat keine GitHub-artige Actions-API (`/actions/runs` liefert 404). Der Zustand
    steht am Commit. Denselben Weg benutzt `aie-gitea-ci-watcher` — existing-first.

    Ein leerer `state` heisst „kein Lauf", nicht „gruen". Beides zu vermischen waere genau
    die Klasse, die am 2026-07-28 sechsmal auftrat.
    """
    from lib.services import vault_get  # noqa: PLC0415 — sys.path ist oben gesetzt

    tok = vault_get("_shared", "gitea", "API_TOKEN") or vault_get("shared", "gitea", "API_TOKEN")
    if not tok:
        return None
    kopf = {"Authorization": f"token {tok}"}
    zweig = _http_json(f"{basis}/api/v1/repos/{besitzer}/{repo}/branches/main", kopf)
    if not zweig:
        return None
    sha = ((zweig.get("commit") or {}).get("id") or "")[:40]
    if not sha:
        return None
    st = _http_json(f"{basis}/api/v1/repos/{besitzer}/{repo}/commits/{sha}/status", kopf)
    zustand = (st or {}).get("state") or ""
    return zustand or None


def _http_json(url: str, headers: dict) -> dict | None:
    import urllib.error
    import urllib.request

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as a:
            return json.loads(a.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


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
        from datetime import datetime, timezone
        
        # Python 3.9 (macOS-Systeminterpreter) kennt `datetime.UTC` nicht — das gibt es erst
        # ab 3.11. Ohne diesen Umweg stirbt der Hook beim Import, endet mit 0, und schreibt nie.
        UTC = timezone.utc
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
                        dt = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(
                            tzinfo=UTC
                        )
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
                    r
                    for r in search_results
                    if len(r) > 30
                    and not r.strip().startswith(
                        (
                            "cd ",
                            "python ",
                            "curl ",
                            "docker ",
                            "git ",
                            "ls ",
                            "cat ",
                            "grep ",
                            "find ",
                            "ssh ",
                            "scp ",
                        )
                    )
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
                capture_output=True,
                text=True,
                timeout=5,
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

    # --- CI-Status: GITEA, nicht GitHub ---
    #
    # ANLASS (2026-07-28, Joe: "github? wofuer wir nutzen gitea?"): hier stand
    # `gh run list` — ein GitHub-Aufruf bei jedem Sitzungsstart.
    #
    # Gitea ist die Code-Quelle, GitHub nur der oeffentliche Spiegel. Der Hook fragte also
    # das falsche System: er meldete den Zustand eines Spiegels, waehrend unsere CI auf
    # Gitea laeuft. Gemessen am selben Tag: beide Repos auf Gitea **rot**, und der Hook
    # haette nur von GitHub berichtet.
    #
    # Gitea kennt keine GitHub-artige Actions-API (`/actions/runs` -> 404). Der Weg ist der
    # Commit-Status, genau wie ihn unser eigener `aie-gitea-ci-watcher` benutzt:
    #   GET /api/v1/repos/{o}/{r}/branches/{br}        -> commit.id
    #   GET /api/v1/repos/{o}/{r}/commits/{sha}/status -> {"state": "success|failure|..."}
    #
    # Der Token kommt aus dem Tresor, nicht aus einer Umgebungsvariablen — sonst laeuft es
    # nur dort, wo zufaellig `GITEA_API_TOKEN` gesetzt ist.
    try:
        is_windows = platform.system() == "Windows"
        git_check = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=3, shell=is_windows, cwd=cwd,
        )
        if git_check.returncode == 0:
            fern = subprocess.run(
                ["git", "remote", "get-url", "gitea"],
                capture_output=True, text=True, timeout=3, cwd=cwd,
            )
            url = (fern.stdout or "").strip()
            if fern.returncode == 0 and "/" in url:
                # http://host:port/owner/repo.git  ->  (basis, owner, repo)
                rest = url.rsplit("/", 2)
                repo = rest[-1].removesuffix(".git")
                besitzer = rest[-2]
                basis = url[: url.index(f"/{besitzer}/{repo}")]
                zustand = _gitea_ci_zustand(basis, besitzer, repo)
                if zustand in ("failure", "error"):
                    parts.append(
                        f"CI ROT auf Gitea: {besitzer}/{repo} — der letzte Lauf auf dem "
                        f"Standardzweig ist {zustand}. Vor dem naechsten Push ansehen."
                    )
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, ValueError):
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
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    [sys.executable, str(watcher), "--parent-pid", str(parent_pid)],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
    except Exception:
        pass

    # --- Output: CI failures and critical warnings as additionalContext ---
    # Was durchgereicht wird, haengt an einer Textsuche — und die ist zerbrechlich.
    #
    # ANLASS (2026-07-28): ich habe die CI-Meldung von "CI FAILURE: ..." auf "CI ROT auf
    # Gitea: ..." umformuliert. Der Filter suchte weiter woertlich nach "CI FAILURE", also
    # entstand die Meldung und **erreichte niemanden**. Der Hook lief, endete mit 0, gab
    # 0 Byte aus. Siebter Fall derselben Klasse an einem Tag.
    #
    # Deshalb jetzt eine Liste von Kennzeichen statt zweier fest verdrahteter Zeichenketten
    # — und ein Test, der sie gegen die tatsaechlich erzeugten Meldungen prueft.
    DRINGEND = ("CI FAILURE", "CI ROT", "CRITICAL", "KRITISCH")
    actionable = [p for p in parts if any(k in p for k in DRINGEND)]
    if actionable:
        print(json.dumps({"additionalContext": " | ".join(actionable)}))

    sys.exit(0)


if __name__ == "__main__":
    main()
