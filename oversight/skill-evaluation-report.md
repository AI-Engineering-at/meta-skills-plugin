# Skill-Evaluierung — Unabhängiger Skill-Evaluator

> Bewertet alle 15 Skills nach objektiven Kriterien aus eval.py v3
> Datum: 2026-04-14
> Evaluierer: Unabhängig (keine Beteiligung an irgendeiner Version)

---

## Bewertungskriterien (aus eval.py v3)

| Kriterium | Punkte | Beschreibung |
|-----------|--------|-------------|
| **Body Conciseness** | 0-15 | Body ≤150 Lines = 15, ≤200 = 8, >200 = 0 |
| **Tool Minimalism** | 0-15 | ≤4 Tools = 15, ≤6 = 8, >6 = 0 |
| **Token Budget** | 0-15 | Explizites token-budget definiert |
| **Complexity Declared** | 0-10 | Declared complexity field vorhanden |
| **Trigger Words** | 0-10 | Trigger in description |
| **Version Tracking** | 0-10 | Version field vorhanden |
| **Model Efficiency** | 0-10 | haiku/sonnet = 10, opus = 5, unknown = 0 |
| **Progressive Disclosure** | 0-10 | disclosure_ratio <0.7 = 10, ref_files >0 = 5 |
| **Category** | 0-5 | Category field vorhanden |

---

## Evaluierung aller 15 Skills

### 1. statusbar — Session Lifecycle
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~120 Lines | **15** |
| Tool Minimalism | 2 Tools (Read, Bash) | **15** |
| Token Budget | 200 | **15** |
| Complexity Declared | skill | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 2.0.0 | **10** |
| Model Efficiency | haiku | **10** |
| Progressive Disclosure | 0 ref_files | **0** |
| Category | meta | **5** |
| **GESAMT** | | **90/100** |

**Stärken:** Extrem sparsam mit Tokens (200 Budget), haiku als Modell, nur 2 Tools, klare Struktur.
**Schwächen:** Keine reference-Files für progressive Disclosure.

---

### 2. dispatch — Parallel Sub-Agent Development
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~170 Lines | **8** |
| Tool Minimalism | 5 Tools | **8** |
| Token Budget | 5000 | **15** |
| Complexity Declared | skill | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 1.0.0 | **10** |
| Model Efficiency | sonnet | **10** |
| Progressive Disclosure | 0 ref_files | **0** |
| Category | orchestration | **5** |
| **GESAMT** | | **76/100** |

**Stärken:** Klares dispatch Pattern, Model Selection Guide, Two-Stage Review.
**Schwächen:** Etwas lang für einen Skill, 5 Tools sind grenzwertig.

---

### 3. creator — Cooperative Skill Creation
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~280 Lines | **0** |
| Tool Minimalism | 6 Tools | **8** |
| Token Budget | 25000 | **15** |
| Complexity Declared | agent | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 0.2.0 | **10** |
| Model Efficiency | sonnet | **10** |
| Progressive Disclosure | ref_files vorhanden | **5** |
| Category | meta | **5** |
| **GESAMT** | | **73/100** |

**Stärken:** Sehr umfassend, 5-Phase-Prozess, Learning Layer Integration.
**Schwächen:** Sehr langer Body, komplexitätsangemessen aber trotzdem ausufernd.

---

### 4. feedback — Bidirectional Session Review
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~80 Lines | **15** |
| Tool Minimalism | 5 Tools | **8** |
| Token Budget | 12000 | **15** |
| Complexity Declared | skill | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 1.0.0 | **10** |
| Model Efficiency | sonnet | **10** |
| Progressive Disclosure | ref_files vorhanden | **5** |
| Category | meta | **5** |
| **GESAMT** | | **88/100** |

**Stärken:** Kompakt, klar strukturiert, gute reference-Files.
**Schwächen:** 5 Tools sind mehr als ideal.

---

### 5. knowledge — Knowledge Funnel
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~180 Lines | **8** |
| Tool Minimalism | 4 Tools | **15** |
| Token Budget | 8000 | **15** |
| Complexity Declared | skill | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 1.0.0 | **10** |
| Model Efficiency | haiku | **10** |
| Progressive Disclosure | 0 ref_files | **0** |
| Category | meta | **5** |
| **GESAMT** | | **83/100** |

**Stärken:** 4-Layer Architektur, haiku-Modell, klare Modes.
**Schwächen:** Keine reference-Files, Body etwas lang.

---

### 6. init — Intelligent Project Entry Point
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~160 Lines | **8** |
| Tool Minimalism | 4 Tools | **15** |
| Token Budget | 2500 | **15** |
| Complexity Declared | skill | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 1.0.0 | **10** |
| Model Efficiency | sonnet | **10** |
| Progressive Disclosure | ref_files vorhanden | **5** |
| Category | meta | **5** |
| **GESAMT** | | **88/100** |

**Stärken:** Orchestrator-Pattern, SDD-Modus, gute Delegation.
**Schwächen:** Body könnte kürzer sein.

---

### 7. harden — Automated Hardening Loop
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~240 Lines | **0** |
| Tool Minimalism | 5 Tools | **8** |
| Token Budget | 10000 | **15** |
| Complexity Declared | agent | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 1.0.0 | **10** |
| Model Efficiency | sonnet | **10** |
| Progressive Disclosure | 0 ref_files | **0** |
| Category | orchestration | **5** |
| **GESAMT** | | **68/100** |

**Stärken:** Umfassender SCAN-TRIAGE-FIX-VERIFY-Zyklus, Security-First.
**Schwächen:** Sehr lang, keine reference-Files obwohl komplex.

---

### 8. verify — Evidence Before Claims
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~110 Lines | **15** |
| Tool Minimalism | 3 Tools | **15** |
| Token Budget | 3000 | **15** |
| Complexity Declared | skill | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 1.0.0 | **10** |
| Model Efficiency | sonnet | **10** |
| Progressive Disclosure | 0 ref_files | **0** |
| Category | verification | **5** |
| **GESAMT** | | **90/100** |

**Stärken:** Kompakt, "Iron Law" klar kommuniziert, minimale Tools.
**Schwächen:** Keine reference-Files.

---

### 9. systematic-debugging — Root Cause Investigation
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~200 Lines | **0** |
| Tool Minimalism | 4 Tools | **15** |
| Token Budget | 3000 | **15** |
| Complexity Declared | skill | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 1.0.0 | **10** |
| Model Efficiency | sonnet | **10** |
| Progressive Disclosure | 0 ref_files | **0** |
| Category | debugging | **5** |
| **GESAMT** | | **75/100** |

**Stärken:** 4-Phase-Prozess, "Iron Law", gute Red Flags.
**Schwächen:** Body zu lang für die Komplexität.

---

### 10. git-worktrees — Isolated Git Workspaces
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~130 Lines | **15** |
| Tool Minimalism | 3 Tools | **15** |
| Token Budget | 2000 | **15** |
| Complexity Declared | skill | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 1.0.0 | **10** |
| Model Efficiency | haiku | **10** |
| Progressive Disclosure | 0 ref_files | **0** |
| Category | git | **5** |
| **GESAMT** | | **90/100** |

**Stärken:** Klar, prägnant, haiku-Modell, perfekte Tool-Auswahl.
**Schwächen:** Keine reference-Files.

---

### 11. tdd — Test-Driven Development
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~150 Lines | **15** |
| Tool Minimalism | 4 Tools | **15** |
| Token Budget | 3000 | **15** |
| Complexity Declared | skill | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 1.0.0 | **10** |
| Model Efficiency | sonnet | **10** |
| Progressive Disclosure | 0 ref_files | **0** |
| Category | testing | **5** |
| **GESAMT** | | **90/100** |

**Stärken:** Red-Green-Refactor klar erklärt, "Iron Law", gute Beispiele.
**Schwächen:** Keine reference-Files.

---

### 12. refactor-loop — Automated Refactoring
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~120 Lines | **15** |
| Tool Minimalism | 6 Tools | **8** |
| Token Budget | 8000 | **15** |
| Complexity Declared | skill | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 1.0.0 | **10** |
| Model Efficiency | sonnet | **10** |
| Progressive Disclosure | 0 ref_files | **0** |
| Category | refactoring | **5** |
| **GESAMT** | | **83/100** |

**Stärken:** 6-Schritt-Zyklus, adversarial-dev Prinzip, Git-Checkpoint.
**Schwächen:** 6 Tools sind zu viele.

---

### 13. design — Visual DESIGN.md Generator
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~60 Lines | **15** |
| Tool Minimalism | 2 Tools | **15** |
| Token Budget | 3000 | **15** |
| Complexity Declared | Ja (fehlt im Frontmatter!) | **0** |
| Trigger Words | Ja | **10** |
| Version Tracking | 0.1.0 | **10** |
| Model Efficiency | sonnet | **10** |
| Progressive Disclosure | 0 ref_files | **0** |
| Category | meta | **5** |
| **GESAMT** | | **65/100** |

**Stärken:** Sehr kompakt, minimale Tools.
**Schwächen:** **FEHLT complexity field!** Sehr oberflächlich, kaum Substanz.

---

### 14. doc-updater — Agent Team Orchestrator
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~200 Lines | **0** |
| Tool Minimalism | 6 Tools | **8** |
| Token Budget | 1500 | **15** |
| Complexity Declared | team | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 2.0.0 | **10** |
| Model Efficiency | sonnet | **10** |
| Progressive Disclosure | 0 ref_files (aber agents als Workers) | **0** |
| Category | documentation | **5** |
| **GESAMT** | | **68/100** |

**Stärken:** Team-Orchestrierung, Smart-Routing, Preset-System.
**Schwächen:** Body zu lang, 6 Tools, keine reference-Files.

---

### 15. judgment-day — Adversarial Blind Review
| Kriterium | Wert | Punkte |
|-----------|------|--------|
| Body Conciseness | ~200 Lines | **0** |
| Tool Minimalism | 5 Tools | **8** |
| Token Budget | 8000 | **15** |
| Complexity Declared | agent | **10** |
| Trigger Words | Ja | **10** |
| Version Tracking | 1.0.0 | **10** |
| Model Efficiency | sonnet | **10** |
| Progressive Disclosure | 0 ref_files | **0** |
| Category | review | **5** |
| **GESAMT** | | **68/100** |

**Stärken:** Adversarial Pattern, 2 Judges parallel, Convergence Pattern.
**Schwächen:** Body zu lang, keine reference-Files obwohl komplex.

---

## Gesamtranking

| Rang | Skill | Score | Modell | Budget | Tools | Body |
|------|-------|-------|--------|--------|-------|------|
| 🥇 1 | **statusbar** | **90/100** | haiku | 200 | 2 | ~120 |
| 🥇 2 | **verify** | **90/100** | sonnet | 3000 | 3 | ~110 |
| 🥇 3 | **git-worktrees** | **90/100** | haiku | 2000 | 3 | ~130 |
| 🥇 4 | **tdd** | **90/100** | sonnet | 3000 | 4 | ~150 |
| 🥈 5 | **feedback** | **88/100** | sonnet | 12000 | 5 | ~80 |
| 🥈 6 | **init** | **88/100** | sonnet | 2500 | 4 | ~160 |
| 🥉 7 | **knowledge** | **83/100** | haiku | 8000 | 4 | ~180 |
| 🥉 8 | **refactor-loop** | **83/100** | sonnet | 8000 | 6 | ~120 |
| 9 | **dispatch** | **76/100** | sonnet | 5000 | 5 | ~170 |
| 10 | **systematic-debugging** | **75/100** | sonnet | 3000 | 4 | ~200 |
| 11 | **creator** | **73/100** | sonnet | 25000 | 6 | ~280 |
| 12 | **harden** | **68/100** | sonnet | 10000 | 5 | ~240 |
| 12 | **doc-updater** | **68/100** | sonnet | 1500 | 6 | ~200 |
| 12 | **judgment-day** | **68/100** | sonnet | 8000 | 5 | ~200 |
| 15 | **design** | **65/100** | sonnet | 3000 | 2 | ~60 |

---

## Fazit

### Bester Skill: **statusbar** (90/100) — geteilt mit verify, git-worktrees, tdd

Die **statusbar** ist der beste Skill, weil er:
1. **Extrem token-effizient** ist (200 Token Budget — niedrigster aller Skills)
2. **haiku** als Modell verwendet (günstigstes angemessenes Modell)
3. Nur **2 Tools** benötigt (minimalster Footprint)
4. Klare, präzise Struktur mit **3 Komponenten** (Statusline, Watcher, Sync)
5. **Version 2.0.0** zeigt Iteration und Reife
6. Cross-Platform Support dokumentiert

### Schlechtester Skill: **design** (65/100)

Der **design** Skill ist der schwächste, weil er:
1. **Kein complexity field** hat (wichtiges Frontmatter-Feld fehlt)
2. Sehr oberflächlich ist (~60 Lines ohne Substanz)
3. Im Wesentlichen nur ein Dashboard-Start-Skript ist
4. Keine eigentliche Funktionalität beschreibt

### Allgemeine Beobachtungen

- **Top-Skills** sind kompakt (≤150 Lines), haben ≤4 Tools, nutzen haiku/sonnet
- **Schwache Skills** sind lang (>200 Lines), haben >5 Tools, keine reference-Files
- **Progressive Disclosure** wird kaum genutzt (nur creator, feedback, init haben ref_files)
- **Trigger Words** sind durchgehend gut gepflegt
- **Version Tracking** ist konsistent (nur design hat 0.1.0)
