#!/usr/bin/env python3
"""Erzeugt aus den geprueften Paletten (contrast.py = einzige Quelle):
  1. tokens.dtcg.json      DTCG 2025.10 (Farb-Wert als Objekt, Alias-Ebene, $extensions)
  2. tokens.css            CSS-Custom-Properties beider Themen (fuer showcase.html)
  3. palette-rows.html     Palettenzeilen mit gerechneten Kontrasten (fuer showcase.html)
Kein Hex-Wert und keine Kontrastzahl wird von Hand getippt (A33/Q11).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contrast import DARK, LIGHT, ratio, composite  # noqa: E402

EXT = 'at.ai-engineering.design'

def hex2comp(h):
    h = h.lstrip('#')
    return [round(int(h[i:i+2], 16) / 255.0, 4) for i in (0, 2, 4)]

def col(hexval, desc, alpha=None, contrast=None, rule=None):
    v = {'colorSpace': 'srgb', 'components': hex2comp(hexval), 'hex': hexval.upper()}
    if alpha is not None:
        v['alpha'] = alpha
    tok = {'$type': 'color', '$value': v, '$description': desc}
    ext = {}
    if contrast:
        ext['contrast'] = contrast
    if rule:
        ext['rule'] = rule
    if ext:
        tok['$extensions'] = {EXT: ext}
    return tok

def alias(ref, desc, rule=None):
    tok = {'$type': 'color', '$value': ref, '$description': desc}
    if rule:
        tok['$extensions'] = {EXT: {'rule': rule}}
    return tok

def dim(px, desc=None):
    tok = {'$type': 'dimension', '$value': {'value': px, 'unit': 'px'}}
    if desc:
        tok['$description'] = desc
    return tok

def num(n, desc=None):
    tok = {'$type': 'number', '$value': n}
    if desc:
        tok['$description'] = desc
    return tok

def cr(P, fg, bg, minimum):
    return {'vs': bg, 'ratio': round(ratio(P[fg], P[bg]), 2), 'min': minimum}

def theme_colors(P, theme):
    """Farb-Token eines Themas. Beschreibungen sind rollen-, nicht themenspezifisch."""
    return {
        'surface': {
            'canvas':  col(P['canvas'],  'App-Grund. Traegt keine Bedeutung — er ist das, wovor Bedeutung steht.'),
            'base':    col(P['surface'], 'Konsolenflaeche, Spalten, Baender. Der benannte Kontrastgrund aller Messungen.'),
            'raised':  col(P['raised'],  'Karte, Tabellenkopf, Dialog.'),
            'sunken':  col(P['sunken'],  'Zitatblock (verbatim), vertiefte Flaechen.'),
        },
        'line': {
            'quiet':   col(P['line'], 'Ruhige Trennlinie. DEKORATIV — darf nie die einzige Kennzeichnung eines Bedienelements sein.',
                           rule='nur dekorativ; Identifikation braucht line.control'),
            'strong':  col(P['line_strong'], 'Betonte Zonentrennung. Strukturell, nicht identifikationstragend.'),
            'control': col(P['line_control'], 'Identifikationskante fuer Bedienelemente (Eingabefeld, Konturtaste, Chip ohne Fuellung). SC 1.4.11.',
                           contrast=[cr(P, 'line_control', 'surface', 3.0), cr(P, 'line_control', 'raised', 3.0), cr(P, 'line_control', 'canvas', 3.0)]),
        },
        'ink': {
            'primary':   col(P['ink'], 'Primaertext.',
                             contrast=[cr(P, 'ink', 'canvas', 4.5), cr(P, 'ink', 'surface', 4.5), cr(P, 'ink', 'raised', 4.5), cr(P, 'ink', 'sunken', 4.5)]),
            'secondary': col(P['ink_dim'], 'Sekundaertext, Metazeilen, Herkunftszeilen.',
                             contrast=[cr(P, 'ink_dim', 'canvas', 4.5), cr(P, 'ink_dim', 'surface', 4.5), cr(P, 'ink_dim', 'raised', 4.5)]),
            'tertiary':  col(P['ink_quiet'], 'NUR Nicht-Text-Zeichen: Gitter, Ticks, Skelettbalken. Nie fuer Text.',
                             rule='nie als Textfarbe einsetzen'),
        },
        'interactive': {
            'accent':    col(P['accent'], 'NUR Bedienung: Fokusring, aktive Ansicht, Primaertaste, Auswahl, Verweis. Nie Zustand, nie Erfolg, nie "info".',
                             contrast=[cr(P, 'accent', 'surface', 4.5), cr(P, 'accent', 'raised', 4.5), cr(P, 'accent', 'canvas', 3.0)],
                             rule='Invariante I1: Interaktions-Kodierung und Zustands-Kodierung sind disjunkt'),
            'on-accent': col(P['on_accent'], 'Text auf gefuellter Primaertaste.',
                             contrast=[{'vs': 'accent', 'ratio': round(ratio(P['on_accent'], P['accent']), 2), 'min': 4.5}]),
        },
        'state': {
            'ok': {
                'base':   col(P['ok'], 'Verifiziert / bereit / erfuellt. Nie Bedienbarkeit.',
                              contrast=[cr(P, 'ok', 'surface', 4.5), cr(P, 'ok', 'raised', 4.5)]),
                'tint':   col(P['ok'], 'Flaechenwash 10% ueber surface. Text darauf: ink.primary.', alpha=0.10),
                'ground': col(P['ok_ground'], 'Eigener Kontrastgrund fuer textlastige ok-Flaechen.'),
                'on-ground': col(P['ok_on'], 'Text auf state.ok.ground.',
                                 contrast=[{'vs': 'ok.ground', 'ratio': round(ratio(P['ok_on'], P['ok_ground']), 2), 'min': 4.5}]),
            },
            'attention': {
                'base':   col(P['attention'], 'Braucht einen Menschen: gegatete Aktion, Countdown, offene Antwort. Heisst nie "kaputt".',
                              contrast=[cr(P, 'attention', 'surface', 4.5), cr(P, 'attention', 'raised', 4.5)]),
                'tint':   col(P['attention'], 'Flaechenwash 10% ueber surface.', alpha=0.10),
                'ground': col(P['att_ground'], 'Eigener Kontrastgrund fuer textlastige attention-Flaechen.'),
                'on-ground': col(P['att_on'], 'Text auf state.attention.ground.',
                                 contrast=[{'vs': 'attention.ground', 'ratio': round(ratio(P['att_on'], P['att_ground']), 2), 'min': 4.5}]),
            },
            'danger': {
                'base':   col(P['danger'], 'Abweichung / Verweigerung / Fehler. Nur hier, nie dekorativ. ALS TEXT NUR AUF state.danger.ground.',
                              contrast=[cr(P, 'danger', 'surface', 3.0), cr(P, 'danger', 'raised', 3.0)],
                              rule='als Text nie auf surface/raised (Hausreserve); als Marke/Kante/Balken erlaubt (>=3:1 gemessen)'),
                'tint':   col(P['danger'], 'Flaechenwash 10% ueber surface.', alpha=0.10),
                'ground': col(P['dan_ground'], 'Alarmgrund. Der Grund, warum der Alarmfall ein eigenes Band mit eigenem Grund hat.'),
                'on-ground': col(P['dan_on'], 'Text auf state.danger.ground.',
                                 contrast=[{'vs': 'danger.ground', 'ratio': round(ratio(P['dan_on'], P['dan_ground']), 2), 'min': 4.5}]),
            },
            'neutral': {
                'base':   alias('{color.%s.ink.secondary}' % theme,
                                'Keine Aussage: UNKNOWN, "nicht geprueft", leere Erfolgszustaende. ALIAS auf ink.secondary — die Gleichheit ist Absicht, kein Zufall (loest Cs fog==ink-dim-Duplikat).',
                                rule='Neutral behauptet nichts; leer ist Erfolg und nie rot'),
                'tint':   col(P['neutral'], 'Flaechenwash 10% ueber surface.', alpha=0.10),
                'ground': col(P['neu_ground'], 'Eigener Kontrastgrund fuer textlastige neutrale Flaechen.'),
                'on-ground': col(P['neu_on'], 'Text auf state.neutral.ground.',
                                 contrast=[{'vs': 'neutral.ground', 'ratio': round(ratio(P['neu_on'], P['neu_ground']), 2), 'min': 4.5}]),
            },
        },
    }

TOKENS = {
    '$description': 'AIE-Design-System v1.0.0 — Token-Quelle. Format: DTCG 2025.10. '
                    'Alle Kontrastwerte in $extensions sind von contrast.py gerechnet, nicht getippt. '
                    'Themes: color.dark (Referenz) und color.light; Aufloesung per DTCG-Resolver (2025.10).',
    'color': {
        'dark':  theme_colors(DARK, 'dark'),
        'light': theme_colors(LIGHT, 'light'),
    },
    'font': {
        'family': {
            'comment': {'$type': 'fontFamily',
                        '$value': ['system-ui', '-apple-system', 'Segoe UI Variable Text', 'Segoe UI', 'Roboto', 'Noto Sans', 'DejaVu Sans', 'sans-serif'],
                        '$description': 'Werkzeugstimme: Labels, Erklaerungen, Tasten, Navigation. Nur System-Schriften.'},
            'quote':   {'$type': 'fontFamily',
                        '$value': ['ui-monospace', 'SF Mono', 'Menlo', 'Cascadia Mono', 'Consolas', 'DejaVu Sans Mono', 'Liberation Mono', 'monospace'],
                        '$description': 'Belegstimme: alles Woertliche — Kommando, Hash, Pfad, Zeitstempel, Fehlercode. Dicktengleich = Beleg.'},
        },
        'size': {
            't10': dim(10, 'Chip-Beschriftung, Spaltenkopf. Versalien + letter-spacing .08em. Zeilenhoehe 1.2'),
            't11': dim(11, 'Metazeile, Herkunftszeile, Zeitstempel. Zeilenhoehe 1.35'),
            't12': dim(12, 'Tabellenzelle, Journal. Zeilenhoehe 1.4'),
            't13': dim(13, 'Grundtext. Zeilenhoehe 1.5'),
            't15': dim(15, 'Kartentitel, Lampenwert. Zeilenhoehe 1.35'),
            't18': dim(18, 'Ansichtstitel, Alarmtitel. Zeilenhoehe 1.25'),
            't22': dim(22, 'Nur der Alarmfall — einmal pro Bildschirm zulaessig. Zeilenhoehe 1.2'),
        },
        'lineheight': {
            't10': num(1.2), 't11': num(1.35), 't12': num(1.4), 't13': num(1.5),
            't15': num(1.35), 't18': num(1.25), 't22': num(1.2),
        },
    },
    'space': {
        '1': dim(4, 'Grundrhythmus'), '2': dim(8), '3': dim(12), '4': dim(16), '5': dim(24), '6': dim(32),
    },
    'radius': {
        's': dim(2, 'Chips, kbd'), 'm': dim(3, 'Karten, Dialoge'), 'l': dim(4, 'Fensterrahmen'),
    },
    'border': {
        'hairline': dim(1, 'Standardkante'), 'strong': dim(2, 'Betonte Kante, Konsequenz-Kante'),
    },
    'focus': {
        'width': dim(2, 'Fokusring-Staerke'), 'offset': dim(2, 'Fokusring-Versatz'),
    },
    'motion': {
        'none': {'$type': 'duration', '$value': {'value': 0, 'unit': 'ms'},
                 '$description': 'Default. Keine Animation ausser Fortschritt/Countdown.'},
        'progress': {'$type': 'duration', '$value': {'value': 1000, 'unit': 'ms'},
                     '$description': 'Einzige bewegte Ausnahme (Countdown-Balken). Bei prefers-reduced-motion: sekundengenaue Zahlenspruenge statt Balken.'},
    },
    'density': {
        'row': dim(28, 'Tabellenzeile'), 'row-dense': dim(24), 'control': dim(28, 'Tastenhoehe'), 'band': dim(60, 'Statusband'),
    },
    'breakpoint': {
        'hard-test': dim(900, 'Haertetest-Fensterbreite — der Entwurf muss hier vollstaendig sein'),
        'collapse': dim(1100, 'Unterhalb kollabiert der Ereignisstrom auf eine Bandkante'),
    },
}

# ---------------------------------------------------------------- Ausgaben
CSS_KEYS = [  # (css-var, palette-key)
    ('canvas', 'canvas'), ('surface', 'surface'), ('raised', 'raised'), ('sunken', 'sunken'),
    ('line', 'line'), ('line-strong', 'line_strong'), ('line-control', 'line_control'),
    ('ink', 'ink'), ('ink-dim', 'ink_dim'), ('ink-quiet', 'ink_quiet'),
    ('accent', 'accent'), ('on-accent', 'on_accent'),
    ('ok', 'ok'), ('attention', 'attention'), ('danger', 'danger'), ('neutral', 'neutral'),
    ('ok-ground', 'ok_ground'), ('ok-on', 'ok_on'),
    ('attention-ground', 'att_ground'), ('attention-on', 'att_on'),
    ('danger-ground', 'dan_ground'), ('danger-on', 'dan_on'),
    ('neutral-ground', 'neu_ground'), ('neutral-on', 'neu_on'),
]

def css_block(P, indent='  '):
    lines = []
    for var, key in CSS_KEYS:
        lines.append('%s--%s:%s;' % (indent, var, P[key]))
    for st, key in (('ok', 'ok'), ('attention', 'attention'), ('danger', 'danger'), ('accent', 'accent')):
        h = P[key].lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        lines.append('%s--tint-%s:rgba(%d,%d,%d,.10);' % (indent, st, r, g, b))
    return '\n'.join(lines)

ROW = ('<tr><td><span class="sw" style="background:%(hex)s"></span></td>'
       '<td class="mono">%(name)s</td><td class="mono">%(hex)s</td>'
       '<td>%(role)s</td><td class="mono num" data-fg="%(fg)s" data-bg="%(bg)s" data-min="%(min)s">%(ratio)s:1 auf %(ground)s</td></tr>')

def palette_rows(P, theme):
    """Zeilen der Schau-Tabelle; data-Attribute erlauben verify_showcase.py das Nachrechnen."""
    spec = [
        ('surface.canvas', 'canvas', 'App-Grund, traegt keine Bedeutung', None, None),
        ('surface.base', 'surface', 'Konsolenflaeche; benannter Messgrund', None, None),
        ('surface.raised', 'raised', 'Karte, Tabellenkopf, Dialog', None, None),
        ('surface.sunken', 'sunken', 'Zitatblock, vertieft', None, None),
        ('line.quiet', 'line', 'dekorative Trennlinie', None, None),
        ('line.strong', 'line_strong', 'Zonentrennung, strukturell', None, None),
        ('line.control', 'line_control', 'Identifikationskante (SC 1.4.11)', 'surface', 3.0),
        ('ink.primary', 'ink', 'Primaertext', 'surface', 4.5),
        ('ink.secondary', 'ink_dim', 'Sekundaertext, Herkunftszeilen', 'surface', 4.5),
        ('ink.tertiary', 'ink_quiet', 'NUR Nicht-Text-Zeichen', None, None),
        ('interactive.accent', 'accent', 'NUR Bedienung, nie Zustand', 'surface', 4.5),
        ('interactive.on-accent', 'on_accent', 'Text auf Primaertaste', 'accent', 4.5),
        ('state.ok.base', 'ok', 'verifiziert / bereit / erfuellt', 'surface', 4.5),
        ('state.attention.base', 'attention', 'braucht einen Menschen', 'surface', 4.5),
        ('state.danger.base', 'danger', 'Abweichung / Fehler; Text nur auf ground', 'surface', 3.0),
        ('state.neutral.base', 'neutral', 'keine Aussage (= ink.secondary, Alias)', 'surface', 4.5),
        ('state.ok.on-ground', 'ok_on', 'Text auf ok.ground', 'ok_ground', 4.5),
        ('state.attention.on-ground', 'att_on', 'Text auf attention.ground', 'att_ground', 4.5),
        ('state.danger.on-ground', 'dan_on', 'Text auf danger.ground', 'dan_ground', 4.5),
        ('state.neutral.on-ground', 'neu_on', 'Text auf neutral.ground', 'neu_ground', 4.5),
    ]
    out = []
    for name, key, role, ground, minimum in spec:
        if ground:
            r = '%.2f' % ratio(P[key], P[ground])
            out.append(ROW % dict(hex=P[key], name=name, role=role, fg=P[key], bg=P[ground],
                                  min=minimum, ratio=r, ground=ground.replace('_', '-')))
        else:
            out.append('<tr><td><span class="sw" style="background:%s"></span></td>'
                       '<td class="mono">%s</td><td class="mono">%s</td><td>%s</td>'
                       '<td class="mono num">&mdash;</td></tr>' % (P[key], name, P[key], role))
    return '\n'.join(out)

if __name__ == '__main__':
    # Pfade haengen am Paket, nicht am Arbeitsverzeichnis. Vorher lagen Werkzeug und
    # Ausgabe im selben Ordner und 'tokens.dtcg.json' war ein relativer Name; seit das
    # Paket unter design-system/ liegt und die Werkzeuge unter design-system/tools/,
    # waere das ein Schreibvorgang an der falschen Stelle. Nachgemessen: die drei
    # erzeugten Dateien sind vor und nach dieser Aenderung bytegleich (sha256).
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(ROOT, 'tokens.dtcg.json'), 'w') as f:
        json.dump(TOKENS, f, indent=2, ensure_ascii=True)
    with open(os.path.join(ROOT, 'tokens.css'), 'w') as f:
        f.write(':root,[data-theme="dark"]{\n' + css_block(DARK) + '\n}\n')
        f.write('[data-theme="light"]{\n' + css_block(LIGHT) + '\n}\n')
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'palette-rows.html'), 'w') as f:
        f.write('<!-- DUNKEL -->\n' + palette_rows(DARK, 'dark') + '\n<!-- HELL -->\n' + palette_rows(LIGHT, 'light') + '\n')
    print('geschrieben: tokens.dtcg.json, tokens.css, tools/palette-rows.html')
