#!/usr/bin/env python3
"""hardening-run.py -- Automated hardening pass with evidence capture.

Runs every SCAN check from skills/harden/references/scan-checks.md, captures
raw stdout+stderr to per-check log files, and generates a markdown report
that LINKS every claim back to the captured evidence file.

Design goal: reproducibility. Every number in the report traces to a log
file that can be re-read or re-generated. No narrative-only claims.

Usage:
    python scripts/hardening-run.py
    python scripts/hardening-run.py --ci        # exit 1 on CRITICAL
    python scripts/hardening-run.py --date 2026-04-17

Artifacts:
    oversight/hardening-<date>/
        00-summary.json        machine-readable metrics
        01-py_compile.log
        02-json-schema.log
        03-ruff.log
        04-validate.log
        05-eval.log
        06-reworker.log
        07-promote-corrections.log
        08-skill-registry.log
    oversight/hardening-<date>.md   human-readable report (links to logs)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_ROOT.parent


@dataclass
class CheckResult:
    """Outcome of a single hardening check."""
    name: str
    slug: str
    cmd: list[str]
    cwd: Path
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_s: float = 0.0
    metrics: dict = field(default_factory=dict)  # parsed numbers
    critical: bool = False

    @property
    def log_filename(self) -> str:
        return f"{self.slug}.log"


def run_check(name: str, slug: str, cmd: list[str], cwd: Path, timeout: int = 120) -> CheckResult:
    """Execute a check, return structured result. Never raises."""
    result = CheckResult(name=name, slug=slug, cmd=cmd, cwd=cwd)
    t0 = datetime.now(UTC).timestamp()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )
        result.returncode = proc.returncode
        result.stdout = proc.stdout or ""
        result.stderr = proc.stderr or ""
    except subprocess.TimeoutExpired as e:
        result.returncode = -1
        result.stderr = f"TIMEOUT after {timeout}s: {e}"
        result.critical = True
    except FileNotFoundError as e:
        result.returncode = -1
        result.stderr = f"TOOL NOT FOUND: {e}"
        # Missing tool is not critical by itself; noted in report
    except Exception as e:
        result.returncode = -1
        result.stderr = f"UNEXPECTED ERROR: {type(e).__name__}: {e}"
        result.critical = True
    result.duration_s = datetime.now(UTC).timestamp() - t0
    return result


def write_log(artifact_dir: Path, result: CheckResult) -> Path:
    """Write per-check log file to artifact dir. Returns path."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    log_path = artifact_dir / result.log_filename
    content = (
        f"# {result.name}\n"
        f"# cmd: {' '.join(result.cmd)}\n"
        f"# cwd: {result.cwd}\n"
        f"# returncode: {result.returncode}\n"
        f"# duration: {result.duration_s:.2f}s\n"
        f"# generated: {datetime.now(UTC).isoformat()}\n"
        f"# ──────── STDOUT ────────\n"
        f"{result.stdout}\n"
        f"# ──────── STDERR ────────\n"
        f"{result.stderr}\n"
    )
    log_path.write_text(content, encoding="utf-8")
    return log_path


# ─── Metric parsers (extract numbers from tool output) ─────────────────

def parse_ruff(r: CheckResult) -> dict:
    """Parse 'Found N errors' lines from ruff output."""
    m = re.search(r"Found (\d+) error", r.stdout + r.stderr)
    errors = int(m.group(1)) if m else 0
    return {"errors": errors, "clean": errors == 0}


def parse_validate(r: CheckResult) -> dict:
    """Parse validate.py summary block."""
    out = r.stdout + r.stderr
    total = int(m.group(1)) if (m := re.search(r"Total:\s+(\d+)", out)) else 0
    errors = int(m.group(1)) if (m := re.search(r"Errors:\s+(\d+)", out)) else 0
    warnings = int(m.group(1)) if (m := re.search(r"Warnings:\s+(\d+)", out)) else 0
    return {"total": total, "errors": errors, "warnings": warnings}


def parse_eval(r: CheckResult) -> dict:
    """Parse eval.py --all JSON output."""
    try:
        data = json.loads(r.stdout)
        results = data.get("results", [])
        scores = [x["quality"]["score"] for x in results if "quality" in x]
        below_70 = [x["name"] for x in results if x.get("quality", {}).get("score", 100) < 70]
        return {
            "total": data.get("total", 0),
            "skills": data.get("skills", 0),
            "agents": data.get("agents", 0),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "below_70_count": len(below_70),
            "below_70_names": below_70[:10],
        }
    except Exception:
        return {"parse_error": True}


def parse_pycompile(r: CheckResult) -> dict:
    """py_compile prints nothing on success; any output = failure."""
    failures = [line for line in (r.stdout + r.stderr).splitlines() if "FAIL" in line or "Error" in line]
    return {"clean": r.returncode == 0 and not failures, "failures": failures}


def parse_json_schema(r: CheckResult) -> dict:
    return {"clean": r.returncode == 0 and "OK" in r.stdout}


# ─── Check catalogue (matches skills/harden/references/scan-checks.md) ──

def run_all_checks(artifact_dir: Path) -> list[CheckResult]:
    results = []

    # 1a. Python syntax
    py_files = list((PLUGIN_ROOT / "hooks").glob("*.py")) + list((PLUGIN_ROOT / "scripts").glob("*.py"))
    r = run_check(
        "Python syntax (py_compile)",
        "01-py_compile",
        [sys.executable, "-m", "py_compile", *map(str, py_files)],
        PLUGIN_ROOT,
    )
    r.metrics = parse_pycompile(r)
    if not r.metrics["clean"]:
        r.critical = True
    results.append(r)

    # 1b. JSON schema
    hooks_json = PLUGIN_ROOT / "hooks" / "hooks.json"
    plugin_json = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    r = run_check(
        "JSON schema (hooks.json + plugin.json)",
        "02-json-schema",
        [sys.executable, "-c",
         f"import json; json.load(open(r'{hooks_json}')); json.load(open(r'{plugin_json}')); print('OK')"],
        PLUGIN_ROOT,
    )
    r.metrics = parse_json_schema(r)
    if not r.metrics["clean"]:
        r.critical = True
    results.append(r)

    # 1c. Ruff lint
    r = run_check("Ruff lint", "03-ruff", ["ruff", "check", "hooks/", "scripts/"], PLUGIN_ROOT)
    r.metrics = parse_ruff(r)
    results.append(r)

    # 1d. Frontmatter validation
    r = run_check(
        "Frontmatter validation",
        "04-validate",
        [sys.executable, "scripts/validate.py"],
        PLUGIN_ROOT,
    )
    r.metrics = parse_validate(r)
    if r.metrics.get("errors", 0) > 0:
        r.critical = True
    results.append(r)

    # 1e. Eval (quality scores) -- must run from REPO_ROOT per eval.py design
    r = run_check(
        "Skill + agent quality scores (eval.py)",
        "05-eval",
        [sys.executable, "meta-skills/scripts/eval.py", "--all"],
        REPO_ROOT,
    )
    r.metrics = parse_eval(r)
    if r.metrics.get("below_70_count", 0) > 0:
        r.critical = True
    results.append(r)

    # 1f. Reworker diagnostics
    r = run_check(
        "Reworker diagnostics",
        "06-reworker",
        [sys.executable, "scripts/reworker.py", "--diagnose", "--top", "10"],
        PLUGIN_ROOT,
        timeout=180,
    )
    r.metrics = {"output_lines": len(r.stdout.splitlines())}
    results.append(r)

    # 1g. Correction promotion
    r = run_check(
        "Correction promotion candidates",
        "07-promote-corrections",
        [sys.executable, "scripts/promote-corrections.py"],
        PLUGIN_ROOT,
    )
    m = re.search(r"Promotion Candidates \((\d+)\)", r.stdout)
    r.metrics = {"candidates": int(m.group(1)) if m else 0}
    results.append(r)

    # 1h. Skill registry
    r = run_check(
        "Skill registry build",
        "08-skill-registry",
        [sys.executable, "scripts/build-skill-registry.py", "--check"],
        PLUGIN_ROOT,
    )
    r.metrics = {"returncode": r.returncode}
    results.append(r)

    for r in results:
        write_log(artifact_dir, r)

    return results


# ─── Report generation ────────────────────────────────────────────────

def write_summary_json(artifact_dir: Path, results: list[CheckResult]) -> Path:
    """Machine-readable summary."""
    summary = {
        "generated": datetime.now(UTC).isoformat(),
        "plugin_root": str(PLUGIN_ROOT),
        "checks": [
            {
                "name": r.name,
                "slug": r.slug,
                "log_file": r.log_filename,
                "returncode": r.returncode,
                "duration_s": round(r.duration_s, 2),
                "critical": r.critical,
                "metrics": r.metrics,
            }
            for r in results
        ],
        "critical_count": sum(1 for r in results if r.critical),
    }
    path = artifact_dir / "00-summary.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return path


def _sanitize(text: str) -> str:
    """Replace env-specific absolute paths with portable placeholders.

    Committed markdown reports must not leak the maintainer's home path,
    username, or Python install location. Applied to cd-commands and cmd
    strings in write_markdown_report. Handles both forward- and backslash
    path separators (Windows mixes them).
    """
    if not text:
        return text
    substitutions = [
        (str(PLUGIN_ROOT).replace("\\", "/"), "<plugin_root>"),
        (str(PLUGIN_ROOT), "<plugin_root>"),
        (str(REPO_ROOT).replace("\\", "/"), "<repo_root>"),
        (str(REPO_ROOT), "<repo_root>"),
        (sys.executable.replace("\\", "/"), "python"),
        (sys.executable, "python"),
        (str(Path.home()).replace("\\", "/"), "~"),
        (str(Path.home()), "~"),
    ]
    for before, after in substitutions:
        if before:  # skip empty prefixes
            text = text.replace(before, after)
    return text


def write_markdown_report(report_path: Path, artifact_dir: Path, results: list[CheckResult], date: str) -> None:
    """Human-readable report linking to every evidence file.

    Paths are sanitized: absolute paths are replaced with <plugin_root> /
    <repo_root> / ~ placeholders so the committed .md is portable and does
    not leak the maintainer's env.
    """
    rel = artifact_dir.name  # 'hardening-2026-04-17'
    lines = [
        f"# Hardening Report {date}",
        "",
        f"Generated by `scripts/hardening-run.py` at {datetime.now(UTC).isoformat()}.",
        f"All metrics below link to captured log files in `oversight/{rel}/`.",
        "",
        "## Summary",
        "",
        "| Check | Result | Evidence |",
        "|---|---|---|",
    ]
    for r in results:
        if r.metrics.get("clean") is True:
            result_cell = "clean"
        elif r.metrics.get("errors", 0) > 0:
            result_cell = f"{r.metrics['errors']} errors"
        elif "avg_score" in r.metrics:
            below = r.metrics.get("below_70_count", 0)
            result_cell = f"{r.metrics.get('total', 0)} components, avg {r.metrics.get('avg_score')}, {below} below 70"
        elif "candidates" in r.metrics:
            result_cell = f"{r.metrics['candidates']} promotion candidates"
        elif r.returncode == 0:
            result_cell = "ok"
        else:
            result_cell = f"rc={r.returncode}"
        if r.critical:
            result_cell = "CRITICAL — " + result_cell
        link = f"[`{r.log_filename}`]({rel}/{r.log_filename})"
        lines.append(f"| {r.name} | {result_cell} | {link} |")

    critical = [r for r in results if r.critical]
    lines.extend([
        "",
        f"**Critical findings:** {len(critical)}",
        "",
    ])
    if critical:
        for r in critical:
            lines.append(f"- {r.name}: see `{r.log_filename}`")
        lines.append("")

    lines.extend([
        "## Reproduction",
        "",
        "Re-run the full hardening pass:",
        "",
        "```bash",
        "cd <plugin_root>",
        "python scripts/hardening-run.py",
        "```",
        "",
        "Individual check commands (for manual re-run):",
        "",
    ])
    for r in results:
        cmd_str = _sanitize(" ".join(r.cmd))
        cwd_str = _sanitize(r.cwd.as_posix())
        lines.append(f"- **{r.name}** (`{rel}/{r.log_filename}`)")
        lines.append("  ```")
        lines.append(f"  cd {cwd_str}")
        lines.append(f"  {cmd_str}")
        lines.append("  ```")
    lines.append("")

    lines.extend([
        "## Raw artifact index",
        "",
        f"- Machine-readable summary: [`{rel}/00-summary.json`]({rel}/00-summary.json)",
    ])
    for r in results:
        lines.append(f"- {r.name}: [`{rel}/{r.log_filename}`]({rel}/{r.log_filename})")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ci", action="store_true", help="exit non-zero on CRITICAL")
    ap.add_argument("--date", default=None, help="override date (default: today UTC)")
    args = ap.parse_args()

    date = args.date or datetime.now(UTC).strftime("%Y-%m-%d")
    artifact_dir = PLUGIN_ROOT / "oversight" / f"hardening-{date}"
    report_path = PLUGIN_ROOT / "oversight" / f"hardening-{date}.md"

    print(f"Hardening run: {date}")
    print(f"  Plugin root:  {PLUGIN_ROOT}")
    print(f"  Artifact dir: {artifact_dir}")
    print(f"  Report:       {report_path}")
    print()

    results = run_all_checks(artifact_dir)

    for r in results:
        status = "CRITICAL" if r.critical else ("ok" if r.returncode == 0 else f"rc={r.returncode}")
        print(f"  [{status:>8}] {r.name:50s} {r.duration_s:.2f}s")

    write_summary_json(artifact_dir, results)
    write_markdown_report(report_path, artifact_dir, results, date)
    print(f"\nReport written: {report_path}")

    critical = sum(1 for r in results if r.critical)
    print(f"Critical findings: {critical}")

    if args.ci and critical > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
