#!/usr/bin/env python3
"""
claude-tabs — Read + Control aller offenen Claude Code Sessions.

Architektur (final nach Deep Research 2026-05-12):
    Cowork-Claude (mich)
        ↓ MCP (Phase 2) oder direkter CLI-Call (Phase 1)
    [claude-tabs/cli.py]
        ↓ Read: ~/.claude/projects/**/*.jsonl
        ↓ Send: claude_agent_sdk.query(resume=session_id, session_store_flush="eager")
    [laufende Claude Code CLI Sessions in Warp-Tabs]

Key insight: session_store_flush="eager" gibt near-real-time Transkript-Mirror,
löst Lock-Konflikt-Problem zwischen externem resume und parallel laufender Session.

Usage:
    python cli.py list [--max 25] [--active-only]
    python cli.py status [--project PATTERN] [--session-id ID]
    python cli.py tail SESSION_ID [--lines 30]
    python cli.py send SESSION_ID "prompt text"
    python cli.py scan [--max-files 50]
    python cli.py find-waiting
    python cli.py find-errors

Install once on Joe's machine:
    pip install claude-agent-sdk
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# Force UTF-8 stdout/stderr on Windows (Python 3.14 default is still cp1252)
# — avoids UnicodeEncodeError on emojis (🔴 🟡 🟢) and box-drawing chars
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass


# ────────────────────────────────────────────────────────────────────────────
# Paths
# ────────────────────────────────────────────────────────────────────────────

CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"


# ────────────────────────────────────────────────────────────────────────────
# Token-Leak Patterns (für scan command)
# ────────────────────────────────────────────────────────────────────────────

TOKEN_PATTERNS: dict[str, re.Pattern] = {
    "GitHub PAT": re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    "GitHub OAuth": re.compile(r"gho_[A-Za-z0-9]{36,}"),
    "GitHub Fine-Grained": re.compile(r"github_pat_[A-Za-z0-9_]{82,}"),
    "OpenAI Key": re.compile(r"sk-(?:proj-)?[A-Za-z0-9]{40,}"),
    "Anthropic Key": re.compile(r"sk-ant-[A-Za-z0-9_-]{90,}"),
    "AWS Access Key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "JWT-like Token": re.compile(
        r"eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"
    ),
    "Slack Bot Token": re.compile(r"xox[bp]-[A-Za-z0-9-]{40,}"),
    "Stripe Key": re.compile(r"(?:sk|pk)_(?:test|live)_[A-Za-z0-9]{24,}"),
}


# ────────────────────────────────────────────────────────────────────────────
# Data classes
# ────────────────────────────────────────────────────────────────────────────


@dataclass
class SessionInfo:
    project_dir: str
    session_id: str
    jsonl_path: Path
    last_modified: datetime
    minutes_ago: float
    size_kb: float
    cwd: str

    @property
    def short_id(self) -> str:
        return self.session_id[:8]


@dataclass
class SessionStatus:
    session: SessionInfo
    classification: (
        str  # "waiting-for-input" | "executing-tool" | "completed" | "error" | "active"
    )
    total_events: int
    last_user_text: Optional[str] = None
    last_assistant_text: Optional[str] = None
    last_tool_use: Optional[str] = None
    has_error: bool = False


# ────────────────────────────────────────────────────────────────────────────
# Core: enumerate + read sessions
# ────────────────────────────────────────────────────────────────────────────


def _decode_project_dir(name: str) -> str:
    """C--Users-Legion-Documents-Playbook01 → C:\\Users\\Legion\\Documents\\Playbook01"""
    if name.startswith("C--"):
        return "C:\\" + name[3:].replace("-", "\\")
    return name.replace("-", "/")


def list_sessions(
    active_only: bool = False, max_results: int = 25
) -> list[SessionInfo]:
    """Enumerate the latest JSONL per project dir, sort by recency."""
    if not CLAUDE_PROJECTS.exists():
        raise FileNotFoundError(f"Claude projects dir not found: {CLAUDE_PROJECTS}")

    results: list[SessionInfo] = []
    now = datetime.now(timezone.utc).astimezone()

    for project_dir in CLAUDE_PROJECTS.iterdir():
        if not project_dir.is_dir():
            continue
        jsonls = sorted(
            project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not jsonls:
            continue
        latest = jsonls[0]
        stat = latest.stat()
        last_mod = datetime.fromtimestamp(stat.st_mtime).astimezone()
        minutes = (now - last_mod).total_seconds() / 60
        results.append(
            SessionInfo(
                project_dir=project_dir.name,
                session_id=latest.stem,
                jsonl_path=latest,
                last_modified=last_mod,
                minutes_ago=round(minutes, 1),
                size_kb=round(stat.st_size / 1024, 1),
                cwd=_decode_project_dir(project_dir.name),
            )
        )

    results.sort(key=lambda s: s.minutes_ago)
    if active_only:
        results = [s for s in results if s.minutes_ago < 60]
    return results[:max_results]


def _tail_lines(path: Path, n: int = 30) -> list[str]:
    """Read last n lines of a (possibly large) JSONL file efficiently."""
    with path.open("rb") as f:
        f.seek(0, 2)
        end = f.tell()
        chunk_size = 8192
        data = b""
        while len(data.splitlines()) <= n + 1 and end > 0:
            read_size = min(chunk_size, end)
            end -= read_size
            f.seek(end)
            data = f.read(read_size) + data
    lines = data.splitlines()
    return [ln.decode("utf-8", errors="replace") for ln in lines[-n:]]


def classify_session(info: SessionInfo, tail_lines: int = 30) -> SessionStatus:
    """Parse the tail and classify state."""
    lines = _tail_lines(info.jsonl_path, tail_lines)

    # Count total events approximately (line count of file)
    total = sum(1 for _ in info.jsonl_path.open("rb"))

    last_user_text: Optional[str] = None
    last_assistant_text: Optional[str] = None
    last_tool_use: Optional[str] = None
    has_error = False
    stop_reason: Optional[str] = None

    for line in reversed(lines):
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        msg = obj.get("message", {})
        content = msg.get("content")

        if obj.get("type") == "user" and last_user_text is None:
            if isinstance(content, str):
                last_user_text = content[:300]
            elif isinstance(content, list) and content:
                first = content[0]
                if isinstance(first, dict):
                    if first.get("type") == "tool_result":
                        result = first.get("content", "")
                        if isinstance(result, str):
                            last_user_text = f"[tool_result] {result[:300]}"
                        if first.get("is_error"):
                            has_error = True
                    else:
                        last_user_text = json.dumps(first)[:300]

        if obj.get("type") == "assistant" and last_assistant_text is None:
            if msg.get("stop_reason"):
                stop_reason = msg["stop_reason"]
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text" and last_assistant_text is None:
                            last_assistant_text = block.get("text", "")[:500]
                        elif block.get("type") == "tool_use" and last_tool_use is None:
                            last_tool_use = block.get("name", "?")

    # Classification logic
    if has_error:
        classification = "error"
    elif stop_reason == "end_turn":
        classification = "waiting-for-input"
    elif last_tool_use:
        classification = "executing-tool"
    elif last_assistant_text:
        classification = "active"
    else:
        classification = "unknown"

    return SessionStatus(
        session=info,
        classification=classification,
        total_events=total,
        last_user_text=last_user_text,
        last_assistant_text=last_assistant_text,
        last_tool_use=last_tool_use,
        has_error=has_error,
    )


# ────────────────────────────────────────────────────────────────────────────
# Send via Claude Agent SDK
# ────────────────────────────────────────────────────────────────────────────


async def send_prompt(
    session_id_prefix: str, prompt: str, cwd: str | None = None
) -> str:
    """
    Send a prompt to an existing session by resuming it.

    Uses claude_agent_sdk with session_store_flush="eager" for safe parallel
    operation alongside a running session in a Warp tab.
    """
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError:
        raise RuntimeError(
            "claude_agent_sdk not installed. Run: pip install claude-agent-sdk"
        )

    # Find matching session
    info = _find_session_by_prefix(session_id_prefix)
    if info is None:
        raise ValueError(f"Session not found for prefix: {session_id_prefix}")

    effective_cwd = cwd or info.cwd
    options = ClaudeAgentOptions(
        resume=info.session_id,
        cwd=effective_cwd,
        session_store_flush="eager",  # KEY: near-real-time mirror, no lock conflict
    )

    output_chunks: list[str] = []
    async for message in query(prompt=prompt, options=options):
        # message is a streaming message object — collect text content
        if hasattr(message, "content"):
            for block in getattr(message, "content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    output_chunks.append(block.get("text", ""))
        elif isinstance(message, dict) and message.get("type") == "text":
            output_chunks.append(message.get("text", ""))

    return "\n".join(output_chunks)


def _find_session_by_prefix(prefix: str) -> Optional[SessionInfo]:
    """Find a session by ID prefix (e.g. '66966474')."""
    for project_dir in CLAUDE_PROJECTS.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl in project_dir.glob(f"{prefix}*.jsonl"):
            stat = jsonl.stat()
            now = datetime.now(timezone.utc).astimezone()
            last_mod = datetime.fromtimestamp(stat.st_mtime).astimezone()
            return SessionInfo(
                project_dir=project_dir.name,
                session_id=jsonl.stem,
                jsonl_path=jsonl,
                last_modified=last_mod,
                minutes_ago=round((now - last_mod).total_seconds() / 60, 1),
                size_kb=round(stat.st_size / 1024, 1),
                cwd=_decode_project_dir(project_dir.name),
            )
    return None


# ────────────────────────────────────────────────────────────────────────────
# Security scan
# ────────────────────────────────────────────────────────────────────────────


@dataclass
class TokenLeak:
    project_dir: str
    session_id: str
    token_type: str
    preview: str
    full_match: str


def scan_for_token_leaks(max_files: int = 50) -> list[TokenLeak]:
    """Scan recent session JSONLs for plaintext credential leaks."""
    sessions = list_sessions(max_results=max_files)
    findings: list[TokenLeak] = []

    for info in sessions:
        try:
            content = info.jsonl_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for token_name, pattern in TOKEN_PATTERNS.items():
            for match in pattern.finditer(content):
                token = match.group(0)
                findings.append(
                    TokenLeak(
                        project_dir=info.project_dir,
                        session_id=info.short_id,
                        token_type=token_name,
                        preview=token[:15] + "...",
                        full_match=token,
                    )
                )

    return findings


# ────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────


def _cmd_list(args) -> int:
    sessions = list_sessions(active_only=args.active_only, max_results=args.max)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        **asdict(s),
                        "jsonl_path": str(s.jsonl_path),
                        "last_modified": s.last_modified.isoformat(),
                    }
                    for s in sessions
                ],
                indent=2,
            )
        )
    else:
        print(f"{'Project':<45} {'MinAgo':>8} {'SizeKB':>8} {'ID':<10}")
        print("-" * 75)
        for s in sessions:
            proj = s.project_dir.replace("C--Users-Legion-", "").replace(
                "Documents-", ""
            )
            print(
                f"{proj[:45]:<45} {s.minutes_ago:>8.1f} {s.size_kb:>8.1f} {s.short_id:<10}"
            )
    return 0


def _cmd_status(args) -> int:
    sessions = list_sessions(max_results=100)
    if args.project:
        sessions = [
            s for s in sessions if args.project.lower() in s.project_dir.lower()
        ]
    if args.session_id:
        sessions = [s for s in sessions if s.session_id.startswith(args.session_id)]
    if args.active_only:
        sessions = [s for s in sessions if s.minutes_ago < 60]
    if not sessions:
        print("No matching sessions.", file=sys.stderr)
        return 1

    for s in sessions:
        status = classify_session(s, tail_lines=args.lines)
        icon = {
            "error": "🔴",
            "waiting-for-input": "🟡",
            "executing-tool": "🟢",
            "active": "🟢",
            "completed": "⚪",
            "unknown": "❔",
        }.get(status.classification, "❔")
        print(f"\n=== {s.project_dir} — {s.short_id} ===")
        print(f"Last mod: {s.last_modified.isoformat()}  ({s.minutes_ago:.1f} min ago)")
        print(f"Events: {status.total_events}")
        print(f"Status: {icon} {status.classification}")
        if status.last_user_text:
            print(f"[USER LAST] {status.last_user_text}")
        if status.last_assistant_text:
            print(f"[ASSIST LAST] {status.last_assistant_text}")
        if status.last_tool_use:
            print(f"[TOOL] {status.last_tool_use}")
    return 0


def _cmd_tail(args) -> int:
    info = _find_session_by_prefix(args.session_id)
    if info is None:
        print(f"Session not found: {args.session_id}", file=sys.stderr)
        return 1
    lines = _tail_lines(info.jsonl_path, args.lines)
    for line in lines:
        print(line)
    return 0


def _cmd_send(args) -> int:
    import asyncio

    try:
        result = asyncio.run(send_prompt(args.session_id, args.prompt, cwd=args.cwd))
        print("=== Response ===")
        print(result)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_scan(args) -> int:
    findings = scan_for_token_leaks(max_files=args.max_files)
    if not findings:
        print(f"✅ No plaintext credentials in last {args.max_files} sessions.")
        return 0
    print(f"🔴 {len(findings)} potential token leaks found:\n")
    print(f"{'Project':<40} {'Session':<10} {'Type':<22} {'Preview':<20}")
    print("─" * 95)
    for f in findings:
        print(
            f"{f.project_dir[:40]:<40} {f.session_id:<10} {f.token_type:<22} {f.preview:<20}"
        )
    if args.show_full:
        print("\n=== Full token values ===")
        for f in findings:
            print(f"  {f.project_dir} :: {f.full_match}")
    return 1  # exit code 1 to signal "leaks found"


def _cmd_find_waiting(args) -> int:
    sessions = list_sessions(active_only=True, max_results=100)
    waiting = []
    for s in sessions:
        try:
            status = classify_session(s, tail_lines=30)
            if status.classification == "waiting-for-input":
                waiting.append((s, status))
        except Exception:
            continue
    if not waiting:
        print("No sessions currently waiting for input.")
        return 0
    print(f"🟡 {len(waiting)} session(s) waiting for input:\n")
    for s, st in waiting:
        proj = s.project_dir.replace("C--Users-Legion-", "").replace("Documents-", "")
        print(f"  {proj} — {s.short_id} — {s.minutes_ago:.1f} min ago")
        if st.last_assistant_text:
            print(f"    last said: {st.last_assistant_text[:200]}")
    return 0


def _cmd_find_errors(args) -> int:
    sessions = list_sessions(max_results=100)
    errored = []
    for s in sessions:
        try:
            status = classify_session(s, tail_lines=50)
            if status.has_error or status.classification == "error":
                errored.append((s, status))
        except Exception:
            continue
    if not errored:
        print("✅ No errored sessions in last 100.")
        return 0
    print(f"🔴 {len(errored)} session(s) with errors:\n")
    for s, st in errored:
        proj = s.project_dir.replace("C--Users-Legion-", "").replace("Documents-", "")
        print(f"  {proj} — {s.short_id} — {s.minutes_ago:.1f} min ago")
        if st.last_user_text:
            print(f"    last tool result: {st.last_user_text[:200]}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="claude-tabs", description=__doc__.splitlines()[0]
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="enumerate all sessions")
    p_list.add_argument("--max", type=int, default=25)
    p_list.add_argument("--active-only", action="store_true")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=_cmd_list)

    p_status = sub.add_parser("status", help="classify session(s) state")
    p_status.add_argument(
        "--project", help="project name pattern (case-insensitive substring)"
    )
    p_status.add_argument("--session-id", help="session ID prefix")
    p_status.add_argument("--active-only", action="store_true")
    p_status.add_argument("--lines", type=int, default=30)
    p_status.set_defaults(func=_cmd_status)

    p_tail = sub.add_parser("tail", help="raw tail of a session's JSONL")
    p_tail.add_argument("session_id", help="session ID prefix")
    p_tail.add_argument("--lines", type=int, default=30)
    p_tail.set_defaults(func=_cmd_tail)

    p_send = sub.add_parser(
        "send", help="send a prompt to a session (via claude_agent_sdk)"
    )
    p_send.add_argument("session_id", help="session ID prefix")
    p_send.add_argument("prompt", help="prompt text to send")
    p_send.add_argument(
        "--cwd", help="override CWD (defaults to project's decoded dir)"
    )
    p_send.set_defaults(func=_cmd_send)

    p_scan = sub.add_parser("scan", help="security-scan for plaintext credential leaks")
    p_scan.add_argument("--max-files", type=int, default=50)
    p_scan.add_argument(
        "--show-full",
        action="store_true",
        help="print full token values (for rotation)",
    )
    p_scan.set_defaults(func=_cmd_scan)

    p_fw = sub.add_parser("find-waiting", help="list sessions waiting for user input")
    p_fw.set_defaults(func=_cmd_find_waiting)

    p_fe = sub.add_parser("find-errors", help="list sessions with errors")
    p_fe.set_defaults(func=_cmd_find_errors)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
