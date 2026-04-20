# CI Actions Runner Investigation — 2026-04-20

> Autor: Opus 4.7 · 1M context (Session 2026-04-20 Track F)
> Scope: GitHub Actions Runner-Availability für `AI-Engineering-at` Org
> Anlass: Recent PR-CI-Runs failing in 3-4 Sekunden ohne job-logs (C-Actions-Quota wurde hypothetisch genannt, Verifikation nötig)
> Auth: `shared/github.com/GITHUB_PAT` (FoxLabs-ai user, scopes incl. `admin:enterprise, admin:org, workflow`)

## TL;DR

Nicht Quota. **Keine Runners für die Org verfügbar.**

- Organization `AI-Engineering-at` hat **0 selbst-gehostete runners** (`total_count: 0`)
- GitHub-hosted runners sind **nicht unterstützt** für diese Org: API antwortet `404 "GitHub hosted runners are not supported for this organization"`
- Runner-group "Default" existiert aber ist leer
- Actions-Config ist offen: `enabled_repositories: all, allowed_actions: all` — kein Config-Blocker
- 3-4s Fail-Pattern = Runs werden submitted → kein Runner picked up → GitHub marks failed nach kurzem Timeout

PRs #12, #14, #17 wurden manuell durch `LEEI1337` gemerged obwohl CI scheiterte (admin override).

## Evidenz (live-befragt 2026-04-20)

```bash
# 1. Hosted Runners gemäß Enterprise-Runner-API
curl -H "Authorization: token $PAT" \
    https://api.github.com/orgs/AI-Engineering-at/actions/hosted-runners
# → {"message": "GitHub hosted runners are not supported for this organization", "status": "404"}

# 2. Self-hosted Runners
curl -H "Authorization: token $PAT" \
    https://api.github.com/orgs/AI-Engineering-at/actions/runners
# → {"total_count": 0, "runners": []}

# 3. Runner-groups
curl -H "Authorization: token $PAT" \
    https://api.github.com/orgs/AI-Engineering-at/actions/runner-groups
# → {"total_count": 1, "runner_groups": [{"name": "Default", ...}]} (empty default group)

# 4. Actions permissions
curl -H "Authorization: token $PAT" \
    https://api.github.com/orgs/AI-Engineering-at/actions/permissions
# → {"enabled_repositories": "all", "allowed_actions": "all", ...}

# 5. Recent run (24670989069, docs(rule-24) commit)
curl -H "Authorization: token $PAT" \
    https://api.github.com/repos/AI-Engineering-at/phantom-ai/actions/runs/24670989069
# → status: completed, conclusion: failure, created: 14:04:37, updated: 14:04:41 (4s)

# 6. Run logs
gh run view 24670989069 --log-failed --repo AI-Engineering-at/phantom-ai
# → "log not found: 72141412443" (keine Job-Logs weil kein Job lief)
```

## Warum PRs trotzdem gemerged werden konnten

PR #12, #14, #17 alle state "MERGED". GitHub erlaubt merge-mit-failing-CI wenn:
- Branch-Protection-Rules die failing Checks nicht blockieren ODER
- Admin-Override durch User mit `admin`-Berechtigung auf Repo

`LEEI1337` ist triggering_actor der Merges — als Org-Admin hat dieser User bypass-Rechte. Das ist **kein Lösungspfad**, nur Beobachtung.

## Warum das wichtig ist

- Alle künftigen PRs müssen per Admin-Override gemerged werden → Single-Point-of-Failure auf Joe
- Kein CI = kein Hardening-Gate = kein Secret-Scan = kein pytest = kein ruff-Blocker vor main
- Externe Contributors (falls je) hätten keinen Pfad, PRs zu mergen
- Die CI-Dateien (`plugins-ci.yml`, `ci.yml`, `docs-ci.yml`, `dashboard-ci.yml`) sind quasi tot

## Zwei Fix-Pfade

### Option I-1: Self-hosted Runner registrieren

**Setup-Maschine:** .99 (reachable laut ping, SSH-auth in vault) oder .82 (Linux, root)

**Steps:**
```bash
# 1. Runner-Token holen (expires 1h):
curl -X POST -H "Authorization: token $PAT" \
    https://api.github.com/orgs/AI-Engineering-at/actions/runners/registration-token
# → {"token": "XXX", "expires_at": "..."}

# 2. Auf .99 SSH:
ssh joe@10.40.10.99  # pw im vault, shared/ssh oder joe/ssh
mkdir ~/actions-runner && cd ~/actions-runner
curl -o actions-runner-linux-x64-2.319.1.tar.gz \
    -L https://github.com/actions/runner/releases/download/v2.319.1/actions-runner-linux-x64-2.319.1.tar.gz
tar xzf actions-runner-linux-x64-2.319.1.tar.gz

# 3. Konfigurieren (Token aus Step 1):
./config.sh --url https://github.com/AI-Engineering-at \
    --token <TOKEN-FROM-STEP-1> \
    --name phantom-ai-runner-99 \
    --labels self-hosted,linux,x64,.99 \
    --runnergroup Default \
    --unattended

# 4. Als systemd-Service starten (dauerhaft):
sudo ./svc.sh install joe
sudo ./svc.sh start

# 5. Verify:
curl -H "Authorization: token $PAT" \
    https://api.github.com/orgs/AI-Engineering-at/actions/runners
# Sollte 1 Runner listen
```

**Workflow-Seite:** Workflows müssen `runs-on: self-hosted` oder `runs-on: [self-hosted, linux]` verwenden. Aktuelle Workflows haben wahrscheinlich `runs-on: ubuntu-latest` → müssen zu `self-hosted` umgestellt werden.

**Cost:** Strom auf .99 + Maintenance.
**Risk:** Self-hosted runner = Code aus PRs läuft auf eurer Infra. Braucht Security-Hygiene (ephemeral runner, isolierter User, keine Secrets in env).

### Option I-2: Org-Plan upgraden

**Setup:** Joe → `github.com/organizations/AI-Engineering-at/billing/plan_summary` → Upgrade auf "Team" ($4/user/month) oder "Enterprise".

Team-Plan bietet 3,000 minutes/month Actions-hosted-runners. Für aktuellen Commit-Rhythmus (geschätzt 30-50 Runs/month × 5min = 250min) reichlich.

**Cost:** $4/user/month × Anzahl Org-Members.
**Risk:** Low — GitHub-native.
**Setup-Time:** 2 min Clicks.

### Option I-3: Actions komplett abschalten (nicht empfohlen)

Workflows deaktivieren, ruff/pytest nur lokal laufen. Kein CI-Gate mehr. Löst das runner-Problem trivial, aber verliert alle CI-Benefits.

## Empfehlung

**I-2 (Plan-Upgrade)** ist die pragmatische Wahl:
- Sofortiger Fix via UI-Click
- Kein Security-Overhead von self-hosted
- Keine Workflow-Änderungen nötig (alle `ubuntu-latest` bleibt)
- $4/user/month ist vernachlässigbar gegen Deliverable-Geschwindigkeit

**I-1 (self-hosted)** macht Sinn wenn:
- Private Repos mit großen Build-Minuten (Docker-Builds für voice-gateway, ops-dashboard)
- Hohe Run-Frequenz (10+ Runs/Tag)
- Security-isolierte Umgebung möglich (dedicated VM, ephemeral runner, keine Secrets im env)

Der Break-Even wäre grob: self-hosted lohnt wenn monatliche hosted-minutes > ~750 (3× free tier).

## Verwandt

- `meta-skills/plans/HANDOVER-2026-04-19.md` §5 — C-Actions-Quota als "extern blocker" erwähnt
- `meta-skills/self-improving/corrections.md.example` — C-STATUSLINE01, C-MULTI-TERMINAL, C-CURL-MULTIPART-WIN (Session 2026-04-18 learnings)
- ERPNext TASK-2026-00650 (Completed) — referenced all prior commits
- Aktueller vault key: `shared/github.com/GITHUB_PAT` (FoxLabs-ai user, admin:enterprise+admin:org scopes) — einziger Weg der aktuell org-admin API Calls macht

---

*Erstellt: 2026-04-20 Opus 4.7 · 1M context · Session 2026-04-20 Track F Playwright initial attempt (login-redirect) → gh API deep-dive mit vault PAT*
