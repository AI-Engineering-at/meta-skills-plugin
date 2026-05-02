#!/usr/bin/env python3
"""Analyze Claude Code session history to find repeated patterns.

Usage:
  python analyze-sessions.py                    # Last 5 sessions
  python analyze-sessions.py --sessions 10      # Last 10 sessions
  python analyze-sessions.py --project /path    # Specific project

Output: JSON on stdout with extracted patterns.

Session files: ~/.claude/projects/<project-hash>/*.jsonl
Each line: {"type":"...", "message":{"role":"...", "content":"..."}, ...}
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SCHEMA_VERSION = 1


def find_session_files(
    project_path: Path | None = None, max_sessions: int = 5
) -> list[Path]:
    """Find JSONL session files, newest first."""
    if project_path and project_path.exists():
        search_dir = project_path
    else:
        # Try current project hash
        claude_dir = Path.home() / ".claude" / "projects"
        if not claude_dir.exists():
            return []
        # Find all project dirs, use most recently modified
        project_dirs = sorted(
            claude_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not project_dirs:
            return []
        search_dir = project_dirs[0]

    jsonl_files = sorted(
        [
            f
            for f in search_dir.glob("*.jsonl")
            if f.stat().st_size > 100 and f.stat().st_size < 50_000_000
        ],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return jsonl_files[:max_sessions]


def parse_session(path: Path) -> dict:
    """Parse a single JSONL session file."""
    tools_used = Counter()
    files_accessed = Counter()
    bash_commands = []
    user_messages = []
    skills_invoked = []
    corrections = 0  # User message right after an error
    turns = 0
    last_was_error = False
    skipped_lines = 0

    with Path(path).open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                skipped_lines += 1
                continue

            msg = entry.get("message", {})
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                turns += 1
                if isinstance(content, str):
                    user_messages.append(content[:200])
                    if last_was_error:
                        corrections += 1
                last_was_error = False

            elif role == "assistant":
                last_was_error = False
                # Check for tool use in content blocks
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            tool_name = block.get("name", "")
                            if tool_name:
                                tools_used[tool_name] += 1

                            # Extract file paths from Read/Write/Edit
                            tool_input = block.get("input", {})
                            if isinstance(tool_input, dict):
                                fp = tool_input.get("file_path", "")
                                if fp:
                                    files_accessed[fp] += 1

                                # Extract bash commands
                                cmd = tool_input.get("command", "")
                                if cmd and tool_name == "Bash":
                                    bash_commands.append(cmd[:200])

                                # Extract skill invocations
                                skill = tool_input.get("skill", "")
                                if skill:
                                    skills_invoked.append(skill)

            # Detect errors
            if entry.get("type") == "tool_result":
                result = entry.get("result", "")
                if isinstance(result, str) and (
                    "error" in result.lower() or "Error" in result
                ):
                    last_was_error = True

    return {
        "file": str(path.name),
        "turns": turns,
        "tools": dict(tools_used.most_common(15)),
        "files": dict(files_accessed.most_common(10)),
        "bash_commands": bash_commands[:20],
        "skills_invoked": skills_invoked,
        "user_message_count": len(user_messages),
        "corrections": corrections,
        "skipped_lines": skipped_lines,
    }


def aggregate(sessions: list[dict]) -> dict:
    """Aggregate patterns across sessions."""
    all_tools = Counter()
    all_files = Counter()
    all_commands = []
    all_skills = []
    total_turns = 0
    total_corrections = 0

    for s in sessions:
        all_tools.update(s["tools"])
        all_files.update(s["files"])
        all_commands.extend(s["bash_commands"])
        all_skills.extend(s["skills_invoked"])
        total_turns += s["turns"]
        total_corrections += s["corrections"]

    # Find repeated bash command patterns (normalize whitespace, strip args)
    cmd_patterns = Counter()
    for cmd in all_commands:
        # Normalize: take first 2 words as pattern
        parts = cmd.strip().split()
        if len(parts) >= 2:
            pattern = f"{parts[0]} {parts[1]}"
        elif parts:
            pattern = parts[0]
        else:
            continue
        cmd_patterns[pattern] += 1

    # Find files accessed across multiple sessions
    cross_session_files = Counter()
    for s in sessions:
        for f in s["files"]:
            cross_session_files[f] += 1  # Count sessions, not accesses

    # Skill sequences (for v2.0 meta:flow preparation)
    skill_sequences = []
    for s in sessions:
        if len(s["skills_invoked"]) >= 2:
            skill_sequences.append(s["skills_invoked"])

    return {
        "sessions_analyzed": len(sessions),
        "total_turns": total_turns,
        "total_corrections": total_corrections,
        "total_skipped_lines": sum(s.get("skipped_lines", 0) for s in sessions),
        "top_tools": dict(all_tools.most_common(10)),
        "top_files": dict(
            Counter(
                {f: c for f, c in cross_session_files.items() if c >= 2}
            ).most_common(10)
        ),
        "repeated_commands": dict(
            Counter({p: c for p, c in cmd_patterns.items() if c >= 3}).most_common(10)
        ),
        "skill_usage": dict(Counter(all_skills).most_common(10)),
        "skill_sequences": skill_sequences[
            :5
        ],  # v2.0 prep: ordered skill lists per session
    }


def main():
    try:
        parser = argparse.ArgumentParser(
            description="Analyze Claude Code session history"
        )
        parser.add_argument(
            "--sessions",
            type=int,
            default=5,
            help="Number of recent sessions to analyze",
        )
        parser.add_argument(
            "--project", type=str, default=None, help="Project directory path"
        )
        args = parser.parse_args()

        project_path = Path(args.project) if args.project else None
        files = find_session_files(project_path, args.sessions)

        if not files:
            print(
                json.dumps(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "error": "No session files found",
                        "searched": str(Path.home() / ".claude" / "projects"),
                    }
                )
            )
            sys.exit(0)

        sessions = [parse_session(f) for f in files]
        result = aggregate(sessions)
        result["per_session"] = [
            {"file": s["file"], "turns": s["turns"], "skills": s["skills_invoked"]}
            for s in sessions
        ]
        result["schema_version"] = SCHEMA_VERSION

        print(json.dumps(result, indent=2))
    except Exception as e:
        print(
            json.dumps(
                {"schema_version": SCHEMA_VERSION, "error": str(e), "fatal": True}
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
