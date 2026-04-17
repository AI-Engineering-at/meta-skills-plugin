#!/usr/bin/env python3
"""Audit all installed skills — score quality, freshness, efficiency.

Usage:
  python audit-skills.py                    # Full audit
  python audit-skills.py --json             # JSON output only
  python audit-skills.py --catalog-only     # Just regenerate catalog

Output: JSON with per-skill scores and recommendations.
Side-effect: Writes/updates ${CLAUDE_PLUGIN_DATA}/skill-catalog.json
"""

import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = 1


# ── Churn Rate ───────────────────────────────────────────────────

def get_churn(skill_path: str) -> int:
    """Count git commits that touched this file. 0 if not in git."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--follow", "--", skill_path],
            capture_output=True, text=True, timeout=5, cwd=str(Path.cwd())
        )
        return len(result.stdout.strip().splitlines()) if result.returncode == 0 else 0
    except Exception:
        return 0


# ── Skill Discovery ─────────────────────────────────────────────

def extract_frontmatter(path: Path) -> dict:
    """Extract YAML frontmatter from SKILL.md."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    meta = {}
    current_key = None
    for line in parts[1].strip().splitlines():
        if line.startswith("  ") and current_key:
            # continuation of multi-line value
            meta[current_key] = meta.get(current_key, "") + " " + line.strip()
        elif ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            meta[key] = val
            current_key = key
    # Parse allowed-tools as list
    tools_str = meta.get("allowed-tools", "")
    if tools_str.startswith("["):
        meta["_tools_list"] = [t.strip() for t in tools_str.strip("[]").split(",")]
    else:
        meta["_tools_list"] = []
    # Body length (lines after frontmatter)
    meta["_body_lines"] = len(parts[2].strip().splitlines())
    meta["_path"] = str(path)
    meta["_source"] = "plugin" if ".claude/plugins" in str(path) else "local"
    return meta


def find_all_skills() -> list[dict]:
    """Find ALL SKILL.md files — local project, user skills, plugin cache."""
    skills = []
    search_paths = []

    # Project-local
    cwd = Path.cwd()
    local = cwd / ".claude" / "skills"
    if local.exists():
        search_paths.append(("local", local))

    # User-level
    user_skills = Path.home() / ".claude" / "skills"
    if user_skills.exists():
        search_paths.append(("user", user_skills))

    # Plugin cache
    plugin_cache = Path.home() / ".claude" / "plugins" / "cache"
    if plugin_cache.exists():
        search_paths.append(("plugin", plugin_cache))

    seen_names = set()
    errors = []
    for source, base in search_paths:
        for skill_md in base.rglob("SKILL.md"):
            try:
                meta = extract_frontmatter(skill_md)
                name = meta.get("name", "")
                if name and name not in seen_names:
                    seen_names.add(name)
                    meta["_source"] = source
                    skills.append(meta)
            except Exception as e:
                errors.append({"path": str(skill_md), "error": str(e)})
                continue

    if errors:
        # Attach errors to last skill as a side-channel, or store globally
        # We store on a sentinel entry that main() can check
        skills.append({"_parse_errors": errors, "name": "", "_source": "error"})

    return skills


# ── Scoring ──────────────────────────────────────────────────────

def score_skill(meta: dict, metrics: dict) -> dict:
    """Score a skill on 5 criteria. Returns score dict with recommendations."""
    name = meta.get("name", "unknown")
    scores = {}
    issues = []

    # 1. Freshness (30%) — last-verified or last-audit date
    last_date = meta.get("last-verified") or meta.get("last-audit") or meta.get("created-date", "")
    if last_date:
        try:
            d = datetime.strptime(str(last_date), "%Y-%m-%d")
            age_days = (datetime.now() - d).days
            if age_days <= 14:
                scores["freshness"] = 1.0
            elif age_days <= 30:
                scores["freshness"] = 0.7
            elif age_days <= 60:
                scores["freshness"] = 0.4
                issues.append(f"Stale: last verified {age_days} days ago")
            else:
                scores["freshness"] = 0.1
                issues.append(f"Very stale: last verified {age_days} days ago")
        except ValueError:
            scores["freshness"] = 0.5
    else:
        scores["freshness"] = 0.3
        issues.append("No last-verified or last-audit date")

    # 2. Token efficiency (25%) — has token-budget? Progressive disclosure?
    has_budget = bool(meta.get("token-budget"))
    body_lines = meta.get("_body_lines", 0)
    tools_count = len(meta.get("_tools_list", []))

    if has_budget and body_lines <= 150 and tools_count <= 4:
        scores["efficiency"] = 1.0
    elif has_budget and body_lines <= 200:
        scores["efficiency"] = 0.7
    elif body_lines <= 150:
        scores["efficiency"] = 0.5
        if not has_budget:
            issues.append("No token-budget set")
    else:
        scores["efficiency"] = 0.3
        issues.append(f"SKILL.md is {body_lines} lines (target: <150)")
        if tools_count > 5:
            issues.append(f"{tools_count} tools in allowed-tools (reduce to save context tokens)")

    # 3. Trigger precision (15%) — description length and trigger words
    desc = meta.get("description", "")
    desc_lines = len(desc.strip().splitlines()) if desc else 0
    has_trigger_words = bool(re.search(r"[Tt]rigger", desc))

    if desc_lines <= 3 and has_trigger_words:
        scores["triggers"] = 1.0
    elif desc_lines <= 3:
        scores["triggers"] = 0.7
        issues.append("No explicit trigger words in description")
    elif desc_lines <= 5:
        scores["triggers"] = 0.5
    else:
        scores["triggers"] = 0.3
        issues.append(f"Description is {desc_lines} lines (target: <=3)")

    # 4. Documentation quality (10%) — frontmatter completeness
    required = ["name", "description", "model", "version"]
    recommended = ["allowed-tools", "user-invocable"]
    meta_fields = ["type", "token-budget", "category"]

    present_req = sum(1 for f in required if meta.get(f))
    present_rec = sum(1 for f in recommended if meta.get(f))
    present_meta = sum(1 for f in meta_fields if meta.get(f))

    doc_score = (present_req / len(required)) * 0.5 + (present_rec / len(recommended)) * 0.3 + (present_meta / len(meta_fields)) * 0.2
    scores["documentation"] = round(doc_score, 2)
    missing = [f for f in required if not meta.get(f)]
    if missing:
        issues.append(f"Missing required fields: {', '.join(missing)}")

    # 5. Usage (20%) — from session metrics
    usage = metrics.get(name, {})
    use_count = usage.get("use_count", 0)
    if use_count >= 10:
        scores["usage"] = 1.0
    elif use_count >= 5:
        scores["usage"] = 0.7
    elif use_count >= 1:
        scores["usage"] = 0.4
    else:
        scores["usage"] = 0.1
        if meta.get("_source") == "local":
            issues.append("Never used (0 invocations in tracked sessions)")

    # Weighted total
    weights = {"freshness": 0.3, "usage": 0.2, "efficiency": 0.25, "triggers": 0.15, "documentation": 0.1}
    total = sum(scores[k] * weights[k] for k in weights)

    # Churn rate
    churn = get_churn(meta.get("_path", ""))

    # Recommendation
    if total >= 0.7:
        recommendation = "keep"
    elif total >= 0.5:
        if scores["efficiency"] < 0.5:
            recommendation = "optimize"
        elif scores["freshness"] < 0.3:
            recommendation = "update"
        else:
            recommendation = "review"
    elif total >= 0.3:
        if scores["usage"] <= 0.1 and meta.get("_source") == "local":
            recommendation = "archive"
        else:
            recommendation = "optimize"
    else:
        recommendation = "archive"

    return {
        "name": name,
        "source": meta.get("_source", "unknown"),
        "score": round(total, 2),
        "scores": {k: round(v, 2) for k, v in scores.items()},
        "recommendation": recommendation,
        "issues": issues,
        "model": meta.get("model", "unknown"),
        "body_lines": body_lines,
        "tools": meta.get("_tools_list", []),
        "token_budget": meta.get("token-budget"),
        "category": meta.get("category", "uncategorized"),
        "churn": churn,
    }


# ── Usage Metrics ────────────────────────────────────────────────

def load_metrics() -> dict:
    """Load usage metrics from session-metrics.jsonl."""
    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA", str(Path.home() / ".claude" / "plugins" / "data" / "meta-skills"))
    metrics_file = Path(data_dir) / "session-metrics.jsonl"
    if not metrics_file.exists():
        return {}

    skill_counts = Counter()
    try:
        with metrics_file.open() as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    for skill in entry.get("skill_sequence", []):
                        if isinstance(skill, dict):
                            skill_counts[skill.get("skill", "")] += 1
                        elif isinstance(skill, str):
                            skill_counts[skill] += 1
                except json.JSONDecodeError:
                    continue
    except Exception:
        return {}

    return {name: {"use_count": count} for name, count in skill_counts.items()}


# ── Catalog Generation ───────────────────────────────────────────

CATEGORY_KEYWORDS = {
    "infrastructure": ["deploy", "swarm", "docker", "node", "monitoring", "stack", "pve", "vm", "infra"],
    "documentation": ["docs", "sync", "index", "knowledge", "wiki", "doc", "navigator"],
    "automation": ["schedule", "loop", "cron", "batch", "workflow", "n8n"],
    "meta": ["creator", "feedback", "design", "review", "reflect", "audit"],
    "analysis": ["benchmark", "audit", "check", "verify", "test", "eval"],
    "communication": ["mattermost", "telegram", "email", "notify", "mm-wait", "echo-log"],
    "security": ["vault", "red-team", "security", "credential"],
    "recovery": ["recovery", "backup", "dr-", "raft"],
}


def auto_categorize(name: str, description: str) -> str:
    """Auto-assign category based on name + description keywords."""
    text = f"{name} {description}".lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw in text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "uncategorized"


def generate_catalog(audit_results: list[dict], skills_meta: list[dict]) -> dict:
    """Generate skill-catalog.json with categories, stats, and related fields."""
    categories = defaultdict(lambda: {"description": "", "skills": []})
    stats = {}

    for result in audit_results:
        name = result["name"]
        cat = result.get("category", "uncategorized")
        if cat == "uncategorized":
            # Try auto-categorize
            meta = next((m for m in skills_meta if m.get("name") == name), {})
            cat = auto_categorize(name, meta.get("description", ""))

        categories[cat]["skills"].append(name)
        stats[name] = {
            "score": result["score"],
            "recommendation": result["recommendation"],
            "model": result.get("model", "unknown"),
            "token_budget": result.get("token_budget"),
            "source": result.get("source", "unknown"),
            "churn": result.get("churn", 0),
            "related": [],  # v2.0 prep: populated from session co-occurrence
        }

    # Set category descriptions
    cat_descriptions = {
        "infrastructure": "Server, Docker, Swarm, Nodes, Monitoring, VMs",
        "documentation": "Docs, Sync, Index, Knowledge Base, Wiki",
        "automation": "Scheduling, Workflows, Batch Processing, n8n",
        "meta": "Process improvement, Skill creation, Feedback, Design",
        "analysis": "Benchmarks, Audits, Testing, Evaluation",
        "communication": "Mattermost, Telegram, Notifications",
        "security": "Vault, Credentials, Red-Team, Security Reviews",
        "recovery": "Disaster Recovery, Backup, Swarm Recovery",
        "uncategorized": "Skills not yet categorized",
    }
    for cat in categories:
        categories[cat]["description"] = cat_descriptions.get(cat, "")

    return {
        "version": "1.0",
        "last_audit": datetime.now().strftime("%Y-%m-%d"),
        "total_skills": len(audit_results),
        "categories": dict(categories),
        "stats": stats,
    }


# ── Main ─────────────────────────────────────────────────────────

def main():
    try:
        catalog_only = "--catalog-only" in sys.argv
        json_output = "--json" in sys.argv

        skills_meta_raw = find_all_skills()

        # Separate parse errors from real skills
        parse_errors = []
        skills_meta = []
        for m in skills_meta_raw:
            if "_parse_errors" in m:
                parse_errors.extend(m["_parse_errors"])
            elif m.get("name"):
                skills_meta.append(m)

        metrics = load_metrics()

        # Score all skills
        results = [score_skill(m, metrics) for m in skills_meta]
        results.sort(key=lambda x: x["score"])

        # Generate catalog
        catalog = generate_catalog(results, skills_meta)

        # Write catalog
        data_dir = os.environ.get("CLAUDE_PLUGIN_DATA", str(Path.home() / ".claude" / "plugins" / "data" / "meta-skills"))
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        catalog_path = Path(data_dir) / "skill-catalog.json"
        with catalog_path.open("w") as f:
            json.dump(catalog, f, indent=2)

        if catalog_only:
            print(json.dumps({"schema_version": SCHEMA_VERSION, "catalog_written": str(catalog_path), "total_skills": len(results)}))
            return

        # Summary
        recs = Counter(r["recommendation"] for r in results)
        summary = {
            "schema_version": SCHEMA_VERSION,
            "total_skills": len(results),
            "by_source": dict(Counter(r["source"] for r in results)),
            "by_recommendation": dict(recs),
            "by_category": {cat: len(data["skills"]) for cat, data in catalog["categories"].items()},
            "parse_errors": parse_errors,
            "needs_attention": [
                {"name": r["name"], "score": r["score"], "recommendation": r["recommendation"], "issues": r["issues"][:3]}
                for r in results if r["recommendation"] in ("archive", "optimize", "update")
            ][:10],
            "top_skills": [
                {"name": r["name"], "score": r["score"]}
                for r in sorted(results, key=lambda x: x["score"], reverse=True)[:5]
            ],
            "catalog_path": str(catalog_path),
        }

        if json_output:
            print(json.dumps({"schema_version": SCHEMA_VERSION, "summary": summary, "skills": results}, indent=2))
        else:
            print(json.dumps(summary, indent=2))
    except Exception as e:
        print(json.dumps({"schema_version": SCHEMA_VERSION, "error": str(e), "fatal": True}))
        sys.exit(1)


if __name__ == "__main__":
    main()
