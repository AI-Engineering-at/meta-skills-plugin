#!/usr/bin/env python3
"""Check if a planned skill overlaps with existing skills.

Usage: python check-duplicates.py "deploy voice gateway to production"
Output: JSON with similar skills (name, similarity score)

Method: TF-IDF on description fields of all local SKILL.md files.
No LLM, no embedding API. Pure text matching.
"""

import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

SCHEMA_VERSION = 1


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
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta


def tokenize(text: str) -> list[str]:
    """Simple word tokenizer."""
    return re.findall(r"[a-z0-9]+", text.lower())


def tfidf_similarity(query_tokens: list[str], doc_tokens: list[str], idf: dict[str, float]) -> float:
    """Cosine similarity using TF-IDF."""
    if not query_tokens or not doc_tokens:
        return 0.0
    q_tf = Counter(query_tokens)
    d_tf = Counter(doc_tokens)
    q_vec = {t: q_tf[t] * idf.get(t, 0) for t in q_tf}
    d_vec = {t: d_tf[t] * idf.get(t, 0) for t in d_tf}
    common = set(q_vec) & set(d_vec)
    if not common:
        return 0.0
    dot = sum(q_vec[t] * d_vec[t] for t in common)
    q_norm = math.sqrt(sum(v ** 2 for v in q_vec.values()))
    d_norm = math.sqrt(sum(v ** 2 for v in d_vec.values()))
    if q_norm == 0 or d_norm == 0:
        return 0.0
    return dot / (q_norm * d_norm)


def find_skills() -> tuple[list[dict], int]:
    """Find all SKILL.md files in local and plugin directories."""
    skills = []
    skipped = 0
    search_paths = [
        Path.home() / ".claude" / "skills",
        Path.home() / ".claude" / "plugins" / "cache",
    ]
    cwd = Path.cwd()
    local_skills = cwd / ".claude" / "skills"
    if local_skills.exists():
        search_paths.insert(0, local_skills)

    for base in search_paths:
        if not base.exists():
            continue
        for skill_md in base.rglob("SKILL.md"):
            try:
                meta = extract_frontmatter(skill_md)
                if meta.get("name"):
                    desc = meta.get("description", "")
                    skills.append({
                        "name": meta["name"],
                        "description": desc,
                        "path": str(skill_md),
                        "tokens": tokenize(f"{meta['name']} {desc}"),
                    })
            except Exception:
                skipped += 1
    return skills, skipped


def main():
    try:
        if len(sys.argv) < 2:
            print(json.dumps({"error": "Usage: check-duplicates.py 'skill description'", "schema_version": SCHEMA_VERSION}))
            sys.exit(1)

        query = sys.argv[1]
        query_tokens = tokenize(query)
        skills, skipped = find_skills()

        if not skills:
            print(json.dumps({"matches": [], "total_skills": 0, "skipped_files": skipped, "schema_version": SCHEMA_VERSION}))
            return

        n = len(skills) + 1
        all_tokens = set()
        for s in skills:
            all_tokens.update(set(s["tokens"]))
        all_tokens.update(set(query_tokens))

        idf = {}
        for token in all_tokens:
            df = sum(1 for s in skills if token in set(s["tokens"]))
            if token in set(query_tokens):
                df += 1
            idf[token] = math.log(n / max(df, 1))

        results = []
        for s in skills:
            score = tfidf_similarity(query_tokens, s["tokens"], idf)
            if score > 0.05:
                results.append({
                    "name": s["name"],
                    "score": round(score, 3),
                    "description": s["description"][:120],
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        print(json.dumps({
            "query": query,
            "matches": results[:5],
            "total_skills": len(skills),
            "skipped_files": skipped,
            "schema_version": SCHEMA_VERSION,
        }, indent=2))
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "error_type": type(e).__name__,
            "script": os.path.basename(__file__),
            "schema_version": SCHEMA_VERSION,
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
