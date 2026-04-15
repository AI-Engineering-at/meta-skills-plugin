# meta-skills v4.0 — Autoreason Upgrade Projektdokument

> Erstellt: 2026-04-13 | Autor: Projekt-Architekt (Opus)
> Basis: 3 parallele Research-Agenten + lokaler Code-Audit
> Status: PLAN (noch nicht gestartet)

---

## 1. Executive Summary

### 1.1 Was wir haben (v3.0 Baseline)

| Dimension | Bestand |
|-----------|---------|
| Skills | 15 (creator, design, dispatch, doc-updater, feedback, git-worktrees, init, judgment-day, knowledge, refactor-loop, statusbar, systematic-debugging, tdd, verify) |
| Commands | 12 Slash-Commands (`/meta-*`) |
| Hooks | 9 (session-init, correction-detect, scope-tracker, approach-guard, exploration-first, token-audit, quality-gate, meta-loop-stop, session-stop) |
| Agents | 6 (doc-auditor, doc-editor, 3x doc-scanner, session-analyst) |
| Scripts | 24 deterministische Python-Scripts (eval, validate, reworker, autoreason, etc.) |
| Autoreason | `autoreason-skills.py` mit 3 CLI-Agents (kimi, opencode, claude) + Devstral API |
| Quality | judgment-day (2 blinde Judges), quality-gate Hook, meta-loop, refactor-loop |

### 1.2 Was wir bauen (v4.0 Vision)

**Cross-Model Autoreason Engine** mit:
- CLI-Orchestrierung als First-Class-Feature (kimi, opencode, claude gleichberechtigt)
- Integration-Test-Harness pro Skill (nicht nur Score, sondern Funktionstest)
- Usage-Tracking + Cost-Attribution (wer benutzt was, was kostet es)
- Governance Dashboard (Stale-Detection, Dependency-Impact, Health-Overview)
- AgentCraft-Pattern-Integration (Event-Bus, Session-Management, File-Conflict-Detection)

### 1.3 Warum (Research-basierte Begruendung)

| Luecke | Beleg | Impact |
|--------|-------|--------|
| Keine Integration-Tests | Finding 3.1 — eval.py scored, testet aber nicht ob Skill FUNKTIONIERT | Skills koennen 80/100 scoren aber bei Aufruf crashen |
| Kein Usage-Tracking | Finding 3.2 — unbekannt welche Skills benutzt werden | Tote Skills bleiben, wertvolle Skills werden nicht optimiert |
| Keine Dependency-Impact-Analyse | Finding 3.3 — keine Breaking-Change Prevention | Hook-Aenderung kann 5 Skills brechen ohne Warnung |
| Kein Skill-Registry Feed | Finding 3.4 — externe Discovery unmoeglich | Kein Ecosystem-Wachstum, keine Community-Nutzung |
| Kein Governance Dashboard | Finding 3.5 — keine Gesundheitsuebersicht | 50+ Skills ohne zentrale Ueberwachung |
| Autoreason ist einzigartig | Finding 4 — kein anderes Tool hat 3 CLIs als Judges + Revision Loop | Wettbewerbsvorteil ausbauen statt aufgeben |

---

## 2. Architektur-Vergleich

### 2.1 Feature-Matrix: Wir vs Wettbewerb

| Feature | meta-skills v3 | Agent Council | sd0x-dev-flow | ralph-loop | ClosedLoop | **meta-skills v4** |
|---------|:-:|:-:|:-:|:-:|:-:|:-:|
| **Multi-CLI Orchestrierung** | Ja (autoreason) | Ja (Panel) | Nein | Nein | Nein | **Ja (erweitert)** |
| **Cross-Model Judges** | Ja (3 CLIs) | Ja (deliberation) | Nein | Nein | Ja (LLM-as-judge) | **Ja (Borda + Rotation)** |
| **Adversarial Revision Loop** | Ja (Critic->B->Synth) | Nein | Ja (dual review) | Nein | Ja (self-learning) | **Ja (verbessert)** |
| **Hook-enforced Quality Gates** | Ja (9 Hooks) | Nein | Ja (sentinel-driven) | Ja (4-stage blocking) | Nein | **Ja (14 Event-Types)** |
| **Session Management** | Basis (session-init/stop) | Nein | Nein | Nein | Nein | **Ja (AgentCraft-Pattern)** |
| **File-Conflict-Detection** | Nein | Nein | Nein | Nein | Nein | **Ja (Multi-Agent-safe)** |
| **Integration Tests** | Nein | Nein | Nein | Nein | Nein | **Ja (Test-Harness)** |
| **Usage Tracking** | Nein | Nein | Nein | Nein | Nein | **Ja (JSONL + Dashboard)** |
| **Dependency-Impact** | Nein | Nein | Nein | Nein | Nein | **Ja (DAG-basiert)** |
| **Governance Dashboard** | Nein | Nein | Nein | Nein | Nein | **Ja (Health-Overview)** |
| **Skill Count** | 15 | ~5 | 90 | ~10 | ~8 | **15+ (qualitaetsgesichert)** |
| **Memory Layers** | 2 (self-improving) | 0 | 0 | 4 | 1 | **3 (self-improving + usage + cost)** |
| **Cost Attribution** | Nein | Nein | Nein | Nein | Nein | **Ja (per-Skill)** |
| **Convergence Detection** | Ja (k=2) | Nein | Nein | Nein | Nein | **Ja (k=2 + Score-Delta)** |

### 2.2 Wo Wettbewerber besser sind (ehrlich)

| Wettbewerber | Staerke | Unser Gap | v4 Adressiert? |
|-------------|---------|-----------|:-:|
| sd0x-dev-flow | 90 Skills — riesiges Skill-Repertoire | 15 Skills | Nein (Qualitaet > Quantitaet) |
| ralph-loop | 4-Layer Memory mit Langzeit-Kontext | 2-Layer Memory | Teilweise (3-Layer) |
| CCManager | 8+ CLI Session Management | Kein Session-Manager | Ja (Phase 8) |
| Maestro | Cross-Runtime Orchestrierung (Gemini+Claude+Codex) | Nur 4 CLIs | Ja (Phase 2, erweiterbar) |
| ClosedLoop | Self-Learning mit Feedback-Integration | Manuelles Learning | Teilweise (Usage-basiert) |

### 2.3 Wo wir EINZIGARTIG sind (Finding 4)

| Differentiator | Details |
|----------------|---------|
| **3 verschiedene CLIs als Judges** | Nicht generisch "any model" — kimi + devstral + claude spezifisch konfiguriert |
| **Autoreason + Revision Loop** | Judges + Revision + Synthese + erneutes Judging, nicht nur Review |
| **Skill-Verbesserung als Ziel** | Meta-Level: verbessert die Tools die Code verbessern |
| **Kein Runtime Lock-In** | Jedes CLI gleichberechtigt, API als Fallback |
| **Adversarial by Design** | Disagreement ist Feature, nicht Bug — Borda-Count faerbt Dissens fair ein |
| **Deterministic Scripts** | eval.py, validate.py, reworker.py verbrauchen 0 LLM-Tokens |

---

## 3. Feature-Matrix v4.0

### A: CLI-Orchestrierung

| ID | Feature | Beschreibung | Prioritaet |
|----|---------|-------------|:-:|
| A1 | CLI Registry | Zentrale Config aller CLI-Agents (kimi, opencode, claude, devstral) mit Capabilities, Flags, Timeouts | P0 |
| A2 | CLI Health-Check | `detect_available_clis()` erweitert um Version-Detection, Model-Info, GPU/CPU-Status | P0 |
| A3 | CLI Fallback-Chain | Wenn kimi nicht verfuegbar → naechstes CLI in Chain. Konfigurierbar per Rolle | P1 |
| A4 | CLI Cost-Tracking | Token-Verbrauch und geschaetzte Kosten pro CLI-Call loggen (JSONL) | P1 |
| A5 | CLI Timeout-Tuning | Adaptive Timeouts basierend auf historischer Response-Time pro CLI | P2 |
| A6 | CLI Output-Normalisierung | Verschiedene CLIs geben verschiedene Formate — Normalizer fuer konsistente Verarbeitung | P1 |

### B: Autoreason Engine

| ID | Feature | Beschreibung | Prioritaet |
|----|---------|-------------|:-:|
| B1 | Critic v2 | Erweiterte Critic-Prompts mit Skill-spezifischen Checklisten (Frontmatter, Body, Triggers) | P0 |
| B2 | Author B v2 | Structured-Output: JSON mit `{problem_id, change, rationale}` pro Aenderung | P1 |
| B3 | Synthesizer v2 | Sektion-weise Merge statt Ganz-Dokument-Synthese (praeziser) | P1 |
| B4 | Judge Rotation | Rotierendes Judge-Assignment ueber Passes hinweg (verhindert Judge-Bias) | P0 |
| B5 | Score-Delta-Gate | Autoreason stoppt wenn Score-Delta < 3 Punkte ueber 2 Passes (Score-Plateau) | P1 |
| B6 | Batch-Autoreason | `--batch N` Flag: N Skills parallel verarbeiten (multiprocessing) | P2 |
| B7 | Autoreason History | Historische Score-Verlaeufe pro Skill (Regression-Detection) | P1 |

### C: Quality Gates

| ID | Feature | Beschreibung | Prioritaet |
|----|---------|-------------|:-:|
| C1 | Pre-Publish Gate | `validate.py` + `eval.py` + Integration-Test muessen bestehen vor Skill-Publish | P0 |
| C2 | Integration-Test-Harness | Pro-Skill Funktionstest: Skill aufrufen, Output pruefen, kein Crash | P0 |
| C3 | Dependency-Check | DAG aller Skill-Abhaengigkeiten — warnt bei Breaking Changes | P1 |
| C4 | Regression-Test-Suite | Nach jedem Autoreason-Run: alle Skills re-evaluieren | P1 |
| C5 | Hook-Validation | Automatischer Test aller 9 Hooks: korrektes stdin-Parsing, kein Timeout, kein Crash | P1 |
| C6 | CI/CD-Integration | GitHub Actions Workflow: `validate.py --all` + `eval.py --all` bei jedem PR | P2 |

### D: Governance Dashboard

| ID | Feature | Beschreibung | Prioritaet |
|----|---------|-------------|:-:|
| D1 | Usage-Tracking | JSONL-Log jeder Skill-Invocation (wer, wann, wie lange, Ergebnis) | P0 |
| D2 | Cost-Attribution | Kosten pro Skill pro Tag (Token-Verbrauch * Model-Preis) | P1 |
| D3 | Stale-Detection | Skills mit `last-verified > 30d` oder `last-used > 60d` automatisch flaggen | P0 |
| D4 | Health-Score | Aggregierter Gesundheitswert pro Skill: eval-score + usage + age + test-status | P1 |
| D5 | Governance-Report | Woechentlicher automatischer Report: Top-Skills, Stale-Skills, Kosten, Score-Trends | P2 |
| D6 | Skill-Registry JSON Feed | Maschinenlesbarer Feed aller Skills (Name, Version, Status, Score, Last-Used) | P1 |

### E: AgentCraft-Pattern Integration

| ID | Feature | Beschreibung | Prioritaet |
|----|---------|-------------|:-:|
| E1 | Event-Bus | Lokaler HTTP-Endpoint fuer Hook-Events (Fire-and-Forget, inspiriert von Port 2468) | P2 |
| E2 | Session-State-Machine | SessionStart → Active → Idle → Stop mit State-Transitions und Cleanup | P1 |
| E3 | File-Conflict-Detection | Multi-Agent-Lock: bevor Write/Edit → pruefen ob anderer Agent gleiche Datei bearbeitet | P1 |
| E4 | SubagentStop-Handler | Neuer Hook: nach Sub-Agent-Ende automatisch Ergebnis in Parent-Context injizieren | P2 |
| E5 | Hook-Event-Erweiterung | Neue Events: `PreToolUse/Task`, `SubagentStop`, `PermissionRequest` (AgentCraft-kompatibel) | P2 |
| E6 | WebSocket-Bridge | Optionale bidirektionale Kommunikation fuer Real-Time Monitoring | P3 |

---

## 4. Implementierungsplan (10 Phasen)

### Phase 1: CLI Registry + Health-Check (Foundation)

| Aspekt | Detail |
|--------|--------|
| **Was wird gebaut** | Zentrale CLI-Agent-Konfiguration als JSON/YAML. Health-Check Erweiterung mit Version-Detection. CLI Output-Normalisierung |
| **Files** | `scripts/cli-registry.json` (NEU), `scripts/cli-health.py` (NEU), `scripts/autoreason-skills.py` (EDIT: CLI_AGENTS aus Registry laden) |
| **Abhaengigkeiten** | Keine — Standalone |
| **Aufwand** | **S** (1-2 Sessions) |
| **Verifikation** | `python3 scripts/cli-health.py` zeigt verfuegbare CLIs mit Version + Status. Autoreason laeuft weiterhin mit bestehenden CLIs |

### Phase 2: Autoreason Engine v2 (Core Upgrade)

| Aspekt | Detail |
|--------|--------|
| **Was wird gebaut** | Erweiterte Critic-Prompts, Structured-Output Author B, Sektion-weiser Synthesizer, Score-Delta-Gate, Judge-Rotation ueber Passes |
| **Files** | `scripts/autoreason-skills.py` (MAJOR EDIT), `scripts/autoreason-prompts.py` (NEU: Prompt-Templates ausgelagert), `oversight/autoreason/history/` (NEU: Score-Verlaeufe) |
| **Abhaengigkeiten** | Phase 1 (CLI Registry) |
| **Aufwand** | **L** (3-5 Sessions) |
| **Verifikation** | `python3 autoreason-skills.py skills/verify/SKILL.md --max-passes 3` — Score-Verlauf plausibel, Judge-Rotation sichtbar in Logs, Structured-Output Author B parsebar |

### Phase 3: Integration-Test-Harness (Test Infrastructure)

| Aspekt | Detail |
|--------|--------|
| **Was wird gebaut** | Pro-Skill Test-Datei in `skills/{name}/test.py`. Test-Runner `scripts/test-skills.py`. Jeder Test: Skill laden, simulierten Input geben, Output auf Plausibilitaet pruefen |
| **Files** | `scripts/test-skills.py` (NEU), `skills/*/test.py` (NEU: pro Skill), `scripts/test-hooks.py` (NEU: Hook-Validierung) |
| **Abhaengigkeiten** | Keine — parallel zu Phase 2 moeglich |
| **Aufwand** | **L** (3-5 Sessions, 15 Skills + 9 Hooks) |
| **Verifikation** | `python3 scripts/test-skills.py --all` — alle Skills gruuen, alle Hooks gruuen. `python3 scripts/test-hooks.py` — kein Timeout, korrektes stdin-Parsing |

### Phase 4: Usage-Tracking + Cost-Attribution (Governance Foundation)

| Aspekt | Detail |
|--------|--------|
| **Was wird gebaut** | JSONL-Logger in `token-audit.py` Hook erweitern: Skill-Name, Invocation-Count, Duration. Cost-Rechner basierend auf CLI-Modell-Preisen |
| **Files** | `hooks/token-audit.py` (EDIT: Skill-Detection hinzufuegen), `scripts/usage-report.py` (NEU), `oversight/usage/` (NEU: JSONL-Dateien) |
| **Abhaengigkeiten** | Keine — parallel zu Phase 2/3 moeglich |
| **Aufwand** | **M** (2-3 Sessions) |
| **Verifikation** | Eine Session lang arbeiten, dann `python3 scripts/usage-report.py` — Skill-Nutzung sichtbar mit Kosten-Schaetzung |

### Phase 5: Dependency-Impact-Analyse (Safety Net)

| Aspekt | Detail |
|--------|--------|
| **Was wird gebaut** | DAG-Builder: liest alle SKILL.md Frontmatter + Hook-Referenzen + Agent-Referenzen. Baut Abhaengigkeits-Graph. Impact-Checker: "Wenn ich X aendere, was bricht?" |
| **Files** | `scripts/dependency-graph.py` (NEU), `oversight/dependency-dag.json` (NEU: generierter Graph), `scripts/impact-check.py` (NEU: CLI fuer "was bricht wenn ich X aendere") |
| **Abhaengigkeiten** | Phase 3 (Integration-Tests bestaetigen echte Abhaengigkeiten) |
| **Aufwand** | **M** (2-3 Sessions) |
| **Verifikation** | `python3 scripts/impact-check.py hooks/quality-gate.py` — zeigt welche Skills/Commands betroffen sind. Graph visualisierbar als Mermaid |

### Phase 6: Pre-Publish Quality Gate (CI/CD)

| Aspekt | Detail |
|--------|--------|
| **Was wird gebaut** | Kombinierter Gate: `validate.py` + `eval.py` (Score >= 70) + Integration-Test + Dependency-Impact = alles muss bestehen. Hook in `meta-loop-stop.py` integriert |
| **Files** | `scripts/pre-publish-gate.py` (NEU: orchestriert alle Checks), `hooks/meta-loop-stop.py` (EDIT: Gate aufrufen), `.github/workflows/meta-skills-ci.yml` (NEU) |
| **Abhaengigkeiten** | Phase 3 (Integration-Tests), Phase 5 (Dependency-Check) |
| **Aufwand** | **M** (2-3 Sessions) |
| **Verifikation** | Absichtlich kaputten Skill publishen → Gate blockiert. Guten Skill publishen → Gate laesst durch. GitHub Actions laufen bei PR |

### Phase 7: Governance Dashboard + Stale-Detection

| Aspekt | Detail |
|--------|--------|
| **Was wird gebaut** | CLI-Dashboard (`/meta-status` erweitern): Health-Scores, Usage-Ranking, Stale-Alerts, Cost-Summary. Woechentlicher Report-Generator |
| **Files** | `skills/statusbar/SKILL.md` (EDIT: Governance-Sections), `scripts/governance-report.py` (NEU), `scripts/stale-detector.py` (NEU), `commands/meta-status.md` (EDIT: Dashboard-Output) |
| **Abhaengigkeiten** | Phase 4 (Usage-Tracking), Phase 5 (Dependency-Graph) |
| **Aufwand** | **M** (2-3 Sessions) |
| **Verifikation** | `/meta-status` zeigt: Top-5-Skills nach Usage, Stale-Skills (>30d), Health-Score-Distribution, Wochen-Kosten |

### Phase 8: AgentCraft Session-Management

| Aspekt | Detail |
|--------|--------|
| **Was wird gebaut** | Session-State-Machine (Start→Active→Idle→Stop). File-Conflict-Detection (Lock-File pro bearbeiteter Datei). SubagentStop-Handler |
| **Files** | `hooks/session-init.py` (EDIT: State-Machine), `hooks/session-stop.py` (EDIT: Cleanup), `hooks/lib/session-state.py` (NEU), `hooks/lib/file-lock.py` (NEU) |
| **Abhaengigkeiten** | Phase 4 (Usage-Tracking nutzt Session-State) |
| **Aufwand** | **M** (2-3 Sessions) |
| **Verifikation** | 2 parallele Claude-Sessions starten, gleiche Datei bearbeiten → File-Conflict-Warning. Session-Stop → sauberer State-Reset |

### Phase 9: Skill-Registry JSON Feed + Batch-Autoreason

| Aspekt | Detail |
|--------|--------|
| **Was wird gebaut** | Maschinenlesbarer JSON-Feed aller Skills (Name, Version, Status, Score, Last-Used, Dependencies). Batch-Autoreason mit Multiprocessing |
| **Files** | `scripts/build-skill-registry.py` (EDIT: JSON-Output), `oversight/skill-registry.json` (NEU: generierter Feed), `scripts/autoreason-skills.py` (EDIT: --batch Flag) |
| **Abhaengigkeiten** | Phase 2 (Autoreason v2), Phase 7 (Governance-Daten fuer Feed) |
| **Aufwand** | **S** (1-2 Sessions) |
| **Verifikation** | `python3 scripts/build-skill-registry.py --json > oversight/skill-registry.json` — valides JSON mit allen Skills. `python3 autoreason-skills.py --all --batch 3` — 3 Skills parallel |

### Phase 10: Hardening + Dokumentation

| Aspekt | Detail |
|--------|--------|
| **Was wird gebaut** | Error-Handling-Review aller neuen Scripts. CLAUDE.md Update (v4.0). README.md Update. Performance-Benchmarks. Cost-Baseline messen |
| **Files** | `CLAUDE.md` (EDIT: v4.0), `README.md` (EDIT: v4.0), `plans/v4-benchmarks.json` (NEU: Baseline-Messwerte), alle neuen Scripts (EDIT: Error-Handling haerten) |
| **Abhaengigkeiten** | Alle vorherigen Phasen |
| **Aufwand** | **M** (2-3 Sessions) |
| **Verifikation** | Vollstaendiger `validate.py --all` + `eval.py --all` + `test-skills.py --all` Durchlauf ohne Fehler. Benchmarks dokumentiert |

### Phasen-Uebersicht (Gantt-artig)

```
Phase 1: CLI Registry          ████                          [S] Woche 1
Phase 2: Autoreason v2         ████████████                  [L] Woche 1-3
Phase 3: Integration-Tests     ████████████                  [L] Woche 1-3 (parallel zu P2)
Phase 4: Usage-Tracking        ██████                        [M] Woche 2-3 (parallel zu P2/P3)
Phase 5: Dependency-Impact     ██████                        [M] Woche 3-4
Phase 6: Pre-Publish Gate      ██████                        [M] Woche 4-5
Phase 7: Governance Dashboard  ██████                        [M] Woche 5-6
Phase 8: AgentCraft Session    ██████                        [M] Woche 5-6 (parallel zu P7)
Phase 9: Registry Feed + Batch ████                          [S] Woche 6-7
Phase 10: Hardening + Docs     ██████                        [M] Woche 7-8
                               ─────────────────────────────
                               W1   W2   W3   W4   W5   W6   W7   W8
```

**Gesamtaufwand:** ~25-35 Sessions ueber 8 Wochen

---

## 5. CLI-Agent Konfiguration

### 5.1 Kimi (Moonshot AI)

```json
{
  "name": "kimi",
  "role": "critic",
  "headless_cmd": ["kimi", "-p", "{prompt}", "--print", "--final-message-only"],
  "version_cmd": ["kimi", "--version"],
  "timeout_seconds": 120,
  "model": "kimi-k2.5 (automatic)",
  "strengths": [
    "Starkes Reasoning (Chain-of-Thought)",
    "Gutes Erkennen von Inkonsistenzen",
    "200k Context Window"
  ],
  "weaknesses": [
    "Langsamer als Claude fuer Code-Generierung",
    "Kein System-Prompt Parameter (wird prepended)",
    "Output-Format nicht konfigurierbar"
  ],
  "flags": {
    "--print": "Print-Modus (kein interaktives UI)",
    "--final-message-only": "Nur letzte Antwort ausgeben (keine Chain-of-Thought)"
  },
  "fallback": "devstral-api",
  "cost_per_1k_input": 0.0,
  "cost_per_1k_output": 0.0,
  "notes": "Kostenlos fuer CLI-Nutzung. Rate-Limit beachten."
}
```

### 5.2 OpenCode

```json
{
  "name": "opencode",
  "role": "general",
  "headless_cmd": ["opencode", "run", "{prompt}"],
  "version_cmd": ["opencode", "--version"],
  "timeout_seconds": 120,
  "model": "configurable (via opencode config)",
  "strengths": [
    "Go-basiert, schneller Startup",
    "LSP-Integration fuer Code-Kontext",
    "Multi-Provider Support (OpenRouter, Ollama, etc.)"
  ],
  "weaknesses": [
    "Kein --print Flag (Output immer interaktiv formatiert)",
    "Output-Parsing schwieriger (ANSI-Codes)",
    "Weniger verbreitet als Claude CLI"
  ],
  "flags": {
    "run": "Non-interactive single-prompt execution"
  },
  "fallback": "claude",
  "cost_per_1k_input": "varies (provider-dependent)",
  "cost_per_1k_output": "varies (provider-dependent)",
  "notes": "Model-Selection via opencode.json Config oder OPENCODE_MODEL env."
}
```

### 5.3 Claude CLI

```json
{
  "name": "claude",
  "role": "synthesizer",
  "headless_cmd": ["claude", "-p", "{prompt}", "--output-format", "text"],
  "version_cmd": ["claude", "--version"],
  "timeout_seconds": 120,
  "model": "claude-sonnet-4-20250514 (default, configurable via --model)",
  "strengths": [
    "Beste Code-Qualitaet fuer Synthese",
    "Sauberer Text-Output mit --output-format text",
    "Zuverlaessigster Output (kein Parsing noetig)",
    "Unterstuetzt --model Flag fuer Model-Selection"
  ],
  "weaknesses": [
    "Teuerster CLI-Agent",
    "Braucht ANTHROPIC_API_KEY oder aktive Session",
    "Langsamer Startup wenn MCP-Server konfiguriert"
  ],
  "flags": {
    "-p": "Headless-Modus (pipe prompt, kein interaktives UI)",
    "--output-format text": "Plain-Text Output (kein JSON, kein Markdown-Wrapper)",
    "--model": "Model-Override (z.B. --model haiku fuer guenstigere Runs)",
    "--no-input": "Kein stdin lesen (fuer Pipe-Chains)",
    "--max-turns 1": "Single-Turn (kein Follow-Up)"
  },
  "fallback": "devstral-api",
  "cost_per_1k_input": 0.003,
  "cost_per_1k_output": 0.015,
  "notes": "Standard-Agent fuer Synthese. --model haiku fuer Budget-Runs."
}
```

### 5.4 Devstral (via OpenRouter API)

```json
{
  "name": "devstral-api",
  "role": "author_b",
  "headless_cmd": null,
  "api_url": "https://openrouter.ai/api/v1/chat/completions",
  "api_key_env": "OPENROUTER_API_KEY",
  "model_id": "mistralai/devstral-small",
  "alternative_models": [
    "mistralai/devstral-medium",
    "mistralai/codestral-latest"
  ],
  "timeout_seconds": 120,
  "strengths": [
    "Optimiert fuer Code-Revision",
    "Guenstiger als Claude fuer Code-Tasks",
    "Kein CLI-Install noetig (nur API-Key)"
  ],
  "weaknesses": [
    "Kein CLI — nur API-basiert",
    "Abhaengig von OpenRouter Verfuegbarkeit",
    "Weniger gut bei nicht-Code-Tasks (Reasoning, Analyse)"
  ],
  "api_config": {
    "max_tokens": 4096,
    "temperature": 0.3,
    "headers": {
      "HTTP-Referer": "https://ai-engineering.at",
      "X-Title": "meta-skills-autoreason"
    }
  },
  "fallback": "claude",
  "cost_per_1k_input": 0.0002,
  "cost_per_1k_output": 0.0006,
  "notes": "Primaer fuer Code-Revision (Author B Rolle). OpenRouter Fallback wenn CLI nicht verfuegbar."
}
```

### 5.5 Rollen-Zuordnung (v4.0)

| Rolle | Primaer-Agent | Fallback-Agent | Grund |
|-------|:---:|:---:|-------|
| **Critic** | kimi | devstral-api | Kimi k2.5 hat staerkstes Reasoning fuer Problemfindung |
| **Author B** | devstral-api | claude | Devstral ist auf Code-Revision optimiert, guenstiger |
| **Synthesizer** | claude | kimi | Claude hat beste Synthese-Qualitaet |
| **Judge 0** | kimi | opencode | Diversitaet: verschiedene Modelle = verschiedene Perspektiven |
| **Judge 1** | devstral-api | claude | Diversitaet: Code-fokussiert |
| **Judge 2** | claude | kimi | Diversitaet: staerkstes General-Purpose |

### 5.6 CLI-Fallback-Logik

```
Fuer jede Rolle:
  1. Primaer-Agent verfuegbar? → Benutzen
  2. Nein → Fallback-Agent verfuegbar? → Benutzen
  3. Nein → Naechster verfuegbarer Agent aus CLI_AGENTS
  4. Kein Agent verfuegbar → eval-only Modus (0 LLM Tokens)
```

---

## 6. Hook-Architektur (AgentCraft-Pattern adaptiert)

### 6.1 Bestehendes Hook-System (v3.0)

```
hooks.json (4 Event-Types)
├── UserPromptSubmit
│   ├── session-init.py      (First-Prompt: Context Loading)
│   ├── correction-detect.py (S10 Compliance)
│   └── scope-tracker.py     (Multi-Task Drift)
├── PreToolUse
│   ├── Bash → approach-guard.py   (Wrong-Approach Prevention)
│   └── Write|Edit → exploration-first.py (Read before Write)
├── PostToolUse
│   ├── * → token-audit.py   (Token-Messung)
│   └── Bash → quality-gate.py (Test/Lint Gate)
└── Stop
    ├── meta-loop-stop.py    (Objective Loop Gates)
    ├── session-stop.py      (Summary + Sync)
    └── run-hook.cmd on-stop (Async Cleanup)
```

### 6.2 AgentCraft Event-Types (Referenz)

Aus `C:/Users/Legion/Documents/AgentCraft/HOOKS-FRAMEWORK.md`:

| Event | AgentCraft Handler | Relevant fuer uns? |
|-------|-------------------|:-:|
| SessionStart | hero-spawn.js | Ja — Session-State-Machine |
| UserPromptSubmit | hero-active.js | Ja (haben wir schon) |
| PreToolUse/Bash | bash-command.js, git-guard.js | Ja (haben wir: approach-guard) |
| PreToolUse/Read | file-access.js | Nein (zu granular) |
| PreToolUse/Write | file-access.js | Ja (File-Conflict-Detection) |
| PreToolUse/Edit | file-access.js | Ja (File-Conflict-Detection) |
| PreToolUse/Task | subagent-spawn.js | Ja — Sub-Agent-Tracking |
| PostToolUse/* | — | Ja (haben wir: token-audit, quality-gate) |
| Stop | hero-idle.js | Ja (haben wir: session-stop) |
| SubagentStop | subagent-complete.js | Ja — Ergebnis-Injection |
| PermissionRequest | permission-request.js | Nein (handled by Claude Code) |

### 6.3 Neue Hook-Architektur (v4.0)

```
hooks.json (6 Event-Types, +2 neue)
├── UserPromptSubmit
│   ├── session-init.py      (ERWEITERT: State-Machine Start)
│   ├── correction-detect.py (UNVER?NDERT)
│   ├── scope-tracker.py     (UNVER?NDERT)
│   └── usage-tracker.py     (NEU: Skill-Invocation-Detection)
├── PreToolUse
│   ├── Bash → approach-guard.py   (UNVER?NDERT)
│   ├── Write|Edit → exploration-first.py (UNVER?NDERT)
│   ├── Write|Edit → file-conflict.py    (NEU: Multi-Agent File-Lock)
│   └── Task → subagent-tracker.py       (NEU: Sub-Agent-Spawn-Log)
├── PostToolUse
│   ├── * → token-audit.py   (ERWEITERT: Cost-Attribution)
│   └── Bash → quality-gate.py (UNVER?NDERT)
├── Stop
│   ├── meta-loop-stop.py    (ERWEITERT: Pre-Publish-Gate)
│   ├── session-stop.py      (ERWEITERT: State-Machine-Cleanup)
│   └── run-hook.cmd on-stop (UNVER?NDERT)
├── SubagentStop (NEU)
│   └── subagent-result.py   (NEU: Ergebnis-Logging + Parent-Notification)
└── Notification (NEU)
    └── governance-alert.py  (NEU: Stale-Detection + Health-Alerts)
```

### 6.4 Session-State-Machine

```
                    ┌─────────┐
   Session Start───►│  INIT   │
                    └────┬────┘
                         │ session-init.py
                    ┌────▼────┐
   User Prompt ───►│ ACTIVE  │◄──── User Prompt (re-activate)
                    └────┬────┘
                         │ 5min no activity
                    ┌────▼────┐
                    │  IDLE   │
                    └────┬────┘
                         │ Stop event
                    ┌────▼────┐
                    │  STOP   │──── session-stop.py (Cleanup, Sync, Report)
                    └─────────┘

State-File: ${CLAUDE_PLUGIN_ROOT}/self-improving/session-state.json
{
  "session_id": "abc123",
  "state": "ACTIVE",
  "started_at": "2026-04-13T10:00:00Z",
  "last_activity": "2026-04-13T10:15:00Z",
  "skills_used": ["init", "judgment-day"],
  "agents_spawned": ["doc-scanner-core"],
  "files_locked": [],
  "total_tokens": 12345,
  "estimated_cost_usd": 0.42
}
```

### 6.5 File-Conflict-Detection

```python
# hooks/lib/file-lock.py (Konzept)

LOCK_DIR = Path("${CLAUDE_PLUGIN_ROOT}/self-improving/.locks/")

def acquire_lock(file_path: str, session_id: str) -> bool:
    """Versuche File-Lock zu setzen. False wenn anderer Agent die Datei hat."""
    lock_file = LOCK_DIR / hashlib.md5(file_path.encode()).hexdigest()
    if lock_file.exists():
        lock_data = json.loads(lock_file.read_text())
        if lock_data["session_id"] != session_id:
            # Anderer Agent hat die Datei
            age_seconds = time.time() - lock_data["timestamp"]
            if age_seconds < 300:  # Lock ist frisch (< 5min)
                return False
            # Lock ist veraltet → uebernehmen
    lock_file.write_text(json.dumps({
        "session_id": session_id,
        "file_path": file_path,
        "timestamp": time.time(),
    }))
    return True

def release_lock(file_path: str, session_id: str) -> None:
    """Lock freigeben nach Write/Edit."""
    lock_file = LOCK_DIR / hashlib.md5(file_path.encode()).hexdigest()
    if lock_file.exists():
        lock_data = json.loads(lock_file.read_text())
        if lock_data["session_id"] == session_id:
            lock_file.unlink()
```

### 6.6 HTTP Event-Endpoint (Optional, Phase E1)

```
POST http://localhost:2469/event     (Port 2469, NICHT 2468 um Konflikt mit AgentCraft zu vermeiden)
Body: { "type": "skill_invoked", "skill": "judgment-day", "session_id": "abc123" }

Nutzung:
- Externes Monitoring (Grafana, Custom Dashboard)
- Cross-Machine Collaboration (wenn mehrere Entwickler am gleichen Repo)
- AgentCraft-Kompatibilitaet (gleiche Event-Struktur)

Implementierung: Optionaler Python HTTP-Server (uvicorn/http.server)
Aktivierung: Nur wenn META_SKILLS_EVENT_SERVER=1 gesetzt
```

---

## 7. Test-Strategie

### 7.1 Automatische Tests (T1-T10)

| ID | Test | Was wird geprüft | Ausfuehrung | Erwartetes Ergebnis |
|----|------|------------------|-------------|---------------------|
| T1 | `validate.py --all` | Frontmatter aller Skills korrekt | `python3 scripts/validate.py --all` | 0 Errors, 0 Warnings |
| T2 | `eval.py --all --json` | Alle Skills Score >= 70 | `python3 scripts/eval.py --all --json` | Alle Skills >= 70/100 |
| T3 | `test-skills.py --all` | Jeder Skill laesst sich laden und parsen | `python3 scripts/test-skills.py --all` | 15/15 gruene Skills |
| T4 | `test-hooks.py` | Alle 9+ Hooks parsen stdin korrekt | `python3 scripts/test-hooks.py` | 0 Timeouts, 0 Parse-Errors |
| T5 | `cli-health.py` | CLI-Registry korrekt, Health-Check | `python3 scripts/cli-health.py` | Mindestens 2 CLIs verfuegbar |
| T6 | `dependency-graph.py --validate` | DAG konsistent, keine Zirkel | `python3 scripts/dependency-graph.py --validate` | 0 zirkulaere Abhaengigkeiten |
| T7 | `pre-publish-gate.py --dry-run` | Gate-Pipeline laeuft durch | `python3 scripts/pre-publish-gate.py --dry-run` | Gate PASS fuer alle Skills |
| T8 | `autoreason-skills.py --all --dry-run` | Autoreason ohne Schreiben | `python3 scripts/autoreason-skills.py --all --dry-run` | Kein Crash, Score-Output fuer alle |
| T9 | `build-skill-registry.py --json --validate` | Registry-Feed valides JSON | `python3 scripts/build-skill-registry.py --json --validate` | Valides JSON, alle Skills enthalten |
| T10 | `usage-report.py --validate` | Usage-Daten parsebar | `python3 scripts/usage-report.py --validate` | JSONL-Format korrekt |

### 7.2 Manuelle Tests (M1-M15)

| ID | Test | Schritte | Erwartetes Ergebnis |
|----|------|----------|---------------------|
| M1 | Skill-Invocation | `/meta-create` aufrufen | Command-Prompt erscheint, 5-Phasen-Prozess startet |
| M2 | Autoreason Single | `python3 autoreason-skills.py skills/verify/SKILL.md` | Mindestens 1 Pass, Score sichtbar |
| M3 | Autoreason All | `python3 autoreason-skills.py --all --max-passes 2` | Alle Skills verarbeitet, Summary korrekt |
| M4 | Judge-Rotation | Autoreason mit --max-passes 3, Log pruefen | 3 verschiedene Judges pro Pass |
| M5 | CLI-Fallback | Kimi deinstallieren, Autoreason starten | Fallback zu devstral-api funktioniert |
| M6 | Usage-Tracking | Session arbeiten, dann `/meta-status` | Usage-Zahlen sichtbar |
| M7 | Stale-Detection | Skill mit altem `last-verified` Date | `/meta-status` zeigt Stale-Warning |
| M8 | File-Conflict | 2 Claude-Sessions, gleiche Datei editieren | Warnung bei zweiter Session |
| M9 | Pre-Publish-Gate | Skill mit Score < 70 publishen | Gate blockiert |
| M10 | Dependency-Impact | Hook aendern, Impact-Check aufrufen | Betroffene Skills gelistet |
| M11 | Governance-Report | `python3 scripts/governance-report.py` | Report mit Top-Skills, Stale-Alerts |
| M12 | Session-State | Session starten + stoppen | State-File zeigt korrekte Transitions |
| M13 | Cost-Attribution | Autoreason-Run, Cost-Report danach | Kosten pro CLI pro Rolle sichtbar |
| M14 | Registry-Feed | `cat oversight/skill-registry.json \| python3 -m json.tool` | Valides JSON mit allen Feldern |
| M15 | Hook-Chain | User-Prompt → PreToolUse → PostToolUse → Stop | Alle Hooks feuern in korrekter Reihenfolge |

### 7.3 End-to-End Tests (E1-E5)

| ID | Test | Szenario | Dauer | Erfolgskriterium |
|----|------|----------|-------|------------------|
| E1 | Full Autoreason Cycle | Skill mit Score 65 → Autoreason → Score >= 75 | ~10 min | Score-Verbesserung + Convergence |
| E2 | Full Quality Pipeline | Neuen Skill erstellen → validate → eval → test → publish | ~5 min | Gate PASS auf allen Stufen |
| E3 | Full Session Lifecycle | Session Start → 3 Skill-Invocations → Session Stop | ~15 min | Usage-Log korrekt, State-Machine korrekt |
| E4 | Multi-Agent Autoreason | 3 Skills parallel autoreasonen (--batch 3) | ~15 min | Alle 3 bearbeitet, kein Race-Condition |
| E5 | Full Governance Cycle | Woche arbeiten → Governance-Report → Stale-Fixes | ~1 Woche | Report zeigt akkurate Daten, Stale-Skills gefixt |

### 7.4 Regressions-Tests

| Trigger | Test-Suite |
|---------|-----------|
| SKILL.md geaendert | T1 + T2 + T3 fuer betroffenen Skill |
| Hook geaendert | T4 + M15 |
| autoreason-skills.py geaendert | T8 + M2 + M3 |
| Neuer Skill hinzugefuegt | T1-T3 + T6 + T7 |
| CLI-Registry geaendert | T5 + M4 + M5 |
| Dependency-Graph geaendert | T6 + M10 |

### 7.5 Performance/Cost Benchmarks

| Metrik | Messmethode | Zielwert |
|--------|-------------|----------|
| Autoreason Dauer pro Skill | `time python3 autoreason-skills.py skills/X/SKILL.md` | < 3 min (3 Passes) |
| Autoreason Kosten pro Skill | Cost-Report nach Run | < $0.10 pro Skill |
| Hook-Latenz | `time python3 hooks/approach-guard.py < test-input.json` | < 500ms pro Hook |
| Full Test-Suite Dauer | `time python3 scripts/test-skills.py --all` | < 60s |
| Validate-All Dauer | `time python3 scripts/validate.py --all` | < 10s |
| Eval-All Dauer | `time python3 scripts/eval.py --all` | < 30s |
| Governance-Report Dauer | `time python3 scripts/governance-report.py` | < 15s |

---

## 8. Metriken

### 8.1 Vorher/Nachher Tabelle

| Metrik | v3.0 (Vorher) | v4.0 (Nachher) | Delta |
|--------|:---:|:---:|:---:|
| **Skills** | 15 | 15+ | +0 (Qualitaet > Quantitaet) |
| **Hook-Event-Types** | 4 | 6 | +2 (SubagentStop, Notification) |
| **Hooks** | 9 | 13 | +4 (usage-tracker, file-conflict, subagent-tracker, governance-alert) |
| **Scripts** | 24 | 32+ | +8 (cli-health, test-skills, test-hooks, usage-report, dependency-graph, impact-check, pre-publish-gate, governance-report, stale-detector) |
| **Durchschnittlicher Skill-Score** | ~72/100 (geschaetzt) | >= 80/100 | +8 |
| **Skills mit Score < 70** | ~3 (geschaetzt) | 0 | -3 |
| **Integration-Test-Abdeckung** | 0% | 100% (alle Skills + Hooks) | +100% |
| **Usage-Tracking** | Nein | Ja (JSONL pro Session) | Neu |
| **Cost-Attribution** | Nein | Ja (per-Skill, per-CLI) | Neu |
| **Stale-Detection** | Manuell | Automatisch (>30d Warning) | Automatisiert |
| **Dependency-Impact** | Nein | DAG + Impact-Checker | Neu |
| **File-Conflict-Detection** | Nein | Lock-basiert | Neu |
| **Autoreason CLI-Agents** | 4 (kimi, opencode, claude, devstral) | 4+ (erweiterbar via Registry) | Erweiterbar |
| **Autoreason Judge-Rotation** | Statisch | Rotierend pro Pass | Fairer |
| **Score-Plateau-Detection** | Nein | Ja (Delta < 3 ueber 2 Passes) | Effizienter |
| **CI/CD Gate** | Nein | GitHub Actions | Automatisiert |
| **Skill-Registry-Feed** | Menschenlesbar (Markdown) | Maschinen + Menschenlesbar (JSON + MD) | Discoverable |
| **Governance-Report** | Nein | Woechentlich automatisch | Transparenz |
| **Session-State-Machine** | Basis (init/stop) | Vollstaendig (INIT→ACTIVE→IDLE→STOP) | Robuster |
| **Hook-Latenz (p99)** | Ungemessen | < 500ms (Ziel) | Messbar |
| **Autoreason-Kosten pro Skill** | Ungemessen | < $0.10 (Ziel) | Messbar |

### 8.2 North-Star-Metriken

| Metrik | Definition | Zielwert v4.0 |
|--------|-----------|:---:|
| **Mean Skill Quality Score** | Durchschnitt aller eval.py Scores | >= 80 |
| **Integration-Test-Pass-Rate** | % Skills die Funktionstest bestehen | 100% |
| **Autoreason Convergence Rate** | % Skills die in <= 3 Passes konvergieren | >= 80% |
| **Monthly Active Skills** | Skills die mindestens 1x/Monat benutzt werden | >= 10 |
| **Mean Time to Detect Stale Skill** | Tage bis ein ungenutzter Skill geflaggt wird | <= 7 |

---

## 9. Risiken + Mitigationen

### Risiko 1: CLI-Verfuegbarkeit (HOCH)

| Aspekt | Detail |
|--------|--------|
| **Beschreibung** | kimi, opencode, oder andere CLIs koennen Versionen breaken, APIs aendern, oder temporaer offline sein |
| **Wahrscheinlichkeit** | Hoch (3 externe Abhaengigkeiten) |
| **Impact** | Autoreason laeuft im Fallback-Modus oder gar nicht |
| **Mitigation 1** | Fallback-Chain pro Rolle (jede Rolle hat Primaer + Fallback Agent) |
| **Mitigation 2** | eval-only Modus als letzter Fallback (0 LLM-Tokens, nur Score-Check) |
| **Mitigation 3** | CLI-Health-Check beim Start mit klarer Warnung welche Agents fehlen |
| **Monitoring** | `cli-health.py` als Teil von `/meta-status` |

### Risiko 2: Token-Kosten-Explosion (MITTEL)

| Aspekt | Detail |
|--------|--------|
| **Beschreibung** | Autoreason mit 3 CLI-Agents + 3 Judges pro Pass kann teuer werden, besonders `--all` auf 15 Skills |
| **Wahrscheinlichkeit** | Mittel (kimi/opencode kostenlos, nur Claude + Devstral kosten) |
| **Impact** | Budget-Ueberschreitung bei haeufigem `--all` Usage |
| **Mitigation 1** | Score-Delta-Gate: stoppt wenn Verbesserung < 3 Punkte (spart Passes) |
| **Mitigation 2** | Cost-Tracking mit Budget-Alarm (warnt bei > $1.00 pro Run) |
| **Mitigation 3** | `--budget` Flag: maximale Kosten pro Run konfigurierbar |
| **Monitoring** | Cost-Attribution in Governance-Dashboard |

### Risiko 3: File-Conflict bei Multi-Agent-Arbeit (MITTEL)

| Aspekt | Detail |
|--------|--------|
| **Beschreibung** | Zwei Claude-Sessions oder Claude + Sub-Agent editieren gleichzeitig dieselbe Datei |
| **Wahrscheinlichkeit** | Mittel (bei dispatch + parallel Agents) |
| **Impact** | Daten-Verlust oder inkonsistente Dateien |
| **Mitigation 1** | File-Lock-System (Phase 8) mit 5-Minuten-Timeout |
| **Mitigation 2** | Lock-Cleanup in session-stop.py (Orphaned Locks entfernen) |
| **Mitigation 3** | Warning statt Block: User entscheidet ob Override |
| **Monitoring** | File-Conflict-Counter in Usage-Tracking |

### Risiko 4: Hook-Latenz beeintraechtigt UX (NIEDRIG)

| Aspekt | Detail |
|--------|--------|
| **Beschreibung** | 13 Hooks statt 9 koennen spuerbare Verzoegerung verursachen (besonders bei UserPromptSubmit mit 4 Hooks) |
| **Wahrscheinlichkeit** | Niedrig (Hooks haben Timeouts, Python-Startup ist schnell) |
| **Impact** | User wartet laenger auf Response |
| **Mitigation 1** | Alle neuen Hooks haben `timeout: 3` (max 3 Sekunden) |
| **Mitigation 2** | Hook-Latenz-Benchmark in Test-Suite (T4) |
| **Mitigation 3** | Neue Hooks als `async: true` wo moeglich (Fire-and-Forget) |
| **Monitoring** | Hook-Latenz in token-audit.py geloggt |

### Risiko 5: Backward-Compatibility-Break (NIEDRIG)

| Aspekt | Detail |
|--------|--------|
| **Beschreibung** | v4.0 Aenderungen an hooks.json, autoreason-skills.py oder CLAUDE.md breaken bestehende Workflows |
| **Wahrscheinlichkeit** | Niedrig (inkrementelle Phasen, Regressions-Tests) |
| **Impact** | Bestehende Skills/Commands funktionieren nicht mehr |
| **Mitigation 1** | Phasen-basierte Implementierung (nichts wird auf einmal geaendert) |
| **Mitigation 2** | Regressions-Test-Suite nach jeder Phase |
| **Mitigation 3** | `validate.py --all` + `eval.py --all` als Gate vor jedem Merge |
| **Monitoring** | CI/CD Gate (Phase 6) verhindert Merges mit Regressions |

---

## 10. Glossar

| Begriff | Definition |
|---------|-----------|
| **Autoreason** | Selbst-Verbesserungsprozess fuer Skills inspiriert von NousResearch/autoreason. Iterativer Critic→Revision→Synthese→Judge Zyklus |
| **Borda Count** | Wahlverfahren: jeder Judge rankt 3 Versionen, 1. Platz = 2 Punkte, 2. = 1, 3. = 0. Hoechste Summe gewinnt |
| **CLI-Agent** | Externes AI-Tool das per Subprocess aufgerufen wird (kimi, opencode, claude) |
| **Convergence** | Autoreason stoppt wenn Version A (Incumbent) k-mal hintereinander gewinnt (k=2 default) |
| **Cost-Attribution** | Zuordnung von Token-Kosten zu spezifischen Skills, Rollen und CLI-Agents |
| **DAG** | Directed Acyclic Graph — Abhaengigkeitsgraph zwischen Skills, Hooks und Commands |
| **Dependency-Impact** | Analyse welche Komponenten brechen wenn eine bestimmte Datei geaendert wird |
| **eval.py** | Deterministisches Scoring-Script (0-100) das SKILL.md Qualitaet misst. 0 LLM-Tokens |
| **File-Conflict** | Situation in der zwei Agents gleichzeitig dieselbe Datei bearbeiten wollen |
| **File-Lock** | Mechanismus der temporaer exklusiven Zugriff auf eine Datei sichert |
| **Fire-and-Forget** | Event wird gesendet ohne auf Antwort zu warten (HTTP POST, kein Response-Handling) |
| **Frontmatter** | YAML-Block am Anfang einer SKILL.md Datei mit Metadaten (name, version, model, etc.) |
| **Governance Dashboard** | Zentraler Ueberblick ueber Gesundheit, Nutzung und Kosten aller Skills |
| **Hook** | Python-Script das bei bestimmten Claude-Code-Events automatisch ausgefuehrt wird |
| **Incumbent** | Version A im Autoreason-Prozess — die aktuelle, unveraenderte SKILL.md |
| **Integration-Test** | Test der prueft ob ein Skill tatsaechlich funktioniert (nicht nur ob er valide ist) |
| **Judge** | LLM-Agent der 3 Versionen blind bewertet und rankt |
| **Judge-Rotation** | Wechsel der Judge-Zuweisung ueber Passes hinweg um Bias zu vermeiden |
| **meta-loop** | Iterationsschleife mit objektiven Gates (Score-basiert, nicht subjektiv) |
| **OpenRouter** | API-Gateway das Zugriff auf verschiedene LLM-Provider bietet (hier: Devstral) |
| **Pre-Publish-Gate** | Kombinierter Check vor Skill-Veroeffentlichung: validate + eval + test + dependency |
| **Progressive Disclosure** | Design-Pattern: Kern-Info in SKILL.md, Details in references/ Unterverzeichnis |
| **Quality Gate** | Automatischer Check der bestimmte Qualitaetskriterien durchsetzt (Hook-basiert) |
| **Reworker** | Script das automatisch Skill-Probleme diagnostiziert und einfache Fixes anwendet |
| **Score-Delta-Gate** | Stoppt Autoreason wenn Score-Verbesserung < 3 Punkte ueber 2 Passes (Plateau) |
| **Session-State-Machine** | Zustandsautomat der Session-Lifecycle verwaltet: INIT → ACTIVE → IDLE → STOP |
| **Skill-Registry** | Maschinenlesbarer Index aller verfuegbaren Skills mit Metadaten |
| **Stale-Detection** | Automatisches Erkennen von Skills die laenger als 30 Tage nicht aktualisiert wurden |
| **Synthesizer** | LLM-Agent der zwei Versionen zu einer kohaerenten Synthese kombiniert |
| **Usage-Tracking** | JSONL-basiertes Logging jeder Skill-Invocation (wer, wann, wie lange, Ergebnis) |
| **validate.py** | CI-Gate das SKILL.md Frontmatter gegen Schema validiert. 0 LLM-Tokens |
| **WebSocket-Bridge** | Bidirektionale Kommunikation fuer Real-Time Monitoring (AgentCraft-Pattern) |

---

*Dokument-Ende. Naechster Schritt: Joe reviewt, priorisiert, gibt Phase 1 frei.*
