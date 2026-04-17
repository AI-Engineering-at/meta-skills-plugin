#!/usr/bin/env python3
"""Harden — Deterministic Quality Scan + Report Engine

Runs ALL quality checks without LLM calls. Pure Python, deterministic.
This is the ENGINE behind the /meta-harden skill.

Usage:
  python3 harden.py                    # Full scan, human-readable output
  python3 harden.py --scan             # Same as default
  python3 harden.py --json             # JSON output for CI/CD
  python3 harden.py --check hooks      # Only check hooks
  python3 harden.py --check skills     # Only check skills
  python3 harden.py --check lint       # Only check lint
  python3 harden.py --check all        # All checks (default)
  python3 harden.py --auto-fix         # Fix auto-fixable issues via reworker
  python3 harden.py --report           # Generate markdown report
"""
import json
import os
import py_compile
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    Path(__file__).parent.parent
))
PHANTOM_ROOT = PLUGIN_ROOT.parent
REPORT_DIR = PLUGIN_ROOT / "oversight"


def check_python_syntax(directory: Path) -> list:
    """Check all .py files for syntax errors."""
    findings = []
    for py_file in sorted(directory.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            findings.append({
                "severity": "CRITICAL",
                "category": "syntax",
                "file": str(py_file.relative_to(PLUGIN_ROOT)),
                "description": f"Syntax error: {e}",
                "auto_fixable": False,
            })
    return findings


def check_json_schemas() -> list:
    """Validate all JSON config files."""
    findings = []
    json_files = [
        PLUGIN_ROOT / "hooks" / "hooks.json",
        PLUGIN_ROOT / ".claude-plugin" / "plugin.json",
        Path.home() / ".claude" / "settings.json",
    ]
    for jf in json_files:
        if not jf.exists():
            findings.append({
                "severity": "WARNING",
                "category": "schema",
                "file": str(jf),
                "description": f"File not found: {jf.name}",
                "auto_fixable": False,
            })
            continue
        try:
            json.loads(jf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            findings.append({
                "severity": "CRITICAL",
                "category": "schema",
                "file": str(jf),
                "description": f"Invalid JSON: {e}",
                "auto_fixable": False,
            })
    return findings


def check_hooks() -> list:
    """Check hooks for crash-safety, exit-0, timeout handling."""
    findings = []
    hooks_dir = PLUGIN_ROOT / "hooks"

    for hook_file in sorted(hooks_dir.glob("*.py")):
        content = hook_file.read_text(encoding="utf-8")
        name = hook_file.stem

        # Check: try/except around stdin parsing
        if "sys.stdin.read()" in content and "try:" not in content:
            findings.append({
                "severity": "CRITICAL",
                "category": "hooks",
                "file": f"hooks/{name}.py",
                "description": "Missing try/except around stdin parsing (hook can crash)",
                "auto_fixable": False,
            })

        # Check: sys.exit(0) as default
        if "sys.exit(0)" not in content:
            findings.append({
                "severity": "CRITICAL",
                "category": "hooks",
                "file": f"hooks/{name}.py",
                "description": "Missing sys.exit(0) default (hook can block)",
                "auto_fixable": False,
            })

        # Check: subprocess timeout
        if "subprocess.run" in content and "timeout" not in content:
            findings.append({
                "severity": "WARNING",
                "category": "hooks",
                "file": f"hooks/{name}.py",
                "description": "subprocess.run without timeout parameter",
                "auto_fixable": False,
            })

        # Check: Windows shell=True only relevant for .cmd / .bat wrappers.
        # Skip when calls go through sys.executable (always python.exe) or
        # known .exe binaries (git, ruff, gh, ssh, scp). Only flag when there is
        # a bare program name that could resolve to a .cmd shim on Windows.
        SAFE_BINARIES = ("sys.executable", '"git"', "'git'", '"ruff"', "'ruff'",
                         '"gh"', "'gh'", '"ssh"', "'ssh'", '"scp"', "'scp'",
                         '"docker"', "'docker'")
        if "subprocess.run" in content and "shell=" not in content:
            if not any(safe in content for safe in SAFE_BINARIES):
                findings.append({
                    "severity": "INFO",
                    "category": "hooks",
                    "file": f"hooks/{name}.py",
                    "description": "subprocess.run without shell= (may fail on Windows .cmd wrappers)",
                    "auto_fixable": False,
                })

    return findings


def check_skills() -> list:
    """Check SKILL.md files for quality issues."""
    findings = []
    skills_dir = PLUGIN_ROOT / "skills"

    for skill_dir in sorted(skills_dir.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        content = skill_file.read_text(encoding="utf-8")
        name = skill_dir.name
        lines = content.split("\n")

        # Parse frontmatter (handles YAML multiline values like description: >)
        fm = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                current_key = None
                current_val = []
                for line in parts[1].strip().split("\n"):
                    if ":" in line and not line.startswith(" ") and not line.startswith("-"):
                        if current_key:
                            fm[current_key] = " ".join(current_val).strip()
                        key, _, val = line.partition(":")
                        current_key = key.strip()
                        val = val.strip()
                        if val in (">", "|", ">-", "|-"):
                            current_val = []
                        else:
                            current_val = [val]
                    elif (line.startswith("  ") and current_key) or (line.startswith("-") and current_key):
                        current_val.append(line.strip())
                if current_key:
                    fm[current_key] = " ".join(current_val).strip()
                body_lines = parts[2].strip().split("\n")
            else:
                body_lines = lines
        else:
            body_lines = lines

        # Check: version field
        if "version" not in fm:
            findings.append({
                "severity": "WARNING",
                "category": "skills",
                "file": f"skills/{name}/SKILL.md",
                "description": "Missing 'version' field in frontmatter (+10 eval points)",
                "auto_fixable": True,
            })

        # Check: token-budget field
        if "token-budget" not in fm:
            findings.append({
                "severity": "WARNING",
                "category": "skills",
                "file": f"skills/{name}/SKILL.md",
                "description": "Missing 'token-budget' field in frontmatter (+15 eval points)",
                "auto_fixable": True,
            })

        # Check: body length
        body_count = len([l for l in body_lines if l.strip()])
        if body_count > 150:
            findings.append({
                "severity": "WARNING",
                "category": "skills",
                "file": f"skills/{name}/SKILL.md",
                "description": f"Body too long ({body_count} lines > 150). Move details to references/",
                "auto_fixable": False,
            })

        # Check: German content in body
        german_count = 0
        german_patterns = re.compile(
            r"\b(Wenn |Fuer |Oder |Pruef|Nutze|Zeige|Sammle|Gruppiere|Fuehre|"
            r"Starte|Wiederhol|Zurueck|Danach|Frage|Kooperativ|Einheitlich|"
            r"Erkennt|Warnt|Nicht |Kein |Sofort|Immer|Nie )\b", re.IGNORECASE
        )
        for line in body_lines:
            if german_patterns.search(line):
                german_count += 1

        if german_count > 2:
            findings.append({
                "severity": "WARNING",
                "category": "skills",
                "file": f"skills/{name}/SKILL.md",
                "description": f"{german_count} German lines in body (Rule 05: Docs = English)",
                "auto_fixable": False,
            })

        # Check: trigger words in description OR separate trigger field
        desc = fm.get("description", "")
        has_trigger_field = "trigger" in fm  # separate frontmatter field
        if not has_trigger_field and "trigger" not in desc.lower() and "when" not in desc.lower():
            findings.append({
                "severity": "INFO",
                "category": "skills",
                "file": f"skills/{name}/SKILL.md",
                "description": "No trigger keywords in description (reduces discoverability)",
                "auto_fixable": False,
            })

    return findings


def check_lint() -> list:
    """Run ruff check on Python files."""
    findings = []
    try:
        result = subprocess.run(
            ["ruff", "check", str(PLUGIN_ROOT / "hooks"), str(PLUGIN_ROOT / "scripts")],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0 and result.stdout:
            for line in result.stdout.strip().split("\n")[:20]:
                findings.append({
                    "severity": "WARNING",
                    "category": "lint",
                    "file": line.split(":")[0] if ":" in line else "unknown",
                    "description": line.strip(),
                    "auto_fixable": True,
                })
    except (FileNotFoundError, subprocess.TimeoutExpired):
        findings.append({
            "severity": "INFO",
            "category": "lint",
            "file": "-",
            "description": "ruff not available or timed out",
            "auto_fixable": False,
        })
    return findings


def check_consistency() -> list:
    """Check cross-file consistency."""
    findings = []

    # Skill count in CLAUDE.md vs actual
    claude_md = PLUGIN_ROOT / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        skills_actual = len(list((PLUGIN_ROOT / "skills").iterdir()))
        match = re.search(r"\*\*(\d+)\s+Skills\*\*", content)
        if match:
            skills_documented = int(match.group(1))
            if skills_documented != skills_actual:
                findings.append({
                    "severity": "WARNING",
                    "category": "consistency",
                    "file": "CLAUDE.md",
                    "description": f"Skill count mismatch: CLAUDE.md says {skills_documented}, actual {skills_actual}",
                    "auto_fixable": False,
                })

    # Hook count
    hooks_actual = len(list((PLUGIN_ROOT / "hooks").glob("*.py")))
    if claude_md.exists():
        match = re.search(r"\*\*(\d+)\s+Hooks\*\*", content)
        if match:
            hooks_documented = int(match.group(1))
            if hooks_documented != hooks_actual:
                findings.append({
                    "severity": "WARNING",
                    "category": "consistency",
                    "file": "CLAUDE.md",
                    "description": f"Hook count mismatch: CLAUDE.md says {hooks_documented}, actual {hooks_actual}",
                    "auto_fixable": False,
                })

    return findings


def run_all_checks(check_filter: str = "all") -> list:
    """Run all checks and return combined findings."""
    all_findings = []

    checks = {
        "syntax": lambda: check_python_syntax(PLUGIN_ROOT / "hooks") + check_python_syntax(PLUGIN_ROOT / "scripts"),
        "schema": check_json_schemas,
        "hooks": check_hooks,
        "skills": check_skills,
        "lint": check_lint,
        "consistency": check_consistency,
    }

    for name, check_fn in checks.items():
        if check_filter != "all" and check_filter != name:
            continue
        try:
            findings = check_fn()
            all_findings.extend(findings)
        except Exception as e:
            all_findings.append({
                "severity": "WARNING",
                "category": name,
                "file": "-",
                "description": f"Check failed: {e}",
                "auto_fixable": False,
            })

    return all_findings


def generate_report(findings: list) -> str:
    """Generate human-readable report."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    criticals = [f for f in findings if f["severity"] == "CRITICAL"]
    warnings = [f for f in findings if f["severity"] == "WARNING"]
    infos = [f for f in findings if f["severity"] == "INFO"]
    auto_fixable = [f for f in findings if f.get("auto_fixable")]

    lines = [
        f"# Hardening Report ({now})",
        "",
        f"Total findings: {len(findings)}",
        f"  CRITICAL: {len(criticals)}",
        f"  WARNING:  {len(warnings)}",
        f"  INFO:     {len(infos)}",
        f"  Auto-fixable: {len(auto_fixable)}",
        "",
    ]

    if criticals:
        lines.append("## CRITICAL")
        for f in criticals:
            lines.append(f"- [{f['category']}] {f['file']}: {f['description']}")
        lines.append("")

    if warnings:
        lines.append("## WARNING")
        for f in warnings:
            marker = " [auto-fix]" if f.get("auto_fixable") else ""
            lines.append(f"- [{f['category']}] {f['file']}: {f['description']}{marker}")
        lines.append("")

    if infos:
        lines.append("## INFO")
        for f in infos:
            lines.append(f"- [{f['category']}] {f['file']}: {f['description']}")
        lines.append("")

    return "\n".join(lines)


def main():
    as_json = "--json" in sys.argv
    auto_fix = "--auto-fix" in sys.argv
    report_only = "--report" in sys.argv
    check_filter = "all"

    for i, arg in enumerate(sys.argv):
        if arg == "--check" and i + 1 < len(sys.argv):
            check_filter = sys.argv[i + 1]

    # Run checks
    findings = run_all_checks(check_filter)

    if as_json:
        print(json.dumps({
            "timestamp": datetime.now(UTC).isoformat(),
            "total": len(findings),
            "critical": len([f for f in findings if f["severity"] == "CRITICAL"]),
            "warning": len([f for f in findings if f["severity"] == "WARNING"]),
            "info": len([f for f in findings if f["severity"] == "INFO"]),
            "auto_fixable": len([f for f in findings if f.get("auto_fixable")]),
            "findings": findings,
        }, indent=2, ensure_ascii=False))
        return

    report = generate_report(findings)

    if report_only:
        report_file = REPORT_DIR / f"hardening-{datetime.now(UTC).strftime('%Y-%m-%d')}.md"
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_file.write_text(report, encoding="utf-8")
        print(f"Report saved: {report_file}")
    else:
        print(report)

    if auto_fix:
        auto = [f for f in findings if f.get("auto_fixable")]
        if auto:
            print(f"\nAuto-fixing {len(auto)} issues via reworker.py...")
            reworker = PLUGIN_ROOT / "scripts" / "reworker.py"
            if reworker.exists():
                subprocess.run(
                    [sys.executable, str(reworker), "--apply"],
                    cwd=str(PHANTOM_ROOT), timeout=30,
                )
            # Lint auto-fix
            lint_issues = [f for f in auto if f["category"] == "lint"]
            if lint_issues:
                subprocess.run(
                    ["ruff", "check", "--fix",
                     str(PLUGIN_ROOT / "hooks"), str(PLUGIN_ROOT / "scripts")],
                    capture_output=True, timeout=30,
                )
                print("  ruff --fix applied")


if __name__ == "__main__":
    main()
