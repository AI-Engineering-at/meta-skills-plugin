#!/usr/bin/env python3
"""usage_aggregate.py — baut das Nutzungs-Aggregat, das die Statusleiste liest.

Warum getrennt von ``statusline.py``: der Vollscan über ``~/.claude/projects``
(2.612 Dateien, ~1 GB) dauert Minuten. Die Leiste rendert jede Sekunde. Sie darf
diesen Scan also **nie** selbst fahren — sie liest nur das Ergebnis.

Ablauf:
  1. Pro Transkriptdatei: dedupliziertes Token-Total (siehe usage_core, Punkt 1).
     Ergebnis wird in einem Datei-Cache mit ``(size, mtime)`` gehalten —
     unveränderte Datei = kein erneutes Lesen. Erst-Lauf Minuten, danach Sekunden.
  2. Kalibrierung: für Sessions, die die Leiste **vollständig** beobachtet hat,
     liegt Anthropics echter ``cost.total_cost_usd`` vor. Faktor =
     echte Kosten / token-gepreiste Kosten. Das ist die einzige Brücke zwischen
     Token und Kostenwahrheit (usage_core, Punkt 3).
  3. Rekonstruktion auf ``accountCreatedAt``: gemessene Rate × Lücke davor.
     ``real`` und ``estimated`` bleiben getrennt — die Grenze muss sichtbar sein.

Aufruf:
  python3 usage_aggregate.py            # refresh wenn älter als MAX_AGE_H
  python3 usage_aggregate.py --force    # immer neu
  python3 usage_aggregate.py --show     # Aggregat ausgeben, nichts rechnen
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import usage_core as U  # noqa: E402

AGG_FILE = Path("~/.claude/statusline-usage-agg.json").expanduser()
FILECACHE = Path("~/.claude/statusline-usage-filecache.json").expanduser()
ALLTIME = Path("~/.claude/statusline-alltime.json").expanduser()
ASSUMPTIONS = Path("~/.claude/statusline-assumptions.json").expanduser()
CLAUDE_JSON = Path("~/.claude.json").expanduser()

MAX_AGE_H = 6.0
# Eine Session taugt nur als Kalibrier-Referenz, wenn die Leiste sie
# vollständig gesehen hat. Test: Hook-Dauer ~ Transkript-Spanne. Gemessen
# 2026-07-26: Session 4e56a2b8 3,26 h vs 3,26 h (gültig) gegen 2ab1310f
# 39,9 h vs 29,6 h (ungültig — nur teilweise beobachtet, ihr Kostenwert ist
# unvollständig und ergab einen um 62 % verzerrten Faktor).
CALIB_SPAN_TOLERANCE = 0.25


def _load_json(path: Path, default: Any) -> Any:
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError, ValueError):
        return default


def _atomic_write(path: Path, payload: Any) -> None:
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, separators=(",", ":"))
        tmp.replace(path)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass


def load_assumptions(path: Path = ASSUMPTIONS) -> dict[str, Any]:
    """Annahmen laden — Einträge **ohne** ``stand`` + ``quelle`` werden verworfen.

    Das ist die Lehre aus der Handkonstante: ein Wert ohne Herkunft ist kein
    Wert. Verworfene Einträge tauchen in ``_rejected`` auf, damit das Verwerfen
    sichtbar ist statt still.
    """
    raw = _load_json(path, {})
    out: dict[str, Any] = {}
    rejected: list[str] = []
    for key, entry in (raw.items() if isinstance(raw, dict) else []):
        if key.startswith("_"):  # _readme u. Ä. sind Kommentare, keine Annahmen
            continue
        if not isinstance(entry, dict) or "value" not in entry:
            rejected.append(key)
            continue
        if not entry.get("stand") or not entry.get("quelle"):
            rejected.append(key)
            continue
        out[key] = entry
    out["_rejected"] = rejected
    return out


def read_account_created(path: Path = CLAUDE_JSON) -> datetime | None:
    cfg = _load_json(path, {})
    raw = ((cfg.get("oauthAccount") or {}) if isinstance(cfg, dict) else {}).get("accountCreatedAt")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


# ═══════════════════════════════════════════════════════════════
# SCAN mit Datei-Cache
# ═══════════════════════════════════════════════════════════════
def _file_totals(path: Path) -> dict[str, Any]:
    """Dedupliziertes Total **einer** Datei, pro Modell-Key, plus Zeitfenster."""
    per_model: dict[str, U.Totals] = {}
    tmin = tmax = None
    for rec in U.dedup_records(list(U.iter_usage_records(path))):
        key = U.normalize_model(rec["model"]) or "<unpriceable>"
        per_model.setdefault(key, U.Totals()).add(rec["usage"], rec["model"])
        ts = rec.get("timestamp")
        if ts:
            if tmin is None or ts < tmin:
                tmin = ts
            if tmax is None or ts > tmax:
                tmax = ts
    return {
        "per_model": {k: v.as_dict() for k, v in per_model.items()},
        "ts_min": tmin,
        "ts_max": tmax,
    }


def scan(projects_dir: Path | None = None) -> dict[str, Any]:
    projects = projects_dir or U.DEFAULT_PROJECTS_DIR
    cache = _load_json(FILECACHE, {})
    if not isinstance(cache, dict):
        cache = {}
    new_cache: dict[str, Any] = {}

    agg: dict[str, dict[str, int | float]] = {}
    tmin = tmax = None
    files = reused = rescanned = 0

    for path in sorted(projects.glob("**/*.jsonl")):
        files += 1
        try:
            st = path.stat()
        except OSError:
            continue
        sig = f"{st.st_size}:{int(st.st_mtime)}"
        key = str(path)
        cached = cache.get(key)
        if isinstance(cached, dict) and cached.get("sig") == sig:
            entry = cached
            reused += 1
        else:
            entry = {"sig": sig, **_file_totals(path)}
            rescanned += 1
        new_cache[key] = entry

        for model, d in (entry.get("per_model") or {}).items():
            slot = agg.setdefault(model, {})
            for field in ("input", "output", "cache_read", "cache_write_5m",
                          "cache_write_1h", "priced_usd", "records",
                          "unpriceable_records"):
                slot[field] = slot.get(field, 0) + (d.get(field) or 0)
        for bound, cmp_lt in ((entry.get("ts_min"), True), (entry.get("ts_max"), False)):
            if not bound:
                continue
            if cmp_lt:
                if tmin is None or bound < tmin:
                    tmin = bound
            else:
                if tmax is None or bound > tmax:
                    tmax = bound

    _atomic_write(FILECACHE, new_cache)
    return {
        "per_model": agg,
        "ts_min": tmin,
        "ts_max": tmax,
        "files": files,
        "files_reused": reused,
        "files_rescanned": rescanned,
    }


# ═══════════════════════════════════════════════════════════════
# KALIBRIERUNG
# ═══════════════════════════════════════════════════════════════
def calibration(projects_dir: Path | None = None) -> dict[str, Any]:
    """Faktor = Anthropics echte Session-Kosten / token-gepreiste Kosten.

    Nur Sessions, deren Hook-Dauer zur Transkript-Spanne passt (siehe
    CALIB_SPAN_TOLERANCE) — sonst hat die Leiste die Session nur teilweise
    gesehen und ihr Kostenwert ist unvollständig.
    """
    projects = projects_dir or U.DEFAULT_PROJECTS_DIR
    stats = _load_json(ALLTIME, {})
    samples: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for sid, entry in (stats.items() if isinstance(stats, dict) else []):
        if sid.startswith("baseline-"):
            continue
        truth = entry.get("cost")
        hook_ms = entry.get("time_ms") or 0
        if not truth or truth <= 0 or hook_ms <= 0:
            continue

        recs: list[dict[str, Any]] = []
        for main in projects.glob(f"**/{sid}.jsonl"):
            recs.extend(U.iter_usage_records(main))
            for sub in sorted((main.parent / sid).glob("**/*.jsonl")):
                recs.extend(U.iter_usage_records(sub))
        if not recs:
            continue

        stamps = [r["timestamp"] for r in recs if r.get("timestamp")]
        if not stamps:
            continue
        try:
            span_h = (
                datetime.fromisoformat(max(stamps).replace("Z", "+00:00"))
                - datetime.fromisoformat(min(stamps).replace("Z", "+00:00"))
            ).total_seconds() / 3600.0
        except ValueError:
            continue
        hook_h = hook_ms / 3_600_000.0
        if span_h <= 0 or abs(hook_h - span_h) / max(hook_h, span_h) > CALIB_SPAN_TOLERANCE:
            skipped.append({"session": sid[:8], "hook_h": round(hook_h, 2),
                            "span_h": round(span_h, 2), "grund": "unvollstaendig beobachtet"})
            continue

        tot = U.Totals()
        for rec in U.dedup_records(recs):
            tot.add(rec["usage"], rec["model"])
        if tot.priced_usd <= 0:
            continue
        samples.append({"session": sid[:8], "truth_usd": round(truth, 2),
                        "priced_usd": round(tot.priced_usd, 2),
                        "factor": truth / tot.priced_usd,
                        "hook_h": round(hook_h, 2), "span_h": round(span_h, 2)})

    if samples:
        factor = sum(s["factor"] for s in samples) / len(samples)
    else:
        factor = 1.0
    return {"factor": factor, "n": len(samples), "samples": samples, "skipped": skipped}


# ═══════════════════════════════════════════════════════════════
# AGGREGAT
# ═══════════════════════════════════════════════════════════════
def build(projects_dir: Path | None = None, now_ts: float | None = None) -> dict[str, Any]:
    now_ts = now_ts if now_ts is not None else time.time()
    now = datetime.fromtimestamp(now_ts, tz=timezone.utc)
    scanned = scan(projects_dir)
    cal = calibration(projects_dir)
    assumptions = load_assumptions()

    tot = U.Totals()
    for d in scanned["per_model"].values():
        for field in ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h",
                      "records", "unpriceable_records"):
            setattr(tot, field, getattr(tot, field) + int(d.get(field) or 0))
        tot.priced_usd += float(d.get("priced_usd") or 0)

    real = tot.as_dict()
    real["usd_calibrated"] = real["priced_usd"] * cal["factor"]

    ts_min, ts_max = scanned["ts_min"], scanned["ts_max"]
    span_days = 0.0
    if ts_min and ts_max:
        try:
            span_days = (
                datetime.fromisoformat(ts_max.replace("Z", "+00:00"))
                - datetime.fromisoformat(ts_min.replace("Z", "+00:00"))
            ).total_seconds() / 86400.0
        except ValueError:
            span_days = 0.0

    acct = read_account_created()
    estimated: dict[str, Any] = {"tokens_all": 0, "usd": 0.0, "gap_days": 0.0, "grund": None}
    if acct is None:
        estimated["grund"] = "accountCreatedAt nicht lesbar"
    elif span_days <= 0:
        estimated["grund"] = "kein messbares Fenster"
    elif not ts_min:
        estimated["grund"] = "kein Fensterbeginn"
    else:
        first = datetime.fromisoformat(ts_min.replace("Z", "+00:00"))
        gap = (first - acct).total_seconds() / 86400.0
        if gap > 0:
            estimated["gap_days"] = gap
            estimated["tokens_all"] = int(real["tokens_all"] / span_days * gap)
            estimated["usd"] = real["usd_calibrated"] / span_days * gap
        else:
            estimated["grund"] = "Account-Anlage liegt im Messfenster"

    total_days = (now - acct).total_seconds() / 86400.0 if acct else span_days
    months = max(1, math.ceil(total_days / 30.44))
    sub_usd = 200.0 * months
    alltime_usd = real["usd_calibrated"] + estimated["usd"]

    return {
        "stand": now.isoformat(),
        "scope": "nur dieser Rechner (~/.claude/projects) — andere Hosts/Accounts nicht enthalten",
        "window": {"from": ts_min, "to": ts_max, "days": span_days,
                   "files": scanned["files"], "files_rescanned": scanned["files_rescanned"]},
        "real": real,
        "estimated": estimated,
        "alltime": {
            "days": total_days,
            "tokens_all": real["tokens_all"] + estimated["tokens_all"],
            "usd": alltime_usd,
            "subscription_usd": sub_usd,
            "saved_usd": alltime_usd - sub_usd,
            "months": months,
        },
        "calibration": cal,
        "per_model": scanned["per_model"],
        "assumptions": {k: v for k, v in assumptions.items() if k != "_rejected"},
        "assumptions_rejected": assumptions.get("_rejected", []),
    }


def is_stale(max_age_h: float = MAX_AGE_H, now_ts: float | None = None) -> bool:
    agg = _load_json(AGG_FILE, None)
    if not isinstance(agg, dict) or not agg.get("stand"):
        return True
    try:
        stand = datetime.fromisoformat(agg["stand"])
    except ValueError:
        return True
    now = datetime.fromtimestamp(now_ts if now_ts is not None else time.time(), tz=timezone.utc)
    return (now - stand).total_seconds() / 3600.0 > max_age_h


def main(argv: list[str]) -> int:
    if "--show" in argv:
        print(json.dumps(_load_json(AGG_FILE, {}), indent=1, ensure_ascii=False))
        return 0
    if "--force" not in argv and not is_stale():
        return 0
    payload = build()
    _atomic_write(AGG_FILE, payload)
    if "--quiet" not in argv:
        w, r, a, c = payload["window"], payload["real"], payload["alltime"], payload["calibration"]
        print(f"Fenster {str(w['from'])[:10]}..{str(w['to'])[:10]} = {w['days']:.1f} d "
              f"({w['files']} Dateien, {w['files_rescanned']} neu gelesen)")
        print(f"gemessen  {r['tokens_all']/1e9:.2f} Mrd Token  ${r['usd_calibrated']:,.0f}  "
              f"cache-hit {(r['cache_hit_ratio'] or 0)*100:.1f}%")
        print(f"seit Okt  {a['tokens_all']/1e9:.1f} Mrd Token  ${a['usd']:,.0f}  "
              f"gespart ${a['saved_usd']:,.0f}")
        print(f"Kalibrierung {c['factor']:.3f} (n={c['n']})"
              + (f", verworfen: {len(c['skipped'])}" if c["skipped"] else ""))
        if payload["assumptions_rejected"]:
            print(f"Annahmen ohne stand/quelle verworfen: {payload['assumptions_rejected']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
