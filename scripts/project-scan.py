#!/usr/bin/env python3
"""project-scan.py — Efficient project scanner for Meta Init.

Scans project structure, quality, git status in ONE shot.
Output: compact JSON — saves tokens by doing all scanning in Python.

Usage:
  python project-scan.py                    # Full scan (JSON)
  python project-scan.py --area code        # Code-focused scan
  python project-scan.py --area infra       # Infrastructure scan
  python project-scan.py --area security    # Security scan
  python project-scan.py --area quality     # Quality/eval scan
  python project-scan.py --area all         # Everything
  python project-scan.py --summary          # Human-readable summary
"""
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).parent.parent.parent
META_ROOT = Path(__file__).parent.parent


def run(cmd, timeout=10):
    """Run command, return stdout or empty string."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout, cwd=str(REPO_ROOT))
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def scan_structure():
    """Scan project structure — languages, frameworks, size."""
    extensions = Counter()
    total_files = 0
    total_lines = 0

    skip = {".git", "node_modules", "__pycache__", ".venv", "venv",
            "dist", "build", "out", ".next", "_archive"}

    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in (".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go",
                       ".java", ".md", ".yml", ".yaml", ".json", ".sh"):
                extensions[ext] += 1
                total_files += 1
                try:
                    p = Path(root) / f
                    if p.stat().st_size < 500_000:  # skip huge files
                        with p.open(encoding="utf-8", errors="replace") as _fh:
                            total_lines += sum(1 for _ in _fh)
                except Exception:
                    pass

    # Detect framework
    framework = "unknown"
    if (REPO_ROOT / "package.json").exists():
        try:
            pkg = json.loads((REPO_ROOT / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "next" in deps:
                framework = "nextjs"
            elif "react" in deps:
                framework = "react"
            elif "express" in deps:
                framework = "express"
            elif "fastify" in deps:
                framework = "fastify"
            else:
                framework = "node"
        except Exception:
            framework = "node"
    elif (REPO_ROOT / "pyproject.toml").exists() or any(REPO_ROOT.glob("*.py")):
        framework = "python"
        if (REPO_ROOT / "voice-gateway").exists():
            framework = "fastapi"
    elif (REPO_ROOT / "Cargo.toml").exists():
        framework = "rust"
    elif (REPO_ROOT / "go.mod").exists():
        framework = "go"

    # Primary language
    code_exts = {k: v for k, v in extensions.items() if k in (".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".java")}
    primary_lang = max(code_exts, key=code_exts.get, default="unknown")
    lang_map = {".py": "python", ".ts": "typescript", ".tsx": "typescript",
                ".js": "javascript", ".rs": "rust", ".go": "go", ".java": "java"}

    return {
        "primary_language": lang_map.get(primary_lang, "unknown"),
        "framework": framework,
        "total_files": total_files,
        "total_lines": total_lines,
        "extensions": dict(extensions.most_common(10)),
    }


def scan_claude_structure():
    """Scan .claude/ and meta-skills/ structure."""
    claude_dir = REPO_ROOT / ".claude"
    result = {
        "has_claude_dir": claude_dir.exists(),
        "has_claude_md": (REPO_ROOT / "CLAUDE.md").exists(),
        "rules": [],
        "skills": [],
        "agents": [],
        "meta_skills": [],
        "meta_agents": [],
    }

    if (claude_dir / "rules").exists():
        result["rules"] = sorted([f.name for f in (claude_dir / "rules").glob("*.md")])

    if (claude_dir / "skills").exists():
        for d in sorted((claude_dir / "skills").iterdir()):
            if d.is_dir() and not d.name.startswith(("_", ".")):
                skill_file = d / "SKILL.md"
                if skill_file.exists():
                    result["skills"].append(d.name)

    if (claude_dir / "agents").exists():
        result["agents"] = sorted([f.stem for f in (claude_dir / "agents").glob("*.md")
                                   if not f.name.startswith(("_", "."))])

    if (META_ROOT / "skills").exists():
        for d in sorted((META_ROOT / "skills").iterdir()):
            if d.is_dir() and not d.name.startswith(("_", ".")):
                result["meta_skills"].append(d.name)

    if (META_ROOT / "agents").exists():
        result["meta_agents"] = sorted([f.stem for f in (META_ROOT / "agents").glob("*.md")])

    result["counts"] = {
        "rules": len(result["rules"]),
        "skills": len(result["skills"]),
        "agents": len(result["agents"]),
        "meta_skills": len(result["meta_skills"]),
        "meta_agents": len(result["meta_agents"]),
        "total": len(result["skills"]) + len(result["agents"]) + len(result["meta_skills"]) + len(result["meta_agents"]),
    }
    return result


def scan_git():
    """Scan git status."""
    branch = run(["git", "branch", "--show-current"])
    status = run(["git", "status", "--short"])
    log = run(["git", "log", "--oneline", "-10"])
    remotes = run(["git", "remote", "-v"])
    ahead_behind = run(["git", "rev-list", "--left-right", "--count", f"origin/{branch}...HEAD"]) if branch else ""

    dirty = len([ln for ln in status.splitlines() if ln.strip()]) if status else 0

    ahead = 0
    behind = 0
    if ahead_behind and "\t" in ahead_behind:
        parts = ahead_behind.split("\t")
        behind, ahead = int(parts[0]), int(parts[1])

    return {
        "branch": branch,
        "dirty_files": dirty,
        "ahead": ahead,
        "behind": behind,
        "recent_commits": log.splitlines()[:10] if log else [],
        "remote": remotes.splitlines()[0].split("\t")[1].split(" ")[0] if remotes else "none",
    }


def scan_quality():
    """Run eval.py and validate.py for quality metrics."""
    # validate.py
    val_raw = run(["python", str(META_ROOT / "scripts" / "validate.py"), "--json"], timeout=30)
    validate = {"total": 0, "errors": 0, "warnings": 0}
    if val_raw:
        try:
            v = json.loads(val_raw)
            validate = {"total": v["total"], "errors": v["errors"], "warnings": v["warnings"]}
        except Exception:
            pass

    # eval.py
    eval_raw = run(["python", str(META_ROOT / "scripts" / "eval.py"), "--all"], timeout=30)
    quality = {"total": 0, "avg_score": 0, "below_70": 0, "above_90": 0, "bottom_5": [], "top_5": []}
    if eval_raw:
        try:
            e = json.loads(eval_raw)
            scores = [r["quality"]["score"] for r in e["results"]]
            quality["total"] = e["total"]
            quality["avg_score"] = round(sum(scores) / len(scores), 1) if scores else 0
            quality["below_70"] = sum(1 for s in scores if s < 70)
            quality["above_90"] = sum(1 for s in scores if s >= 90)
            sorted_results = sorted(e["results"], key=lambda x: x["quality"]["score"])
            quality["bottom_5"] = [{"name": r["name"], "score": r["quality"]["score"]}
                                   for r in sorted_results[:5]]
            quality["top_5"] = [{"name": r["name"], "score": r["quality"]["score"]}
                                for r in sorted_results[-5:]]
        except Exception:
            pass

    return {"validate": validate, "eval": quality}


def scan_infra():
    """Scan infrastructure markers."""
    result = {
        "has_docker": (REPO_ROOT / "Dockerfile").exists() or (REPO_ROOT / "docker-compose.yml").exists(),
        "has_ci": (REPO_ROOT / ".github" / "workflows").exists(),
        "has_tests": False,
        "test_framework": "unknown",
        "services": [],
    }

    # Test detection
    if (REPO_ROOT / "pytest.ini").exists() or (REPO_ROOT / "pyproject.toml").exists():
        result["has_tests"] = True
        result["test_framework"] = "pytest"
    if (REPO_ROOT / "vitest.config.ts").exists() or (REPO_ROOT / "jest.config.js").exists():
        result["has_tests"] = True
        result["test_framework"] = "vitest/jest"

    # Docker services
    compose = REPO_ROOT / "docker-compose.yml"
    if compose.exists():
        try:
            text = compose.read_text()
            services = [ln.strip().rstrip(":") for ln in text.splitlines()
                       if ln.strip() and not ln.startswith("#") and ln.endswith(":")
                       and "  " not in ln[:4]]
            result["services"] = services[:20]
        except Exception:
            pass

    # CI workflows
    ci_dir = REPO_ROOT / ".github" / "workflows"
    if ci_dir.exists():
        result["ci_workflows"] = [f.name for f in ci_dir.glob("*.yml")]

    return result


def scan_security():
    """Quick security scan markers."""
    result = {
        "has_env_example": (REPO_ROOT / ".env.example").exists(),
        "has_gitignore": (REPO_ROOT / ".gitignore").exists(),
        "has_vault": (REPO_ROOT / ".claude" / "credentials" / "vault.py").exists(),
        "exposed_secrets": [],
    }

    # Check for common secret patterns in tracked files
    gitignore = (REPO_ROOT / ".gitignore").read_text() if result["has_gitignore"] else ""

    for pattern in [".env", "credentials.json", "secrets.yaml"]:
        p = REPO_ROOT / pattern
        if p.exists() and pattern not in gitignore:
            result["exposed_secrets"].append(pattern)

    return result


def scan_mcp():
    """Discover MCP server configurations."""
    result = {"servers": [], "count": 0}

    # Check .mcp.json in repo root
    mcp_file = REPO_ROOT / ".mcp.json"
    if mcp_file.exists():
        try:
            data = json.loads(mcp_file.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", {})
            for name, cfg in servers.items():
                result["servers"].append({
                    "name": name,
                    "command": cfg.get("command", "unknown"),
                    "transport": cfg.get("type", "stdio"),
                })
        except Exception:
            pass

    # Check user settings.json for MCP servers
    settings_path = Path("~/.claude/settings.json").expanduser()
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            for key in ("mcpServers", "mcp"):
                servers = data.get(key, {})
                if isinstance(servers, dict):
                    for name, cfg in servers.items():
                        if not any(s["name"] == name for s in result["servers"]):
                            result["servers"].append({
                                "name": name,
                                "command": cfg.get("command", "unknown"),
                                "transport": cfg.get("type", "stdio"),
                                "source": "user-settings",
                            })
        except Exception:
            pass

    result["count"] = len(result["servers"])
    return result


def scan_agents_detail():
    """Detailed agent discovery — colors, models, health."""
    agents = []

    for agents_dir in [REPO_ROOT / ".claude" / "agents", META_ROOT / "agents"]:
        if not agents_dir.exists():
            continue
        for f in sorted(agents_dir.glob("*.md")):
            if f.name.startswith(("_", ".")):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                if not text.startswith("---"):
                    continue
                end = text.find("---", 3)
                if end == -1:
                    continue
                fm = text[3:end]
                meta = {}
                for line in fm.strip().splitlines():
                    if ":" in line and not line.startswith("  "):
                        k, _, v = line.partition(":")
                        meta[k.strip()] = v.strip()

                # Health check — what's missing?
                missing = []
                if not meta.get("color"):
                    missing.append("color")
                if not meta.get("model"):
                    missing.append("model")
                if not meta.get("version"):
                    missing.append("version")
                if not meta.get("complexity"):
                    missing.append("complexity")
                has_triggers = "trigger" in meta.get("description", "").lower()
                if not has_triggers:
                    missing.append("triggers")

                agents.append({
                    "name": meta.get("name", f.stem),
                    "color": meta.get("color", "none"),
                    "model": meta.get("model", "unknown"),
                    "complexity": meta.get("complexity", "unknown"),
                    "maxTurns": meta.get("maxTurns", "none"),
                    "missing": missing,
                    "health": "healthy" if len(missing) == 0 else ("warn" if len(missing) <= 2 else "unhealthy"),
                })
            except Exception:
                pass

    healthy = sum(1 for a in agents if a["health"] == "healthy")
    return {
        "agents": agents,
        "total": len(agents),
        "healthy": healthy,
        "unhealthy": len(agents) - healthy,
    }


def full_scan(areas=None):
    """Run all requested scans."""
    if areas is None:
        areas = ["structure", "claude", "git", "quality"]

    result = {"scan_version": 1, "repo_root": str(REPO_ROOT)}

    if "structure" in areas or "all" in areas:
        result["structure"] = scan_structure()
    if "claude" in areas or "all" in areas:
        result["claude"] = scan_claude_structure()
    if "git" in areas or "all" in areas:
        result["git"] = scan_git()
    if "quality" in areas or "all" in areas or "quality" in areas:
        result["quality"] = scan_quality()
    if "infra" in areas or "all" in areas:
        result["infra"] = scan_infra()
    if "security" in areas or "all" in areas:
        result["security"] = scan_security()
    if "mcp" in areas or "all" in areas:
        result["mcp"] = scan_mcp()
    if "agents" in areas or "all" in areas or "discovery" in areas:
        result["agents_detail"] = scan_agents_detail()

    return result


def format_summary(data):
    """Human-readable summary from scan data."""
    lines = ["# Projekt-Scan Ergebnis\n"]

    if "structure" in data:
        s = data["structure"]
        lines.append(f"**Stack:** {s['primary_language']}/{s['framework']} | {s['total_files']} Files | ~{s['total_lines']:,} LOC")

    if "claude" in data:
        c = data["claude"]["counts"]
        lines.append(f"**Meta-Skills:** {c['rules']} Rules | {c['skills']} Skills | {c['agents']} Agents | {c['meta_skills']} Meta-Skills | {c['total']} Total")

    if "quality" in data:
        q = data["quality"]
        v = q["validate"]
        e = q["eval"]
        lines.append(f"**Quality:** Score {e['avg_score']} | {e['total']} Komponenten | {e['below_70']} unter 70 | {e['above_90']} ueber 90")
        lines.append(f"**Schema:** {v['total']} validiert | {v['errors']} Errors | {v['warnings']} Warnings")
        if e["bottom_5"]:
            bottom = ", ".join(f"{b['name']}({b['score']})" for b in e["bottom_5"])
            lines.append(f"**Bottom 5:** {bottom}")

    if "git" in data:
        g = data["git"]
        lines.append(f"**Git:** {g['branch']} | {g['dirty_files']} dirty | +{g['ahead']}/-{g['behind']} vs origin")

    if "infra" in data:
        i = data["infra"]
        lines.append(f"**Infra:** Docker={'✅' if i['has_docker'] else '❌'} | CI={'✅' if i['has_ci'] else '❌'} | Tests={i['test_framework']}")

    if "security" in data:
        sec = data["security"]
        if sec["exposed_secrets"]:
            lines.append(f"**⚠ SECURITY:** Exposed: {', '.join(sec['exposed_secrets'])}")
        else:
            lines.append(f"**Security:** Vault={'✅' if sec['has_vault'] else '❌'} | .gitignore={'✅' if sec['has_gitignore'] else '❌'}")

    if "mcp" in data:
        mcp = data["mcp"]
        names = ", ".join(s["name"] for s in mcp["servers"][:8])
        lines.append(f"**MCP:** {mcp['count']} Server ({names})")

    if "agents_detail" in data:
        ad = data["agents_detail"]
        unhealthy_names = ", ".join(a["name"] for a in ad["agents"] if a["health"] != "healthy")
        lines.append(f"**Agents:** {ad['total']} total | {ad['healthy']} healthy | {ad['unhealthy']} issues{': ' + unhealthy_names if unhealthy_names else ''}")

    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]

    areas = ["structure", "claude", "git", "quality"]
    summary = False

    if "--area" in args:
        idx = args.index("--area")
        if idx + 1 < len(args):
            area = args[idx + 1]
            if area == "all":
                areas = ["structure", "claude", "git", "quality", "infra", "security", "mcp", "agents"]
            elif area == "code":
                areas = ["structure", "git", "quality"]
            elif area == "infra":
                areas = ["structure", "infra"]
            elif area == "security":
                areas = ["security", "claude"]
            elif area == "quality":
                areas = ["quality", "claude"]
            else:
                areas = [area]

    if "--summary" in args:
        summary = True

    if "--all" in args:
        areas = ["structure", "claude", "git", "quality", "infra", "security"]

    data = full_scan(areas)

    if summary:
        print(format_summary(data))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))
