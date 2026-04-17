#!/usr/bin/env python3
"""Filter eval.py output to only show the 15 meta-skills from this repo."""
import json
import sys

data = json.load(sys.stdin)
meta_skills = []
for r in data["results"]:
    path = r["path"].replace("\\", "/")
    if "meta-skills/skills" in path:
        q = r["quality"]
        m = r["metrics"]
        t = r["tokens"]
        meta_skills.append({
            "name": r["name"],
            "score": q["score"],
            "body_lines": m["body_lines"],
            "tools": m["tools_count"],
            "model": m["model"],
            "declared_budget": r.get("declared_budget"),
            "invocation_cost": t["invocation_cost"],
            "version": m["version"],
            "complexity": q.get("declared_complexity", "?"),
            "has_triggers": q.get("has_triggers", False),
            "disclosure_ratio": m["disclosure_ratio"],
            "ref_files": m["ref_files"],
        })

meta_skills.sort(key=lambda x: x["score"], reverse=True)
print(json.dumps({"count": len(meta_skills), "skills": meta_skills}, indent=2))
