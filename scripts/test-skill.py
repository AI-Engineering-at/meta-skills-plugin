#!/usr/bin/env python3
"""Behavioral Skill Tests — Verify skills WORK, not just that they parse.

Reads test-scenario.md from each skill directory, combines skill body + test
input as a prompt, runs via cheapest available CLI, and checks output against
pass/fail patterns.

Inspired by OpenJudge's Skill Graders (5 graders for agent skill evaluation).

Usage:
  python3 test-skill.py skills/verify                    # Test one skill
  python3 test-skill.py --all                             # Test all skills
  python3 test-skill.py --all --json                      # JSON output
  python3 test-skill.py skills/verify --cli qwen          # Force specific CLI
"""
import argparse
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    Path(__file__).parent.parent
))
SKILLS_DIR = PLUGIN_ROOT / "skills"
RESULTS_DIR = PLUGIN_ROOT / "oversight" / "skill-tests"

IS_WINDOWS = platform.system() == "Windows"

# CLI preference order (cheapest first)
CLI_PREFERENCE = ["qwen", "kimi", "opencode", "codex", "copilot", "claude"]
CLI_COMMANDS = {
    "qwen":     ["qwen", "-p", "{prompt}", "--output-format", "text"],
    "kimi":     ["kimi", "-p", "{prompt}", "--print", "--final-message-only"],
    "opencode": ["opencode", "run", "{prompt}"],
    "codex":    ["codex", "exec", "{prompt}"],
    "copilot":  ["copilot", "-p", "{prompt}", "--allow-all-tools"],
    "claude":   ["claude", "-p", "{prompt}", "--output-format", "text"],
}


def detect_cli() -> str | None:
    """Find cheapest available CLI."""
    for name in CLI_PREFERENCE:
        try:
            result = subprocess.run(
                [name, "--version"], capture_output=True,
                timeout=5, shell=IS_WINDOWS,
            )
            if result.returncode == 0:
                return name
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
    return None


def parse_test_scenario(scenario_path: Path) -> dict:
    """Parse a test-scenario.md file.

    Format:
    ```
    Input: "the test input prompt"
    Expected: what the output should contain
    Pass: regex1|regex2|regex3
    Fail: regex1|regex2
    ```
    """
    if not scenario_path.exists():
        return {}

    content = scenario_path.read_text(encoding="utf-8")
    scenario = {}

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("Input:"):
            scenario["input"] = line[6:].strip().strip('"')
        elif line.startswith("Expected:"):
            scenario["expected"] = line[9:].strip()
        elif line.startswith("Pass:"):
            patterns = line[5:].strip()
            scenario["pass_patterns"] = [p.strip() for p in patterns.split("|") if p.strip()]
        elif line.startswith("Fail:"):
            patterns = line[5:].strip()
            scenario["fail_patterns"] = [p.strip() for p in patterns.split("|") if p.strip()]

    return scenario


def run_skill_test(skill_dir: Path, cli_name: str, timeout: int = 60) -> dict:
    """Run a behavioral test for a single skill."""
    skill_name = skill_dir.name
    skill_file = skill_dir / "SKILL.md"
    scenario_file = skill_dir / "test-scenario.md"

    if not skill_file.exists():
        return {"skill": skill_name, "status": "SKIP", "reason": "No SKILL.md"}

    if not scenario_file.exists():
        return {"skill": skill_name, "status": "SKIP", "reason": "No test-scenario.md"}

    scenario = parse_test_scenario(scenario_file)
    if not scenario.get("input"):
        return {"skill": skill_name, "status": "SKIP", "reason": "No Input in test-scenario.md"}

    # Build the prompt: skill body + test input
    skill_content = skill_file.read_text(encoding="utf-8")
    # Strip frontmatter for the prompt
    body = skill_content
    if body.startswith("---"):
        end = body.find("---", 3)
        if end > 0:
            body = body[end + 3:].strip()

    prompt = (
        f"You are following this skill instruction:\n\n"
        f"{body[:2000]}\n\n"
        f"---\n\n"
        f"Now respond to this input:\n{scenario['input']}\n\n"
        f"Respond concisely (under 200 words)."
    )

    # Run via CLI
    cmd_template = CLI_COMMANDS.get(cli_name, [])
    if not cmd_template:
        return {"skill": skill_name, "status": "ERROR", "reason": f"Unknown CLI: {cli_name}"}

    cmd = [prompt if part == "{prompt}" else part for part in cmd_template]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, shell=IS_WINDOWS,
            env={**os.environ, "TERM": "dumb"},
        )
        output = result.stdout.strip()
        if not output:
            output = result.stderr.strip()
    except subprocess.TimeoutExpired:
        return {"skill": skill_name, "status": "TIMEOUT", "reason": f"CLI timeout ({timeout}s)"}
    except Exception as e:
        return {"skill": skill_name, "status": "ERROR", "reason": str(e)}

    if not output:
        return {"skill": skill_name, "status": "ERROR", "reason": "Empty CLI output"}

    # Check pass/fail patterns
    output_lower = output.lower()
    pass_patterns = scenario.get("pass_patterns", [])
    fail_patterns = scenario.get("fail_patterns", [])

    pass_hits = [p for p in pass_patterns if re.search(p, output_lower)]
    fail_hits = [p for p in fail_patterns if re.search(p, output_lower)]

    pass_score = len(pass_hits) / max(len(pass_patterns), 1)
    has_fail = len(fail_hits) > 0

    if has_fail:
        status = "FAIL"
    elif pass_score >= 0.5:
        status = "PASS"
    else:
        status = "WEAK"  # Some pass patterns matched but not enough

    return {
        "skill": skill_name,
        "status": status,
        "cli": cli_name,
        "pass_score": round(pass_score, 2),
        "pass_hits": pass_hits,
        "fail_hits": fail_hits,
        "output_preview": output[:300],
        "expected": scenario.get("expected", ""),
    }


def main():
    parser = argparse.ArgumentParser(description="Behavioral Skill Tests")
    parser.add_argument("skill_dir", nargs="?", help="Path to skill directory")
    parser.add_argument("--all", action="store_true", help="Test all skills with test-scenario.md")
    parser.add_argument("--cli", default=None, help="Force specific CLI tool")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--timeout", type=int, default=60, help="CLI timeout in seconds")

    args = parser.parse_args()

    if not args.skill_dir and not args.all:
        parser.print_help()
        sys.exit(1)

    # Detect CLI
    cli_name = args.cli or detect_cli()
    if not cli_name:
        print("ERROR: No CLI tool available (qwen, kimi, opencode, codex, copilot, claude)")
        sys.exit(1)

    # Collect targets
    targets = []
    if args.all:
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            if (skill_dir / "test-scenario.md").exists():
                targets.append(skill_dir)
    else:
        targets.append(Path(args.skill_dir))

    if not targets:
        print("No skills with test-scenario.md found.")
        sys.exit(0)

    if not args.json:
        print(f"Behavioral Skill Tests")
        print(f"CLI: {cli_name}")
        print(f"Skills: {len(targets)}")
        print(f"{'='*60}")

    # Run tests
    results = []
    for target in targets:
        if not args.json:
            print(f"\n  Testing: {target.name}...", end=" ", flush=True)
        result = run_skill_test(target, cli_name, timeout=args.timeout)
        results.append(result)
        if not args.json:
            status = result["status"]
            score = result.get("pass_score", 0)
            print(f"[{status}] (score={score})")
            if result.get("fail_hits"):
                print(f"    Fail patterns matched: {result['fail_hits']}")

    # Summary
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    weak = sum(1 for r in results if r["status"] == "WEAK")
    skipped = sum(1 for r in results if r["status"] == "SKIP")

    if args.json:
        print(json.dumps({
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "weak": weak,
            "skipped": skipped,
            "cli": cli_name,
            "results": results,
        }, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*60}")
        print(f"RESULTS: {passed} PASS, {failed} FAIL, {weak} WEAK, {skipped} SKIP")
        print(f"{'='*60}")

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    results_file = RESULTS_DIR / f"skill-test-{now}.json"
    results_file.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8",
    )

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
