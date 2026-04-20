# Migration Guide — `services/comfyui-build` Submodule Initialisation

> Gilt für: phantom-ai-Klone die vor `55a27b85` (2026-04-20) gecloned wurden
> Anlass: PR #14 hat `services/comfyui-build/` als Submodule registriert. Klone ohne erneutes `git submodule update` haben den Submodule leer oder broken. (Devstral External Review Finding #5)
> Schwester-Doku: `phantom-ai/.claude/rules/24-meta-skills-sync.md` — Gesamt-Submodule-Workflow

## Wen betrifft das?

| Maschine | Braucht ComfyUI-Build Zugriff? | Aktion |
|---|---|---|
| Dev-PC (.91, .15, .210 wenn reachable) | Ja (occasional) | **Vollmigration** (Abschnitt 1) |
| CI-Runner (self-hosted) | Ja | **Vollmigration** + Deploy-Key (Abschnitt 3) |
| .80/.82/.83 (Server/Swarm) | Nein | **Opt-out** (Abschnitt 2) |
| .99 (Bridge-Host) | Ja für ComfyUI-Jobs | **Vollmigration** (Abschnitt 1) |
| .28/.29 (Worker ohne GPU) | Nein | **Opt-out** (Abschnitt 2) |

## Symptom-Check: bin ich betroffen?

```bash
cd ~/phantom-ai
git submodule status
```

| Output | Bedeutung | Nächste Schritte |
|---|---|---|
| `<SHA> services/comfyui-build (heads/main)` | Submodule ist initialisiert ✓ | Nichts zu tun |
| `-<SHA> services/comfyui-build` | Submodule ist registriert, aber nicht populiert | Abschnitt 1 (Vollmigration) |
| `U<SHA> services/comfyui-build` | Merge-Konflikt im Submodule | Abschnitt 4 (Konflikt-Recovery) |
| (nicht aufgeführt) | `.gitmodules` ist vor `55a27b85` | Abschnitt 1 |

## Abschnitt 1: Vollmigration (Standard-Path)

### 1.1 Pre-Check
```bash
cd ~/phantom-ai

# Aktualisiere den Main-Pointer zuerst
git pull --ff-only                # erwartet: bis mind. 55a27b85

# Lokale Änderungen sichern (falls was uncommitted ist)
if ! git diff --quiet HEAD; then
    git stash push -u -m "pre-comfyui-migration $(date +%Y%m%d_%H%M)"
fi
```

### 1.2 Auth-Setup (einmalig pro Maschine, falls noch nicht gemacht)

`comfyui-build` ist ein **privates** Repo. Lies access braucht eine der beiden Varianten aus Rule 24:

**Option A: SSH-Key** (empfohlen für Dev-Maschinen mit Persistenz)
```bash
# Vorhandenen Key prüfen
ssh -T git@github.com    # erwartet: "Hi <username>!"

# Falls kein Key: neuen generieren
ssh-keygen -t ed25519 -C "phantom-ai-$(hostname)" -f ~/.ssh/github_phantom
cat ~/.ssh/github_phantom.pub
# → Füge den Public Key hinzu: github.com/settings/keys
```

**Option B: PAT (für ephemeren CI-Runner):** siehe Rule 24 Abschnitt "Auth-Voraussetzung"

### 1.3 Submodule sync + init

```bash
# Die wichtige Kombo:
git submodule sync                                    # refresht .git/config aus .gitmodules
git submodule update --init --recursive services/comfyui-build

# Verify:
git submodule status services/comfyui-build
# erwartet: "<SHA> services/comfyui-build (heads/main)" — OHNE "-" Prefix
ls services/comfyui-build/                            # muss Dateien zeigen (Dockerfile, docker-stack.yml, etc.)
```

### 1.4 Pop stash falls 1.1 eine gemacht hat
```bash
git stash list | head -1
git stash pop                     # falls die pre-comfyui-migration drin ist
```

## Abschnitt 2: Opt-out (Maschinen ohne ComfyUI-Bedarf)

Wenn die Maschine ComfyUI-Build NIE braucht (z.B. Swarm-Server, Monitoring-Worker):

```bash
cd ~/phantom-ai

# Einmalig in lokaler .git/config:
git config submodule.services/comfyui-build.update none

# Verify:
git config --get submodule.services/comfyui-build.update
# → "none"
```

Danach ignoriert `git submodule update` den Submodule komplett. `git pull --ff-only` funktioniert weiter normal, der Pointer wird gefetched aber nicht populiert.

**Zurücknehmen** (falls sich der Bedarf ändert):
```bash
git config --unset submodule.services/comfyui-build.update
# Dann Abschnitt 1.3 ausführen
```

## Abschnitt 3: CI-Runner (self-hosted oder GitHub-hosted)

CI hat kein persistentes SSH/PAT. Zwei Varianten:

### 3.1 plugins-ci.yml (aktueller Stand)
CI initialisiert **nur** `meta-skills`, skippt `comfyui-build` bewusst. Plugin-Scan braucht comfyui-build nicht.

Wenn ein Workflow doch `comfyui-build` Content braucht:

### 3.2 Deploy-Key pro Repo
```yaml
# .github/workflows/<workflow>.yml
steps:
  - uses: actions/checkout@v4
    with:
      submodules: recursive
      ssh-key: ${{ secrets.COMFYUI_BUILD_DEPLOY_KEY }}   # read-only deploy key
```

Deploy-Key-Setup siehe `phantom-ai/.claude/rules/24-meta-skills-sync.md` Abschnitt "Deploy-Keys für CI/Server-Maschinen".

## Abschnitt 4: Konflikt-Recovery

Falls `git submodule status` `U` (unmerged) zeigt:

```bash
cd ~/phantom-ai
cd services/comfyui-build
git status                        # siehst du was konfliktet ist
git log --oneline -3              # welche SHAs sind involved
```

Drei Optionen:

| Wenn | Dann |
|---|---|
| Du hast lokale Änderungen im Submodule, willst sie behalten | `cd services/comfyui-build && git commit && git push` (push zum comfyui-build Remote) + `cd .. && git add services/comfyui-build && git commit` |
| Lokale Änderungen egal | `cd services/comfyui-build && git reset --hard origin/main` (Achtung: S1 — lokale Arbeit wird zerstört, vorher Backup) |
| Zweifel | STOPP. `git submodule show services/comfyui-build` ansehen, Joe fragen |

## Abschnitt 5: Verify End-to-End

Nach der Migration, Sanity-Check:

```bash
cd ~/phantom-ai
git status                                 # saubere working tree (keine M services/comfyui-build)
git submodule status                       # zeigt beide Submodule mit SHA, ohne '-' prefix
ls meta-skills/ services/comfyui-build/   # beide haben Content
```

Danach kannst du normal weiterarbeiten.

## Abschnitt 6: FAQ

**Q: Ich habe `git pull` gemacht und jetzt ist `services/comfyui-build` verschwunden.**
A: Nicht verschwunden — nur nicht populiert. `git submodule update --init services/comfyui-build`.

**Q: `git submodule update` sagt "Repository not found".**
A: Auth fehlt. Abschnitt 1.2. Teste mit `ssh -T git@github.com` oder `gh api repos/AI-Engineering-at/comfyui-build`.

**Q: Kann ich auf einer Maschine ohne GitHub-Access arbeiten?**
A: Ja, mit Opt-out (Abschnitt 2). Nur nicht für Work der comfyui-build Content braucht.

**Q: Wie kommt der Submodule-Pointer auf einen neuen SHA?**
A: Jemand committet im comfyui-build Repo + pushed, dann jemand im phantom-ai Repo macht `cd services/comfyui-build && git pull && cd .. && git add services/comfyui-build && git commit`. Siehe Rule 24 Abschnitt "Submodule-Pointer bumpen".

## Verwandt

- `phantom-ai/.claude/rules/24-meta-skills-sync.md` — Gesamt-Workflow
- `phantom-ai/.gitmodules` — aktuelle Submodule-Registrierung
- PR #14 (`55a27b85` + Vorgänger) — Einführung von comfyui-build als Submodule
- `meta-skills/self-improving/corrections.md.example` C-CLAIM02 — vorherige Submodule-Migration-Pain (meta-skills)

---

*Erstellt: 2026-04-20 · Opus 4.7 · 1M context · Session 2026-04-20 Track B · ERPNext TASK-2026-00650*
