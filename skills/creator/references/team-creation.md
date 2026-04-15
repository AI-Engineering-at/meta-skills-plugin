# Phase 4c-Team: Team-Spezifische Felder

> Loaded on-demand during Phase 4 when Phase 1 determined complexity=team.

Wenn Phase 1 "Team" ergab, sammle diese zusaetzlichen Informationen:

1. **Workers definieren:**
   "Welche Agents/Skills laufen parallel?"
   → Liste als `team-workers: [agent1, agent2, agent3]`
   → Pruefen ob jeder Worker als .claude/agents/*.md existiert
   → Fehlende Workers: "agent1 existiert noch nicht. Soll ich ihn nach Phase 5 erstellen?"

2. **Consolidator definieren:**
   "Wer fasst die Ergebnisse zusammen?"
   → Ein Agent der alle Worker-Outputs zusammenfuehrt
   → `team-consolidator: richter` (oder neuer Agent)
   → Consolidator MUSS als .claude/agents/*.md existieren

3. **Presets definieren (optional):**
   "Gibt es verschiedene Modi? (z.B. quick/full/security)"
   → Preset-Tabelle mit Worker-Zuordnung erstellen
   → Beispiel: war-consul hat 7 Presets (code, security, business, infra, claude-md, full, quick)

4. **Frontmatter generieren:**
   ```yaml
   complexity: team
   team-workers: [worker1, worker2, worker3]
   team-consolidator: consolidator-name
   ```

5. **Body-Template fuer Teams:**
   - Usage Section mit Preset-Beispielen
   - Preset-Tabelle (Preset | Workers | Use Case)
   - Execution Flow (Dispatch → Collect → Consolidate)
   - Severity/Output Definition

Referenz-Team: `.claude/skills/war-consul/SKILL.md` (15 Workers, richter Consolidator, 7 Presets)
