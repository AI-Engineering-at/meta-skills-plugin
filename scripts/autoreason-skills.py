#!/usr/bin/env python3
"""Autoreason for Skills -- Self-Refinement That Knows When to Stop

Adapted from NousResearch/autoreason for SKILL.md quality improvement.

Each iteration produces 3 competing versions:
  A  = unchanged incumbent (current SKILL.md)
  B  = adversarial revision (addresses critic findings)
  AB = synthesis (best elements from both)

3 fresh judge agents rank A, B, AB via blind Borda count.
"Do nothing" (A stays) is always first-class.
Converges when A wins k=2 consecutive times.

Usage:
  python3 autoreason-skills.py skills/verify/SKILL.md          # Improve one skill
  python3 autoreason-skills.py --all                            # Improve all skills
  python3 autoreason-skills.py --all --dry-run                  # Show what would change
  python3 autoreason-skills.py skills/dispatch/SKILL.md --max-passes 5

Requires: ANTHROPIC_API_KEY in environment (uses Claude API directly).
If no API key: falls back to eval.py scoring only (no LLM refinement).
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    Path(__file__).parent.parent
))
SKILLS_DIR = PLUGIN_ROOT / "skills"
EVAL_SCRIPT = PLUGIN_ROOT / "scripts" / "eval-skill.py"
VALIDATE_SCRIPT = PLUGIN_ROOT / "scripts" / "validate.py"
RESULTS_DIR = PLUGIN_ROOT / "oversight" / "autoreason"

# --- Autoreason Config (from centralized config, fallback to defaults) ---
try:
    sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
    from lib.config import load_config as _load_config
    _cfg = _load_config()
    _ar = _cfg.get("autoreason", {})
    MAX_PASSES = _ar.get("max_passes", 5)
    CONVERGENCE_K = _ar.get("convergence_k", 2)
    _CLI_TIMEOUT = _ar.get("cli_timeout_s", 180)
    _API_TIMEOUT = _ar.get("api_timeout_s", 120)
except Exception:
    MAX_PASSES = 5
    CONVERGENCE_K = 2
    _CLI_TIMEOUT = 180
    _API_TIMEOUT = 120

# --- Prompts (adapted from NousResearch/autoreason) ---
CRITIC_SYSTEM = (
    "Du bist ein kritischer Skill-Reviewer. Dein EINZIGER Job: echte Probleme finden. "
    "Sei spezifisch und konkret. Schlage KEINE Fixes vor."
)

CRITIC_PROMPT = """Hier ist ein SKILL.md File fuer ein Claude Code Plugin:

---
{skill_content}
---

Finde echte Probleme:
- Unklare oder fehlende Trigger-Woerter (wann wird der Skill aktiviert?)
- Fehlende Frontmatter-Felder (version, model, allowed-tools, token-budget)
- Body zu lang (>150 Zeilen) oder zu kurz (<20 Zeilen)
- Inkonsistente oder widerspruechliche Anweisungen
- Fehlende Beispiele oder Edge Cases
- Over-Engineering (zu viele Tools, zu komplexe Prozesse fuer simple Tasks)
- Token-Verschwendung (redundante Sections, zu viel Prosa)

NUR echte Probleme. Keine kosmetischen Verbesserungen. Keine Lob-Formeln."""

AUTHOR_B_SYSTEM = (
    "Du bist ein Skill-Experte der SKILL.md Files verbessert. "
    "Adressiere NUR die identifizierten Probleme. "
    "Mache KEINE Aenderungen die nicht durch ein Problem motiviert sind."
)

AUTHOR_B_PROMPT = """ORIGINAL SKILL.md:
---
{skill_content}
---

PROBLEME GEFUNDEN:
---
{critique}
---

Ueberarbeite das SKILL.md um die Probleme zu beheben.
Fuer jede Aenderung: sage welches Problem sie loest.
Gib das KOMPLETTE ueberarbeitete SKILL.md aus (inkl. Frontmatter).
Mache KEINE Aenderungen die nicht durch ein identifiziertes Problem motiviert sind."""

AUTHOR_C_SYSTEM = (
    "Du bist ein Skill-Experte der FUNDAMENTAL ANDERE Ansaetze findet. "
    "Die vorherige Revision hat die Judges NICHT ueberzeugt. "
    "Dein Job: komplett anderen Blickwinkel, andere Struktur, andere Schwerpunkte."
)

AUTHOR_C_PROMPT = """ORIGINAL SKILL.md (der aktuelle Gewinner):
---
{skill_content}
---

VORHERIGE KRITIK (wurde bereits versucht zu fixen, hat NICHT ueberzeugt):
---
{critique}
---

VORHERIGER REVISIONS-ANSATZ (hat VERLOREN — mach es KOMPLETT ANDERS):
---
{failed_revision_summary}
---

Erstelle eine FUNDAMENTAL ANDERE Version:
- Andere Struktur (z.B. weniger Sections statt mehr, oder umgekehrt)
- Andere Schwerpunkte (z.B. Beispiele statt Regeln, oder Checkliste statt Prosa)
- Anderer Ton (z.B. direkter/kuerzer oder ausfuehrlicher mit Kontext)
- Ueberrasche: was waere wenn der Skill nur halb so lang waere? Oder doppelt?

Gib das KOMPLETTE SKILL.md aus (inkl. Frontmatter).
Erklaere in 1 Satz was du fundamental anders gemacht hast."""

RECOMBINE_SYSTEM = (
    "Du bist ein Skill-Experte. Du erhaeltst zwei verschiedene Revisionen die "
    "beide Staerken haben. Kombiniere die besten Elemente zu einer kohaerenten Version."
)

RECOMBINE_PROMPT = """Zwei verschiedene Revisionen eines Skills. Beide haben Staerken:

REVISION B (inkrementell):
---
{version_b}
---

REVISION C (orthogonal/radikal):
---
{version_c}
---

Kombiniere die staerksten Elemente aus beiden.
Gib das KOMPLETTE SKILL.md aus (inkl. Frontmatter)."""

SYNTHESIZER_SYSTEM = (
    "Du bist ein Skill-Experte. Du erhaeltst zwei Versionen als gleichwertige Inputs. "
    "Nimm die besten Elemente aus beiden und erstelle eine kohaerente Synthese."
)

SYNTHESIZER_PROMPT = """Hier sind zwei Versionen eines SKILL.md Files. Behandle sie als gleichwertige Inputs.

VERSION X:
---
{version_x}
---

VERSION Y:
---
{version_y}
---

Erstelle eine Synthese die die staerksten Elemente aus beiden nimmt.
Waehle pro Abschnitt die bessere Version und mach sie kohaerent.
Gib das KOMPLETTE SKILL.md aus (inkl. Frontmatter)."""

JUDGE_SYSTEM = (
    "Du bist ein unabhaengiger Skill-Evaluator. Du hast keinen Anteil an irgendeiner Version. "
    "Bewerte welche Version den Skill am besten erfuellt."
)

JUDGE_PROMPT = """Drei Versionen eines SKILL.md wurden unabhaengig erstellt. Bewerte:

BEWERTUNGS-KRITERIEN:
- Trigger-Qualitaet: Wird der Skill in den richtigen Situationen aktiviert?
- Frontmatter-Vollstaendigkeit: Alle nötigen Felder vorhanden?
- Body-Qualitaet: Klar, praezise, actionable?
- Token-Effizienz: Keine Verschwendung?
- Gesamtqualitaet: Wuerde dieser Skill in Production funktionieren?

VERSION 1:
---
{version_1}
---

VERSION 2:
---
{version_2}
---

VERSION 3:
---
{version_3}
---

Bewerte jede Version kurz (2-3 Saetze). Dann:

CONFIDENCE: [high|medium|low]
high = clear winner, obvious quality difference
medium = some differences but close call
low = hard to tell, marginal differences

RANKING: [best], [second], [worst]

Wobei jeder Slot die Versionsnummer (1, 2, oder 3) ist."""


def run_eval(skill_path: Path) -> dict:
    """Run eval-skill.py on a SKILL.md and return score + metrics."""
    if not EVAL_SCRIPT.exists():
        return {"score": -1, "error": "eval-skill.py not found"}
    try:
        result = subprocess.run(
            [sys.executable, str(EVAL_SCRIPT), str(skill_path)],
            capture_output=True, text=True, timeout=15,
        )
        # Parse score from output
        for line in result.stdout.split("\n"):
            if "score" in line.lower() and ":" in line:
                try:
                    score = int("".join(c for c in line.split(":")[-1] if c.isdigit()))
                    return {"score": score, "output": result.stdout[:500]}
                except ValueError:
                    pass
        return {"score": -1, "output": result.stdout[:500]}
    except Exception as e:
        return {"score": -1, "error": str(e)}


# --- CLI-Based Multi-Agent Council ---
# 7 CLI tools + 1 API fallback = maximum cross-model diversity
# Like war-consul but with REAL different AI models from different companies
CLI_AGENTS = {
    "claude": {
        "cmd": ["claude", "-p", "{prompt}", "--output-format", "text"],
        "check": ["claude", "--version"],
        "timeout": 120,
        "vendor": "Anthropic",
        "strengths": "Best synthesis, strongest reasoning, most reliable",
    },
    "kimi": {
        "cmd": ["kimi", "-p", "{prompt}", "--print", "--final-message-only"],
        "check": ["kimi", "--version"],
        "timeout": 180,
        "vendor": "Moonshot AI",
        "strengths": "Strong reasoning (k2.5), good at finding issues",
    },
    "qwen": {
        "cmd": ["qwen", "-p", "{prompt}", "--output-format", "text"],
        "check": ["qwen", "--version"],
        "timeout": 180,
        "vendor": "Alibaba/Qwen",
        "strengths": "Multilingual, good code understanding, fast",
    },
    "codex": {
        "cmd": ["codex", "exec", "{prompt}"],
        "check": ["codex", "--version"],
        "timeout": 120,
        "vendor": "OpenAI",
        "strengths": "Code-focused, strong at refactoring",
    },
    "copilot": {
        "cmd": ["copilot", "-p", "{prompt}", "--allow-all-tools"],
        "check": ["copilot", "--version"],
        "timeout": 120,
        "vendor": "GitHub/OpenAI",
        "strengths": "Code review, pattern matching, pragmatic",
    },
    "opencode": {
        "cmd": ["opencode", "run", "{prompt}"],
        "check": ["opencode", "--version"],
        "timeout": 120,
        "vendor": "OpenCode (multi-model)",
        "strengths": "Can use different models via -m flag",
    },
    # API fallback (Devstral via OpenRouter -- no CLI needed)
    "devstral": {
        "cmd": None,
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key_env": "OPENROUTER_API_KEY",
        "model": "mistralai/devstral-small",
        "timeout": 120,
        "vendor": "Mistral AI",
        "strengths": "Code-specialized, fast, cost-effective",
    },
}

# --- Council Configuration ---
# Judges rotate through ALL available CLIs for maximum diversity.
# The more diverse the judges, the fewer blind spots.
# Order: primary preference (most reliable first, fallback last)
JUDGE_PRIORITY = ["kimi", "qwen", "devstral", "codex", "copilot", "opencode", "claude"]

# Role assignments (best tool for each role)
ROLE_AGENTS = {
    "critic": "kimi",       # Kimi k2.5: strong reasoning, finds real issues
    "author_b": "qwen",     # Qwen: fast, good code revision
    "synthesizer": "claude", # Claude: best synthesis quality
}

# How many judges to use (from config, default 3)
NUM_JUDGES = _ar.get("num_judges", 3) if '_ar' in dir() else 3


def detect_available_clis() -> list:
    """Detect which CLI tools are available.
    On Windows, npm-installed CLIs need shell=True for .cmd wrappers.
    """
    import platform
    is_windows = platform.system() == "Windows"
    available = []

    for name, config in CLI_AGENTS.items():
        if config.get("cmd") is None:
            # API-based, check for API key
            key_env = config.get("api_key_env", "")
            if key_env and os.environ.get(key_env, ""):
                available.append(name)
            continue
        try:
            check_cmd = config.get("check", [config["cmd"][0], "--version"])
            result = subprocess.run(
                check_cmd, capture_output=True, timeout=5,
                shell=is_windows,  # Windows needs shell=True for .cmd
            )
            if result.returncode == 0:
                available.append(name)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
    return available


def call_cli(agent_name: str, full_prompt: str) -> str:
    """Call a CLI agent as subprocess. Returns response text."""
    config = CLI_AGENTS.get(agent_name)
    if not config:
        return ""

    # API-based agent (Devstral via OpenRouter)
    if config.get("cmd") is None:
        return _call_api(config, full_prompt)

    # CLI-based agent (kimi, opencode, claude, qwen, codex, copilot)
    import platform
    is_windows = platform.system() == "Windows"

    cmd = []
    for part in config["cmd"]:
        if part == "{prompt}":
            cmd.append(full_prompt)
        else:
            cmd.append(part)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=config.get("timeout", 120),
            shell=is_windows,  # Windows needs shell=True for .cmd wrappers
            env={**os.environ, "TERM": "dumb", "PYTHONIOENCODING": "utf-8"},
        )
        output = result.stdout.strip()
        if not output and result.stderr:
            output = result.stderr.strip()
        return output
    except subprocess.TimeoutExpired:
        print(f"    [{agent_name}] TIMEOUT ({config['timeout']}s)", file=sys.stderr)
        return ""
    except FileNotFoundError:
        print(f"    [{agent_name}] CLI not found", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"    [{agent_name}] failed: {e}", file=sys.stderr)
        return ""


def _call_api(config: dict, prompt: str) -> str:
    """Call API-based agent (OpenRouter/Devstral)."""
    import urllib.request

    api_key = os.environ.get(config.get("api_key_env", ""), "")
    if not api_key:
        return ""

    try:
        payload = json.dumps({
            "model": config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.3,
        }).encode("utf-8")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ai-engineering.at",
            "X-Title": "meta-skills-autoreason",
        }

        req = urllib.request.Request(
            config["api_url"], data=payload, headers=headers, method="POST",
        )
        with urllib.request.urlopen(req, timeout=config.get("timeout", 120)) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"    [devstral-api] failed: {e}", file=sys.stderr)
        return ""


def get_available_judges() -> list:
    """Get list of available CLI agents for judging, ordered by priority."""
    available = detect_available_clis()
    # Sort by priority order
    ordered = [a for a in JUDGE_PRIORITY if a in available]
    # Add any available agents not in priority list
    for a in available:
        if a not in ordered:
            ordered.append(a)
    return ordered


def call_llm_role(role: str, system: str, prompt: str) -> str:
    """Call LLM with role-based agent selection for cross-model diversity.

    Uses CLI tools (kimi, qwen, codex, copilot, opencode, claude) as subprocesses.
    System prompt is prepended to user prompt (CLIs don't have separate system param).
    Judges rotate through ALL available CLIs for maximum diversity.
    """
    available = detect_available_clis()

    # Determine which agent to use
    if role.startswith("judge_"):
        judges = get_available_judges()
        if not judges:
            return ""
        idx = int(role.split("_")[1]) % len(judges)
        agent_name = judges[idx]
    else:
        agent_name = ROLE_AGENTS.get(role, "claude")
        # Fallback if preferred agent not available
        if agent_name not in available:
            if available:
                agent_name = available[0]
            else:
                return ""

    # Combine system + prompt (CLI tools get one input)
    full_prompt = f"{system}\n\n---\n\n{prompt}"

    # Try preferred agent, fallback to next available on failure
    result = call_cli(agent_name, full_prompt)
    if result:
        vendor = CLI_AGENTS.get(agent_name, {}).get("vendor", "?")
        print(f"    [{agent_name}] ({vendor}) OK ({len(result)} chars)")
        return result

    # Fallback: try other available agents
    for fallback in available:
        if fallback != agent_name:
            result = call_cli(fallback, full_prompt)
            if result:
                vendor = CLI_AGENTS.get(fallback, {}).get("vendor", "?")
                print(f"    [{fallback}] ({vendor}) OK ({len(result)} chars) [fallback]")
                return result

    return ""


# Legacy compatibility
def call_llm(system: str, prompt: str, model: str = "haiku") -> str:
    """Legacy wrapper -- routes to call_llm_role."""
    return call_llm_role("critic", system, prompt)


CONFIDENCE_WEIGHTS = {"high": 1.0, "medium": 0.7, "low": 0.4}


def parse_ranking(judge_response: str) -> tuple:
    """Extract ranking + confidence from judge response.
    Returns (ranking_list, confidence_str).
    ranking_list = [best, second, worst] version numbers.
    confidence_str = "high" | "medium" | "low".
    """
    import re

    # Extract confidence
    confidence = "medium"  # default
    conf_match = re.search(r"CONFIDENCE:\s*\[?\s*(high|medium|low)\s*\]?", judge_response, re.IGNORECASE)
    if conf_match:
        confidence = conf_match.group(1).lower()

    # Extract ranking — handles [2], [1], [3] and 2, 1, 3 and [2] [1] [3]
    # Find all digits 1-3 after "RANKING:" (within 100 chars)
    ranking_section = ""
    rank_start = re.search(r"RANKING:", judge_response, re.IGNORECASE)
    if rank_start:
        ranking_section = judge_response[rank_start.end():rank_start.end() + 100]
        digits = re.findall(r"([123])", ranking_section)
        if len(digits) >= 3:
            seen = []
            for d in digits:
                if int(d) not in seen:
                    seen.append(int(d))
                if len(seen) == 3:
                    return seen, confidence

    # Fallback: look for any 3 unique digits 1-3 in last 200 chars
    numbers = re.findall(r"([123])", judge_response[-200:])
    if len(numbers) >= 3:
        seen = []
        for n in numbers:
            if int(n) not in seen:
                seen.append(int(n))
            if len(seen) == 3:
                return seen, confidence
    return [1, 2, 3], confidence  # Default: incumbent wins


def borda_count(rankings: list, confidences: list = None) -> tuple:
    """Given list of rankings from judges, return (winner, verdict, consensus_score).

    Borda: 1st place = 2pts, 2nd = 1pt, 3rd = 0pt.
    With confidence weighting: points * confidence_weight.

    Verdict levels (MCO pattern: agreement_ratio * avg_confidence):
      confirmed         = all judges agree on winner AND avg confidence >= 0.8
      needs-verification = majority agrees but mixed confidence
      unverified        = no clear winner or low confidence
    """
    if confidences is None:
        confidences = ["medium"] * len(rankings)

    scores = {1: 0.0, 2: 0.0, 3: 0.0}
    for ranking, conf in zip(rankings, confidences):
        weight = CONFIDENCE_WEIGHTS.get(conf, 0.7)
        for i, version in enumerate(ranking):
            scores[version] += (2 - i) * weight

    winner = max(scores, key=scores.get)

    # Calculate consensus metrics
    avg_confidence = sum(CONFIDENCE_WEIGHTS.get(c, 0.7) for c in confidences) / max(len(confidences), 1)
    first_place_votes = sum(1 for r in rankings if r[0] == winner)
    agreement_ratio = first_place_votes / max(len(rankings), 1)
    consensus_score = agreement_ratio * avg_confidence

    # Verdict
    if consensus_score >= 0.8:
        verdict = "confirmed"
    elif consensus_score >= 0.5:
        verdict = "needs-verification"
    else:
        verdict = "unverified"

    return winner, verdict, consensus_score


def autoreason_one_skill(skill_path: Path, max_passes: int = MAX_PASSES, dry_run: bool = False) -> dict:
    """Run autoreason on a single SKILL.md file."""
    skill_name = skill_path.parent.name
    print(f"\n{'='*60}")
    print(f"AUTOREASON: {skill_name}")
    print(f"{'='*60}")

    # Read incumbent
    incumbent = skill_path.read_text(encoding="utf-8")
    initial_eval = run_eval(skill_path)
    print(f"  Initial score: {initial_eval.get('score', '?')}")

    # Check which CLI agents are available
    available_clis = detect_available_clis()
    has_llm = len(available_clis) > 0
    if available_clis:
        print(f"  Available agents: {', '.join(available_clis)}")
    else:
        print(f"  No CLI agents found (kimi, opencode, claude) and no API keys")

    if not has_llm:
        print("  No ANTHROPIC_API_KEY -- running eval-only mode (no LLM refinement)")
        return {
            "skill": skill_name,
            "mode": "eval-only",
            "initial_score": initial_eval.get("score", -1),
            "final_score": initial_eval.get("score", -1),
            "passes": 0,
            "converged": True,
            "changes": [],
        }

    version_a = incumbent
    consecutive_a_wins = 0
    changes = []

    for pass_num in range(1, max_passes + 1):
        print(f"\n  --- Pass {pass_num}/{max_passes} ---")

        # Step 1: Critic (Kimi -- good at finding issues)
        print(f"  Critic analyzing...")
        critique = call_llm_role(
            "critic",
            CRITIC_SYSTEM,
            CRITIC_PROMPT.format(skill_content=version_a),
        )
        if not critique:
            print(f"  Critic failed, stopping.")
            break

        # Step 2: Author B (Devstral -- good at code revision)
        print(f"  Author B revising...")
        version_b = call_llm_role(
            "author_b",
            AUTHOR_B_SYSTEM,
            AUTHOR_B_PROMPT.format(skill_content=version_a, critique=critique),
        )
        if not version_b:
            print(f"  Author B failed, stopping.")
            break

        # Step 3: Synthesizer (Sonnet -- best synthesis quality)
        print(f"  Synthesizer combining...")
        import random
        if random.random() > 0.5:
            version_ab = call_llm_role(
                "synthesizer",
                SYNTHESIZER_SYSTEM,
                SYNTHESIZER_PROMPT.format(version_x=version_a, version_y=version_b),
            )
        else:
            version_ab = call_llm_role(
                "synthesizer",
                SYNTHESIZER_SYSTEM,
                SYNTHESIZER_PROMPT.format(version_x=version_b, version_y=version_a),
            )
        if not version_ab:
            version_ab = version_b  # Fallback: use B if synth fails

        # Step 4: Cross-model judge panel (N judges from different CLI tools)
        # Maximum diversity = minimum blind spots
        judges = get_available_judges()
        num_j = min(NUM_JUDGES, len(judges))
        judge_names = [judges[i % len(judges)] for i in range(num_j)]
        print(f"  {num_j} Cross-Model Judges ranking ({' + '.join(judge_names)})...")
        versions = {1: version_a, 2: version_b, 3: version_ab}

        rankings = []
        confidences = []
        for judge_idx in range(num_j):
            order = list(versions.keys())
            random.shuffle(order)
            reverse_map = {"1": order[0], "2": order[1], "3": order[2]}

            judge_response = call_llm_role(
                f"judge_{judge_idx}",
                JUDGE_SYSTEM,
                JUDGE_PROMPT.format(
                    version_1=versions[order[0]][:3000],
                    version_2=versions[order[1]][:3000],
                    version_3=versions[order[2]][:3000],
                ),
            )
            if judge_response:
                raw_ranking, confidence = parse_ranking(judge_response)
                true_ranking = [reverse_map.get(str(r), r) for r in raw_ranking]
                rankings.append(true_ranking)
                confidences.append(confidence)

        if not rankings:
            print(f"  All judges failed, stopping.")
            break

        winner, verdict, consensus_score = borda_count(rankings, confidences)
        version_names = {1: "A (incumbent)", 2: "B (revision)", 3: "AB (synthesis)"}
        conf_summary = ", ".join(f"{c}" for c in confidences)
        print(f"  Winner: {version_names.get(winner, '?')} [{verdict}] "
              f"(consensus={consensus_score:.2f}, confidence=[{conf_summary}])")

        if winner == 1:
            consecutive_a_wins += 1
            print(f"  Incumbent wins ({consecutive_a_wins}/{CONVERGENCE_K} for convergence)")

            # P3: Orthogonal Revision — try Author C before converging
            if consecutive_a_wins == 1 and pass_num < max_passes:
                print(f"\n  --- ORTHOGONAL PASS (Author C) ---")
                print(f"  Previous revision lost. Trying COMPLETELY DIFFERENT approach...")

                version_c = call_llm_role(
                    "author_b",  # reuse author slot, different prompt
                    AUTHOR_C_SYSTEM,
                    AUTHOR_C_PROMPT.format(
                        skill_content=version_a,
                        critique=critique,
                        failed_revision_summary=version_b[:500] if version_b else "N/A",
                    ),
                )

                if version_c:
                    # Judge A vs C (2-way comparison using 3-slot format)
                    print(f"  Judging A vs C (orthogonal)...")
                    versions_c = {1: version_a, 2: version_c, 3: version_c}  # C in both 2+3 slots
                    rankings_c = []
                    confidences_c = []
                    for judge_idx in range(num_j):
                        order = list(versions_c.keys())
                        random.shuffle(order)
                        reverse_map_c = {"1": order[0], "2": order[1], "3": order[2]}
                        jr = call_llm_role(
                            f"judge_{judge_idx}",
                            JUDGE_SYSTEM,
                            JUDGE_PROMPT.format(
                                version_1=versions_c[order[0]][:3000],
                                version_2=versions_c[order[1]][:3000],
                                version_3=versions_c[order[2]][:3000],
                            ),
                        )
                        if jr:
                            rr, cc = parse_ranking(jr)
                            tr = [reverse_map_c.get(str(r), r) for r in rr]
                            rankings_c.append(tr)
                            confidences_c.append(cc)

                    if rankings_c:
                        winner_c, verdict_c, score_c = borda_count(rankings_c, confidences_c)
                        print(f"  Orthogonal result: {'A wins again' if winner_c == 1 else 'C wins!'} "
                              f"[{verdict_c}] (consensus={score_c:.2f})")

                        if winner_c != 1:
                            # C wins — recombine B + C into D
                            print(f"  Recombining B + C into D...")
                            version_d = call_llm_role(
                                "synthesizer",
                                RECOMBINE_SYSTEM,
                                RECOMBINE_PROMPT.format(
                                    version_b=version_b[:2000] if version_b else "",
                                    version_c=version_c[:2000],
                                ),
                            )
                            if version_d:
                                consecutive_a_wins = 0
                                version_a = version_d
                                changes.append({
                                    "pass": pass_num,
                                    "winner": "D (recombined B+C)",
                                    "verdict": verdict_c,
                                    "consensus_score": round(score_c, 2),
                                    "confidences": confidences_c,
                                    "critique_summary": f"Orthogonal: {critique[:100]}",
                                })
                                print(f"  New incumbent: D (recombined B+C)")
                                continue
                            else:
                                # Recombine failed, use C directly
                                consecutive_a_wins = 0
                                version_a = version_c
                                changes.append({
                                    "pass": pass_num,
                                    "winner": "C (orthogonal)",
                                    "verdict": verdict_c,
                                    "consensus_score": round(score_c, 2),
                                    "confidences": confidences_c,
                                    "critique_summary": f"Orthogonal: {critique[:100]}",
                                })
                                print(f"  New incumbent: C (orthogonal)")
                                continue
                        else:
                            # A wins against C too — now it's 2 consecutive
                            consecutive_a_wins = 2
                            print(f"  A wins orthogonal too ({consecutive_a_wins}/{CONVERGENCE_K})")

            if consecutive_a_wins >= CONVERGENCE_K:
                print(f"  CONVERGED -- incumbent is good enough.")
                break
        else:
            consecutive_a_wins = 0
            version_a = versions[winner]
            changes.append({
                "pass": pass_num,
                "winner": version_names.get(winner, "?"),
                "verdict": verdict,
                "consensus_score": round(consensus_score, 2),
                "confidences": confidences,
                "critique_summary": critique[:200],
            })
            print(f"  New incumbent: {version_names.get(winner, '?')}")

    # Final eval
    final_content = version_a
    if final_content != incumbent and not dry_run:
        skill_path.write_text(final_content, encoding="utf-8")
        print(f"\n  SKILL.md UPDATED")
    elif dry_run and final_content != incumbent:
        print(f"\n  DRY RUN -- would update SKILL.md")

    final_eval = run_eval(skill_path)

    result = {
        "skill": skill_name,
        "mode": "autoreason",
        "initial_score": initial_eval.get("score", -1),
        "final_score": final_eval.get("score", -1),
        "passes": pass_num if 'pass_num' in dir() else 0,
        "converged": consecutive_a_wins >= CONVERGENCE_K,
        "changes": changes,
    }

    delta = result["final_score"] - result["initial_score"]
    print(f"\n  Score: {result['initial_score']} -> {result['final_score']} ({'+' if delta >= 0 else ''}{delta})")
    print(f"  Converged: {result['converged']}")
    print(f"  Changes: {len(changes)}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Autoreason for Skills")
    parser.add_argument("skill_path", nargs="?", help="Path to SKILL.md")
    parser.add_argument("--all", action="store_true", help="Run on all skills")
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes")
    parser.add_argument("--max-passes", type=int, default=MAX_PASSES, help=f"Max passes (default: {MAX_PASSES})")

    args = parser.parse_args()

    if not args.skill_path and not args.all:
        parser.print_help()
        sys.exit(1)

    # Collect targets
    targets = []
    if args.all:
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            sf = skill_dir / "SKILL.md"
            if sf.exists():
                targets.append(sf)
    else:
        targets.append(Path(args.skill_path))

    if not targets:
        print("No skills found.")
        sys.exit(1)

    print(f"Autoreason: {len(targets)} skill(s)")
    print(f"Max passes: {args.max_passes}")
    print(f"Convergence: A must win {CONVERGENCE_K}x consecutively")
    if args.dry_run:
        print("DRY RUN -- no files will be modified")

    # Run
    results = []
    for target in targets:
        result = autoreason_one_skill(target, max_passes=args.max_passes, dry_run=args.dry_run)
        results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print(f"AUTOREASON SUMMARY")
    print(f"{'='*60}")
    print(f"Skills processed: {len(results)}")

    improved = [r for r in results if r["final_score"] > r["initial_score"]]
    converged = [r for r in results if r["converged"]]
    changed = [r for r in results if r["changes"]]

    print(f"Improved: {len(improved)}")
    print(f"Converged: {len(converged)}")
    print(f"Changed: {len(changed)}")

    for r in results:
        delta = r["final_score"] - r["initial_score"]
        status = "CONVERGED" if r["converged"] else f"{len(r['changes'])} changes"
        print(f"  {r['skill']:25s} {r['initial_score']:3d} -> {r['final_score']:3d} ({'+' if delta >= 0 else ''}{delta:+d}) [{status}]")

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    results_file = RESULTS_DIR / f"autoreason-{now}.json"
    results_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults saved: {results_file}")


if __name__ == "__main__":
    main()
