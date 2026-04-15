# SCAN Checks — Hardening Step 1

All deterministic checks (0 LLM cost):

## 1a. Python Syntax
```bash
cd meta-skills && for f in hooks/*.py scripts/*.py; do
  python3 -m py_compile "$f" 2>&1 || echo "FAIL: $f"
done
```

## 1b. JSON Schema
```bash
python3 -c "import json; json.load(open('hooks/hooks.json'))"
python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"
```

## 1c. Skill Quality Scores
```bash
python3 scripts/eval.py --all 2>&1
```

## 1d. Frontmatter Validation
```bash
python3 scripts/validate.py 2>&1
```

## 1e. Lint
```bash
ruff check hooks/ scripts/ 2>&1 || true
```

## 1f. Reworker Diagnostics
```bash
python3 scripts/reworker.py --diagnose --top 10 2>&1
```

## 1g. Correction Promotion Candidates
```bash
python3 scripts/promote-corrections.py 2>&1
```

## 1h. Skill Registry
```bash
python3 scripts/build-skill-registry.py --check 2>&1
```

## 1i. harness-verify (if available)
```bash
cd ../../harness-verify && python3 harness.py --json 2>/dev/null || true
```
