"""usage_core.py — der eine Rechenkern für Claude-Code-Nutzungsdaten.

Warum diese Datei existiert (2026-07-26): es gab drei Implementierungen derselben
Größe — Statusleiste, LLM-Bridge, Ad-hoc-Scans — mit drei verschiedenen
Ergebnissen (Faktor bis 2,8), und niemand hat sie gegeneinander geprüft. Dieser
Modul ist die gemeinsame Quelle. Wer eine Nutzungszahl braucht, ruft hier an.

Drei Fakten, die dieses Modul erzwingt — jeder war ein Fehler, der Geld und
Vertrauen gekostet hat:

1. **Dedup ist Pflicht.** Claude Code schreibt eine Assistant-Nachricht während
   des Streamings mehrfach ins Transkript (bis zu 42× beobachtet). Die Zeilen
   sind *Schnappschüsse*, keine Deltas: ``cache_creation`` ist auf allen Zeilen
   identisch, ``output_tokens`` wächst. Summieren zählt denselben Cache-Write
   dutzendfach. Dedup-Schlüssel ist ``requestId`` (ein API-Request = ein
   Usage-Block), Fallback ``message.id``; die letzte Zeile gewinnt, weil sie die
   vollständige ist. Messung 2026-07-26: ohne Dedup 232,2 M in+out, mit Dedup
   95,3 M — 59 % waren Duplikate.

2. **Cache-Token dominieren.** ``input + output`` ist nicht das Volumen. Über
   67 Tage: 95,3 M in+out gegen 10,71 Mrd. Cache-Token. Wer nur in+out zeigt,
   zeigt 0,9 % des Verbrauchs — genau deshalb hat die Leiste monatelang eine
   Größenordnung zu klein angezeigt.

3. **Kosten sind aus Token NICHT ableitbar.** Gegen Anthropics eigenen
   ``cost.total_cost_usd`` lag die Token-Preisrechnung bei 63 % (Sonnet-5-Session)
   bzw. 140 % (Opus-5[1m]-Session) — kein systematischer Faktor, und die
   Transkripte enthalten kein Kostenfeld. Deshalb liefert ``price_usage`` eine
   *Zwischengröße* für die Kalibrierung, nie eine Kostenwahrheit. Wahrheit ist
   ``cost.total_cost_usd`` pro Session; siehe ``calibration_factors``.

Keine Netzwerkzugriffe, keine Subprozesse, nur Lesen. Python ≥ 3.11.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator

# ═══════════════════════════════════════════════════════════════
# PREISE — Zwischengröße für die Kalibrierung, keine Kostenwahrheit
# ═══════════════════════════════════════════════════════════════
# $/1M Token. Quelle: claude-api-Skill (platform.claude.com Pricing),
# verifiziert 2026-07-26. cache_read = 0,1 × input; cache_write_5m = 1,25 ×
# input; cache_write_1h = 2,0 × input.
#
# Die Transkripte unterscheiden 5m/1h nur, wenn ``cache_creation`` als Objekt
# mit ``ephemeral_5m_input_tokens``/``ephemeral_1h_input_tokens`` vorliegt.
# Fehlt der Split, wird der Aggregatwert als 5m gewertet — die günstigere
# Variante, also die konservative Richtung (nie eine unbelegte Zahl nach oben
# treiben; A33).
MODEL_PRICES: dict[str, dict[str, float]] = {
    # Opus-Tier
    "opus-5": {"input": 5.00, "output": 25.00},
    "opus-4.8": {"input": 5.00, "output": 25.00},
    "opus-4.7": {"input": 5.00, "output": 25.00},
    "opus-4.6": {"input": 5.00, "output": 25.00},
    "opus-4.5": {"input": 5.00, "output": 25.00},
    # Sonnet-Tier. Sonnet-5 hat Einführungspreise ($2/$10) bis 2026-08-31;
    # danach $3/$15. Hier steht der Listenpreis, weil die Kalibrierung die
    # Differenz ohnehin auffängt — ein Einführungspreis-Fehler würde sonst
    # doppelt korrigiert.
    "sonnet-5": {"input": 3.00, "output": 15.00},
    "sonnet-4.6": {"input": 3.00, "output": 15.00},
    "sonnet-4.5": {"input": 3.00, "output": 15.00},
    # Haiku-Tier
    "haiku-4.5": {"input": 1.00, "output": 5.00},
    # Fable/Mythos-Tier
    "fable-5": {"input": 10.00, "output": 50.00},
    "mythos-5": {"input": 10.00, "output": 50.00},
}

# Unbekannte Modell-ID → Opus-Tarif. Konservativ nach oben, damit eine neue
# Modellgeneration nicht still als "kostenlos" durchläuft (der Fehler, der
# ``costUSD: 0`` zu "keine Kostendaten" gemacht hat). Der Aufrufer erfährt es
# über ``unknown_models``.
FALLBACK_PRICE_KEY = "opus-5"

CACHE_READ_FACTOR = 0.1
CACHE_WRITE_5M_FACTOR = 1.25
CACHE_WRITE_1H_FACTOR = 2.0


def normalize_model(model_id: str | None) -> str | None:
    """``claude-opus-4-8`` → ``opus-4.8``; ``claude-opus-5[1m]`` → ``opus-5``.

    Der ``[1m]``-Suffix ist Claude Codes Anzeige für das 1M-Kontextfenster und
    kein eigener Tarif (Opus 4.7+ haben laut Pricing keinen Long-Context-
    Aufschlag). Datums-Suffixe (``-20251001``) fallen weg.

    Gibt ``None`` für Nicht-Modelle wie ``<synthetic>`` oder ``unknown``, damit
    der Aufrufer sie ehrlich als unbepreisbar behandeln kann statt sie mit einem
    Fantasietarif zu belegen.
    """
    if not model_id:
        return None
    m = str(model_id).strip().lower()
    if m.startswith("<") or m in ("unknown", ""):
        return None
    m = m.split("[", 1)[0]  # [1m]-Suffix
    if m.startswith("claude-"):
        m = m[len("claude-") :]
    parts = m.split("-")
    if not parts:
        return None
    family = parts[0]
    nums = [p for p in parts[1:] if p.isdigit()]
    if not nums:
        return family or None
    # Datums-Suffix (8 Stellen) verwerfen: haiku-4-5-20251001 → haiku-4.5
    nums = [n for n in nums if len(n) < 8] or nums[:1]
    version = nums[0] if len(nums) == 1 else f"{nums[0]}.{nums[1]}"
    return f"{family}-{version}"


def price_for(model_id: str | None) -> tuple[dict[str, float] | None, bool]:
    """→ ``(preise, war_fallback)``. ``(None, False)`` für Nicht-Modelle."""
    key = normalize_model(model_id)
    if key is None:
        return None, False
    if key in MODEL_PRICES:
        return MODEL_PRICES[key], False
    return MODEL_PRICES[FALLBACK_PRICE_KEY], True


def split_usage(usage: dict[str, Any]) -> tuple[int, int, int, int, int]:
    """→ ``(input, output, cache_read, cache_write_5m, cache_write_1h)``.

    ``cache_creation`` als Objekt liefert den 5m/1h-Split; fehlt es, gilt der
    Aggregatwert ``cache_creation_input_tokens`` als 5m (siehe MODEL_PRICES).
    """
    inp = int(usage.get("input_tokens") or 0)
    out = int(usage.get("output_tokens") or 0)
    cread = int(usage.get("cache_read_input_tokens") or 0)
    creation = usage.get("cache_creation")
    if isinstance(creation, dict) and creation:
        w5 = int(creation.get("ephemeral_5m_input_tokens") or 0)
        w1 = int(creation.get("ephemeral_1h_input_tokens") or 0)
    else:
        w5 = int(usage.get("cache_creation_input_tokens") or 0)
        w1 = 0
    return inp, out, cread, w5, w1


def price_usage(usage: dict[str, Any], model_id: str | None) -> float | None:
    """Token-gepreiste Kosten in USD, oder ``None`` wenn nicht bepreisbar.

    **Keine Kostenwahrheit** — siehe Modul-Docstring Punkt 3. Nur als
    Zwischengröße für ``calibration_factors`` und für die Rekonstruktion
    historischer Fenster, in denen kein echter Kostenwert existiert.
    """
    prices, _ = price_for(model_id)
    if prices is None:
        return None
    inp, out, cread, w5, w1 = split_usage(usage)
    pin = prices["input"]
    return (
        inp * pin
        + out * prices["output"]
        + cread * pin * CACHE_READ_FACTOR
        + w5 * pin * CACHE_WRITE_5M_FACTOR
        + w1 * pin * CACHE_WRITE_1H_FACTOR
    ) / 1_000_000


# ═══════════════════════════════════════════════════════════════
# TRANSKRIPT-LESER
# ═══════════════════════════════════════════════════════════════
DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"

_ASSISTANT_MARKERS = ('"type":"assistant"', '"type": "assistant"')


def iter_usage_records(path: Path) -> Iterator[dict[str, Any]]:
    """Assistant-Records **einer** Transkriptdatei, in Dateireihenfolge.

    Tolerant: unlesbare Datei → keine Records; kaputte Zeile → übersprungen.
    Nie eine Exception nach oben, weil die Statusleiste jede Sekunde rendert und
    ein einzelnes defektes Transkript sie nicht abschießen darf.
    """
    try:
        fh = path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            if not any(mk in line for mk in _ASSISTANT_MARKERS):
                continue
            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if obj.get("type") != "assistant":
                continue
            message = obj.get("message")
            if not isinstance(message, dict):
                continue
            usage = message.get("usage")
            if not isinstance(usage, dict):
                continue
            yield {
                "key": obj.get("requestId") or message.get("id") or obj.get("uuid"),
                "session_id": obj.get("sessionId") or path.stem,
                "is_sidechain": bool(obj.get("isSidechain")),
                "model": message.get("model"),
                "timestamp": obj.get("timestamp"),
                "usage": usage,
            }


class Totals:
    """Additiver Sammler. Hält Token getrennt nach Art, damit niemand mehr
    ``total_tokens`` schreiben kann und in+out meinen (die Namensfalle, die in
    Leiste *und* Bridge steckte)."""

    __slots__ = ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h",
                 "priced_usd", "records", "unpriceable_records")

    def __init__(self) -> None:
        self.input = self.output = self.cache_read = 0
        self.cache_write_5m = self.cache_write_1h = 0
        self.priced_usd = 0.0
        self.records = 0
        self.unpriceable_records = 0

    def add(self, usage: dict[str, Any], model_id: str | None) -> None:
        inp, out, cread, w5, w1 = split_usage(usage)
        self.input += inp
        self.output += out
        self.cache_read += cread
        self.cache_write_5m += w5
        self.cache_write_1h += w1
        self.records += 1
        cost = price_usage(usage, model_id)
        if cost is None:
            self.unpriceable_records += 1
        else:
            self.priced_usd += cost

    @property
    def tokens_io(self) -> int:
        return self.input + self.output

    @property
    def tokens_cache(self) -> int:
        return self.cache_read + self.cache_write_5m + self.cache_write_1h

    @property
    def tokens_all(self) -> int:
        return self.tokens_io + self.tokens_cache

    @property
    def cache_hit_ratio(self) -> float | None:
        """Anteil der input-seitigen Token, die aus dem Cache kamen.

        ``None`` wenn es keine input-seitigen Token gibt (frische Session) —
        statt einer irreführenden 0 %.
        """
        denom = self.input + self.cache_read + self.cache_write_5m + self.cache_write_1h
        return (self.cache_read / denom) if denom else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "input": self.input,
            "output": self.output,
            "cache_read": self.cache_read,
            "cache_write_5m": self.cache_write_5m,
            "cache_write_1h": self.cache_write_1h,
            "tokens_io": self.tokens_io,
            "tokens_cache": self.tokens_cache,
            "tokens_all": self.tokens_all,
            "priced_usd": self.priced_usd,
            "records": self.records,
            "unpriceable_records": self.unpriceable_records,
            "cache_hit_ratio": self.cache_hit_ratio,
        }


def dedup_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Schnappschuss-Duplikate entfernen — letzte Zeile gewinnt.

    Siehe Modul-Docstring Punkt 1. Records ohne Dedup-Schlüssel bleiben
    einzeln erhalten (lieber ein Record zu viel als einer verworfen, dessen
    Zugehörigkeit unklar ist).
    """
    out: dict[Any, dict[str, Any]] = {}
    keyless: list[dict[str, Any]] = []
    for rec in records:
        if rec["key"] is None:
            keyless.append(rec)
        else:
            out[rec["key"]] = rec
    return list(out.values()) + keyless
