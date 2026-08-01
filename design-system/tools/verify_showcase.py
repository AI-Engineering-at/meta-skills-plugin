#!/usr/bin/env python3
"""Maschinelle Selbstpruefung von showcase.html (Q6/Q7: der Prototyp wird
vermessen, nicht nur gebaut). Jeder Check druckt PASS/FAIL mit Rohwert."""
import re
import sys
import os
import hashlib
from html.parser import HTMLParser

# Pfade haengen am Paket, nicht am Arbeitsverzeichnis (siehe gen_tokens.py).
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from contrast import ratio  # noqa: E402

SRC = os.path.join(ROOT, 'showcase.html')
html = open(SRC, 'rb').read()
text = html.decode('ascii', errors='replace')
fails = 0

def check(name, ok, detail=''):
    global fails
    if not ok:
        fails += 1
    print('%-58s %s %s' % (name, 'PASS' if ok else '** FAIL **', detail))

# 1. Reines ASCII
non_ascii = [b for b in html if b > 127]
check('reines ASCII', len(non_ascii) == 0, '(%d Bytes > 127)' % len(non_ascii))

# 2. Beginnt mit <title>, dann <style>
check('Form: beginnt mit <title>', text.startswith('<title>'))
check('Form: <style> folgt direkt', text.split('\n', 1)[1].lstrip().startswith('<style>'))
check('Form: kein doctype/html/head/body-Tag',
      not re.search(r'<(!doctype|html|head|body)[\s>]', text, re.I))

# 3. Tag-Balance
class Bal(HTMLParser):
    VOID = {'br', 'hr', 'img', 'input', 'meta', 'link', 'wbr'}
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []
    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)
    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(tag)
b = Bal()
b.feed(text)
check('Tag-Balance', not b.errors and not b.stack,
      '(fehlpaarungen=%d, offen=%s)' % (len(b.errors), b.stack[:5]))

# 4. Keine externen Anforderungen
ext = re.findall(r'(?:src|href)\s*=\s*["\']https?://|url\(\s*["\']?https?://', text)
check('kein externer Request', len(ext) == 0, '(%d Treffer)' % len(ext))

# 5. Keine literale font-size (Token-Disziplin --t*)
lit = re.findall(r'font-size\s*:\s*[0-9]', text)
lit2 = re.findall(r'font\s*:\s*[^;]*[0-9]+px', text)
check('keine literale font-size (nur var(--t*))', len(lit) == 0 and len(lit2) == 0,
      '(%d + %d Treffer)' % (len(lit), len(lit2)))

# 6. Jede behauptete Kontrastzahl nachrechnen
pat = re.compile(r'data-fg="(#[0-9A-Fa-f]{6})"\s+data-bg="(#[0-9A-Fa-f]{6})"\s+data-min="([\d.]+)"\s*>([\d.]+):1')
claims = pat.findall(text)
bad = []
for fg, bg, mn, shown in claims:
    real = ratio(fg, bg)
    if abs(real - float(shown)) > 0.005:
        bad.append((fg, bg, shown, round(real, 2)))
    if real < float(mn):
        bad.append((fg, bg, 'unter Schwelle', mn))
check('Kontrast-Behauptungen nachgerechnet', len(claims) > 0 and not bad,
      '(%d Zahlen geprueft, %d falsch)' % (len(claims), len(bad)))
for x in bad:
    print('   ABWEICHUNG:', x)

# 7. Pruefwerte: Gruppen zusammensetzen und nachrechnen
hashvals = re.findall(r'<div class="hashVal num">((?:<span>[0-9a-f]{8}</span>)+)</div>', text)
joined = [''.join(re.findall(r'[0-9a-f]{8}', h)) for h in hashvals]
tok_digest = hashlib.sha256(open(os.path.join(ROOT, 'tokens.dtcg.json'), 'rb').read()).hexdigest()
exp_digest = hashlib.sha256(b'uname -a').hexdigest()
act_digest = hashlib.sha256(b'uname -a\n').hexdigest()
check('Digest 1 = sha256(tokens.dtcg.json)', len(joined) > 0 and joined[0] == tok_digest)
check('Digest 2 = sha256("uname -a")', len(joined) > 1 and joined[1] == exp_digest)
check('Digest 3 = sha256("uname -a\\n")', len(joined) > 2 and joined[2] == act_digest)
check('kein zusammenhaengendes 64-Hex im Quelltext',
      not re.search(r'[0-9a-fA-F]{64}', text))

# 8. Acht Zustaende in der Galerie und in der Kartenreihe
states = ['idle', 'pending', 'success', 'empty', 'partial', 'failed', 'unavailable', 'locked']
gal = text.split('id="zustaende"', 1)[1].split('</section>', 1)[0]
missing = [s for s in states if '<b>%s</b>' % s not in gal]
check('Zustandsgalerie: alle 8 Zustaende', not missing, str(missing))
cards = text.split('M2 &middot;', 1)[1].split('<h3>M3', 1)[0]
tags = re.findall(r'<span class="stateTag">([a-z]+)', cards)
check('M2-Karten: 8 Zustands-Tags', len(tags) == 8, '(%d: %s)' % (len(tags), tags))

# 9. Eingebettete Paletten identisch mit tokens.css (eine Quelle)
tok_css = open(os.path.join(ROOT, 'tokens.css')).read()
blocks = re.findall(r'--[a-z-]+:[^;]+;', tok_css)
miss = [bl for bl in blocks if bl not in text.replace('  ', '  ')]
miss = [bl for bl in blocks if bl.strip() not in text]
check('alle tokens.css-Werte im Schaustueck', not miss, '(%d fehlen)' % len(miss))

# 10. Bedienelemente haben zugaenglichen Namen (SC 4.1.2): kein leerer button
empty_btn = re.findall(r'<button[^>]*>\s*</button>', text)
check('kein unbenannter <button>', len(empty_btn) == 0, '(%d)' % len(empty_btn))

# 11. Statistik
print('-' * 78)
print('Statistik: %d Bytes, %d Zeilen, %d Kontrast-Behauptungen, %d Hashbloecke'
      % (len(html), text.count('\n') + 1, len(claims), len(joined)))
print('FAILS:', fails)
sys.exit(1 if fails else 0)
