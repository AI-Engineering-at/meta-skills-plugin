# CI Gates Proposal (2026-04-17)

Adds two jobs to `phantom-ai/.github/workflows/plugins-ci.yml`:

- **Job 6 `format-tests`** — runs `pytest tests/test_statusline_formatters.py`.
  Gates against regressions of the `$1000k` boundary bug and any future
  formatter edge-case.
- **Job 7 `hardening-evidence`** — runs `scripts/hardening-run.py --ci`,
  uploads `oversight/hardening-*/` as CI artifact with 30-day retention.
  Fails the build on CRITICAL findings.

## Why the change isn't applied directly

The CI workflow lives in the `phantom-ai` repo, which is currently on a
VRAM-guard feature branch. Landing CI changes there needs its own PR flow
and Joe's approval. The patch is staged here for review.

## How to apply

From the `phantom-ai` repo root:

```bash
# On a clean branch of phantom-ai main
git checkout main && git pull
git checkout -b chore/plugins-ci-format-tests-and-evidence
git apply meta-skills/oversight/ci-gates-proposal.patch
git add .github/workflows/plugins-ci.yml
git commit -m "ci(plugins): add format-tests + hardening-evidence gates"
git push -u origin chore/plugins-ci-format-tests-and-evidence
# Open PR → main
```

## Verification after landing

- `format-tests` must run on PRs touching `meta-skills/**`
- `hardening-evidence` artifact `hardening-evidence-<run_id>` must appear
  in the Actions run summary
- Break the boundary intentionally (`fcost(999_999.99)` returning `$1000k`)
  and confirm `format-tests` fails the PR

## Rollback

```bash
git revert <commit-sha>
```

No state outside CI config is affected. No runtime impact on the plugin.
