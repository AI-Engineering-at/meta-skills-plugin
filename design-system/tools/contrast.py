#!/usr/bin/env python3
"""WCAG-2.2-Kontrastrechner fuer das AIE-Design-System.
Rechnet JEDE vorgeschlagene Kombination aus und prueft sie gegen ihre Schwelle.
Formel: WCAG 2.x relative luminance (sRGB), ratio = (L1+0.05)/(L2+0.05).
Keine Zahl im Design-Dokument darf aus einer anderen Quelle stammen als diesem Lauf.
"""

def srgb_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def lum(hexcol):
    h = hexcol.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.2126 * srgb_lin(r) + 0.7152 * srgb_lin(g) + 0.0722 * srgb_lin(b)

def ratio(fg, bg):
    l1, l2 = lum(fg), lum(bg)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)

def composite(over_hex, alpha, under_hex):
    """10%-Tint ueber Grund -> effektive Flaechenfarbe."""
    o = over_hex.lstrip('#'); u = under_hex.lstrip('#')
    out = []
    for i in (0, 2, 4):
        a = int(o[i:i+2], 16); b = int(u[i:i+2], 16)
        out.append(round(a * alpha + b * (1 - alpha)))
    return '#%02X%02X%02X' % tuple(out)

# ---------------------------------------------------------------- Paletten
DARK = dict(
    canvas='#0E141A', surface='#151E26', raised='#1C2831', sunken='#0A1015',
    line='#26343F', line_strong='#3D5164', line_control='#587490',
    ink='#DDE7ED', ink_dim='#93A7B4', ink_quiet='#61737F',
    accent='#5D9FD6', on_accent='#0A1015',
    ok='#63AC76', attention='#CE9737', danger='#E1584D', neutral='#93A7B4',
    ok_ground='#12271A', ok_on='#A8D8B5',
    att_ground='#2B2107', att_on='#E8C687',
    dan_ground='#3A1512', dan_on='#F4A198',
    neu_ground='#1B252D', neu_on='#B6C8D2',
)
LIGHT = dict(
    canvas='#E9EEF2', surface='#F6F9FB', raised='#FFFFFF', sunken='#DCE4EA',
    line='#C3CFD8', line_strong='#A2B3BF', line_control='#6E8699',
    ink='#182129', ink_dim='#455864', ink_quiet='#8195A1',
    accent='#1C6CA8', on_accent='#FFFFFF',
    ok='#22713F', attention='#875410', danger='#AC3428', neutral='#455864',
    ok_ground='#D9EDDF', ok_on='#174D2B',
    att_ground='#F3E4C4', att_on='#5F3B08',
    dan_ground='#F6DCD8', dan_on='#7E2317',
    neu_ground='#DFE7EC', neu_on='#33434E',
)

def check(theme_name, P):
    print('=' * 76)
    print('THEMA:', theme_name)
    print('=' * 76)
    fails = 0
    rows = []

    def t(label, fg, bg, need):
        nonlocal fails
        r = ratio(P[fg] if fg in P else fg, P[bg] if bg in P else bg)
        ok = r >= need
        if not ok:
            fails += 1
        rows.append((label, P.get(fg, fg), P.get(bg, bg), r, need, ok))

    # --- Text 4.5:1 (SC 1.4.3 normal) -----------------------------------
    t('ink auf canvas', 'ink', 'canvas', 4.5)
    t('ink auf surface', 'ink', 'surface', 4.5)
    t('ink auf raised', 'ink', 'raised', 4.5)
    t('ink auf sunken', 'ink', 'sunken', 4.5)
    t('ink-dim auf canvas', 'ink_dim', 'canvas', 4.5)
    t('ink-dim auf surface', 'ink_dim', 'surface', 4.5)
    t('ink-dim auf raised', 'ink_dim', 'raised', 4.5)
    t('accent als Text auf surface', 'accent', 'surface', 4.5)
    t('accent als Text auf raised', 'accent', 'raised', 4.5)
    t('on-accent auf accent (Primaertaste)', 'on_accent', 'accent', 4.5)
    t('ok als Text auf surface', 'ok', 'surface', 4.5)
    t('attention als Text auf surface', 'attention', 'surface', 4.5)
    t('danger als Text auf surface  [erwartet: Regel noetig]', 'danger', 'surface', 4.5)
    t('neutral als Text auf surface', 'neutral', 'surface', 4.5)
    t('ok-on auf ok-ground', 'ok_on', 'ok_ground', 4.5)
    t('attention-on auf attention-ground', 'att_on', 'att_ground', 4.5)
    t('danger-on auf danger-ground', 'dan_on', 'dan_ground', 4.5)
    t('neutral-on auf neutral-ground', 'neu_on', 'neu_ground', 4.5)

    # --- Text auf 10%-Tints (ink bleibt der Texttraeger) -----------------
    for st in ('ok', 'attention', 'danger', 'accent'):
        key = st if st != 'accent' else 'accent'
        eff = composite(P[key], 0.10, P['surface'])
        t('ink auf tint-%s (10%% ueber surface = %s)' % (st, eff), 'ink', eff, 4.5)

    # --- Zustandsfarben als Chip-Text auf Karten (raised) ----------------
    t('ok als Text auf raised', 'ok', 'raised', 4.5)
    t('attention als Text auf raised', 'attention', 'raised', 4.5)
    t('neutral als Text auf raised', 'neutral', 'raised', 4.5)

    # --- Grafik / Bedienelement-Kanten 3:1 (SC 1.4.11) -------------------
    t('line-control vs surface (Identifikationskante)', 'line_control', 'surface', 3.0)
    t('line-control vs raised', 'line_control', 'raised', 3.0)
    t('line-control vs canvas', 'line_control', 'canvas', 3.0)
    t('accent vs surface (Fokusring)', 'accent', 'surface', 3.0)
    t('accent vs raised (Fokusring auf Karte)', 'accent', 'raised', 3.0)
    t('accent vs canvas (Fokusring auf Grund)', 'accent', 'canvas', 3.0)
    t('ok-Marke vs surface', 'ok', 'surface', 3.0)
    t('attention-Marke vs surface', 'attention', 'surface', 3.0)
    t('danger-Marke vs surface', 'danger', 'surface', 3.0)
    t('danger-Marke vs raised', 'danger', 'raised', 3.0)
    t('neutral-Marke vs surface', 'neutral', 'surface', 3.0)

    # --- Informativ (keine Schwelle): dekorative Kanten, Nicht-Text ------
    for lbl, fg, bg in (('line (ruhig) vs surface — dekorativ', 'line', 'surface'),
                        ('line-strong vs surface — strukturell, NICHT identifikationstragend', 'line_strong', 'surface'),
                        ('ink-quiet vs surface — nur Nicht-Text-Zeichen', 'ink_quiet', 'surface')):
        r = ratio(P[fg], P[bg])
        rows.append((lbl + '  [info]', P[fg], P[bg], r, 0.0, True))

    for label, fg, bg, r, need, ok in rows:
        print('%-58s %s auf %s  %5.2f:1  (>=%s)  %s' %
              (label, fg, bg, r, need, 'PASS' if ok else '** FAIL **'))
    print('-' * 76)
    print('FAILS:', fails)
    return fails

if __name__ == '__main__':
    f = check('DUNKEL (Referenz)', DARK) + check('HELL', LIGHT)
    print()
    print('GESAMT-FAILS:', f)
