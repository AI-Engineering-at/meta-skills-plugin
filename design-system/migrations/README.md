# migrations/

Eine Datei je MAJOR-Sprung. Namensschema: `<alt>-zu-<neu>.md`, z. B. `1.0.0-zu-2.0.0.md`.

## Warum das ein Gate ist und keine Bitte

`scripts/design-check.py --ci` **bricht**, wenn ein Projekt einen MAJOR-Sprung vor sich
hat und die passende Datei hier fehlt. Ein MAJOR ohne Migrationsanleitung ist keine
Version, sondern ein Bruch mit Ansage — und die Ansage fehlt dann auch noch.

## Was in so einer Datei steht

1. **Das Geruest kommt aus der Diff-Ausgabe** (`tdiff`, sonst der reduzierte
   Eigenvergleich). Entfernte, umbenannte und typgeaenderte Token werden aufgelistet,
   nicht abgetippt.
2. **Die Ersetzungsempfehlung schreibt ein Mensch.** Ein Werkzeug kann sagen, dass
   `state.alarm` weg ist. Es kann nicht sagen, was stattdessen gemeint war.
3. **Je Eintrag:** alter Pfad · neuer Pfad oder „ersatzlos" · was zu tun ist · ob
   `design-check.py --migrate` den Fall automatisch umschreiben kann.

## Heute

Leer — das System steht bei `1.0.0`, es gab noch keinen MAJOR-Sprung. Das ist kein
fehlendes Bauteil, sondern die ehrliche Lage: eine erfundene Beispielmigration waere ein
Platzhalter im Produktivpfad (A33).
