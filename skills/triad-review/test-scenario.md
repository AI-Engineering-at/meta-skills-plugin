# Test Scenarios — Triad Review

## Test 1: Must spawn 3 specialized agents

**Input:** `/triad-review src/api/users.py`

**Pass criteria:**
- "THE BREAKER" Agent gestartet (haiku, background)
- "THE SNEAK" Agent gestartet (haiku, background)
- "THE SCALPEL" Agent gestartet (haiku, background)
- Alle 3 PARALLEL (nicht sequentiell)
- Jeder Agent hat unterschiedlichen Prompt

**Fail criteria:**
- `^same prompt` — alle Agents kriegen denselben Text
- `^sequential` — Agents werden nacheinander gestartet
- Nur 2 oder weniger Agents

---

## Test 2: Breaker findet Crash-Szenarien

**Input:** Code mit fehlender Null-Check:
```python
def get_user(user_id):
    db = connect()
    return db.query(f"SELECT * FROM users WHERE id = {user_id}")
```

**Pass criteria:**
- Breaker findet: `user_id = None` → TypeError oder SQL-Syntaxfehler
- Breaker findet: `user_id = ""` → leere WHERE-Klausel
- Konkrete Trigger-Inputs genannt (nicht "malicious input")
- Severity als BREAK/CORRUPT/DEGRADE klassifiziert

**Fail criteria:**
- `^style` oder `^naming` — Breaker kommentiert Style
- Keine konkreten Input-Werte
- Nur "could potentially" ohne spezifischen Trigger

---

## Test 3: Sneak findet Security-Lücken

**Input:** Obiger Code (SQL Injection)

**Pass criteria:**
- Sneak findet: `user_id = "1 OR 1=1--"` → SQL Injection
- Exakter Payload genannt
- Was der Angreifer gewinnt erklärt (alle Daten lesbar)
- Severity als EXPLOIT klassifiziert

**Fail criteria:**
- `^you should use parameterized` — nur Empfehlung ohne Finding
- `^good practice` — generischer Ratschlag
- Kein konkreter Payload

---

## Test 4: Scalpel findet Performance-Probleme

**Input:**
```python
def get_all_orders():
    users = db.query("SELECT * FROM users")
    for user in users:
        orders = db.query(f"SELECT * FROM orders WHERE user_id = {user.id}")
        user.orders = orders
    return users
```

**Pass criteria:**
- Scalpel findet: N+1 Query Pattern
- Trigger: "N users → N+1 queries"
- Impact: latency spike unter Last
- Severity: MELTDOWN bei hoher User-Zahl

**Fail criteria:**
- `^refactor` — nur Umbau-Empfehlung
- `^consider caching` — vager Vorschlag ohne konkretes Problem

---

## Test 5: Cross-Validation erkennt Überschneidungen

**Input:** Code wo Breaker UND Sneak dasselbe Problem finden:
```python
def execute(query):
    os.system(f"psql -c '{query}'")
```

**Pass criteria:**
- Breaker: `query = None` → Command Injection + Crash
- Sneak: `query = "'; DROP TABLE users;--"` → Command Injection
- Synthese markiert als CROSS-VALIDATED
- Höchste Priorität im Report

**Fail criteria:**
- Finding nur bei einem Angreifer
- Cross-Validation nicht erkannt

---

## Test 6: PoC-Validierung downgraded unrealistische Findings

**Input:** Breaker findet theoretisches Problem:
```
Line 42: Wenn user_id > 2^63, kann Integer Overflow passieren
```

**Pass criteria:**
- Validierung prüft: Kann user_id im echten Betrieb > 2^63 sein?
- Wenn DB als INT64 definiert → NEIN → THEORETICAL
- Severity downgraded, nicht gelöscht

**Fail criteria:**
- Finding einfach gelöscht
- Nicht begründet warum unrealistisch

---

## Test 7: Mitigated-Kategorie erkennt existierenden Schutz

**Input:**
```python
@app.route("/user/<id>")
@require_auth
def get_user(id):
    if not request.user.is_owner_or_admin(id):
        raise Forbidden()
    return db.get_user(id)
```

**Pass criteria:**
- Sneak könnte IDOR finden (direkter Objekt-Zugriff)
- Validierung erkennt: `@require_auth` + `is_owner_or_admin` existieren
- Kategorie: MITIGATED mit Restrisiko-Bewertung

**Fail criteria:**
- Finding als Critical markiert trotz Schutz
- Schutzmechanismen ignoriert

---

## Test 8: Re-Validierung OHNE neue Agents

**Input:** Nach Fix von SQL Injection:
```python
def get_user(user_id):
    return db.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

**Pass criteria:**
- Re-Validierung prüft statisch: `1 OR 1=1--` funktioniert nicht mehr
- Finding als RESOLVED markiert
- KEINE neuen Agent-Launches für diesen Fix

**Fail criteria:**
- `^launch.*breaker` oder `^launch.*sneak` — Agents neu gestartet
- `^approved` ohne statische PoC-Prüfung

---

## Test 9: Terminal States korrekt gesetzt

**Szenario A: 0 Critical, 0 High**
- Input: Sauberer Code
- Erwartet: Verdict = SECURE

**Szenario B: 2 Critical nach Fix round 1**
- Input: Criticals gefunden, gefixt, noch 1 Critical
- Erwartet: Verdict = PATCH NEEDED, nicht APPROVED

**Szenario C: 8 Critical, System unsicher**
- Input: Viele Criticals
- Erwartet: Verdict = ESCALATE

**Fail criteria (alle Szenarien):**
- Falscher Terminal State
- APPROVED vor vollständiger Prüfung

---

## Test 10: Verbotene Patterns nicht verwendet

**Input:** Beliebiger Code

**Pass criteria:**
- NONE der folgenden Phrasen im Output:
  - "looks good"
  - "consider refactoring"
  - "best practice would be"
  - "you might want to"
  - "generally recommended"
  - "clean code suggests"

**Fail criteria:**
- `^looks good` — oberflächliches Urteil
- `^refactor` — nicht im Scope
- `^best practice` — generischer Ratschlag
