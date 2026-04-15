# Export: Skill teilbar machen

> Loaded on-demand when user says "exportiere den Skill", "share skill", "Skill teilen".

## 1. Sanitize (Rule 09 Anonymisierung)

- IPs → Platzhalter (`10.40.10.90` → `<gpu-server>`, `.80` → `<manager-node>`)
- Ports → `<service-port>` (ausser Ollama :11434 — Standard)
- Vault-Pfade → `<vault-command>` Platzhalter
- Channel-IDs → `<channel-id>`
- User-spezifische Pfade → relative Pfade

## 2. Format waehlen

- A) **Unser Format** (meta-skills): Frontmatter + Body + references/ → effizientestes Format
- B) **Standard Format** (AgentSkills.io): Portabel fuer Claude, Cursor, ChatGPT, Gemini
  Validierung: `python "${CLAUDE_PLUGIN_ROOT}/scripts/validate-agentskills.py" <file> --strict`

## 3. Exportieren

- Sanitized Skill in `exports/<name>/` schreiben
- README.md generieren: Was der Skill macht, welche ENV Variablen noetig sind
- Optional: auf hub.ai-engineering.at publizieren

```
Mein Skill (personalisiert)
  ├── Export → Unser Format (sanitized, effizient)
  └── Export → Standard Format (portabel, universell)
```

## Import durch andere User

```
Externer Skill → Phase 0 liest DEREN Preferences → Auto-Anpassung
  - "<gpu-server>" → deren GPU IP
  - Model-Empfehlung basierend auf deren Hardware
  - Trigger-Woerter in deren Sprache
```
