#!/usr/bin/env python3
"""
Statisztikai számítások — "LLM válaszainak minősége a prompt jellegétől függően"

Bemenet:
    data/manifest.json                654 futás metaadata
    data/want-verdicts.json           elvárásonkénti MET / VIOL / NA ítélet

Kimenet: konzolriport + stats-output.json

Függőség: csak a Python standard könyvtár (nincs numpy/scipy).
    Khi-négyzet 2x2-re, df=1:  p = erfc(sqrt(chi2 / 2))

Futtatás:
    python3 stats.py
"""
import json, math, os
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
# a data/ mappa a szkripttel azonos szinten vagy eggyel feljebb
for cand in (BASE, os.path.dirname(BASE)):
    if os.path.isdir(os.path.join(cand, 'data')):
        BASE = cand
        break
MANIFEST = os.path.join(BASE, 'data', 'manifest.json')
VERDICTS = os.path.join(BASE, 'data', 'want-verdicts.json')
OUT_JSON = os.path.join(BASE, 'results', 'stats-output.json')

Z = 1.959963984540054  # 95%-os kétoldalú normális kvantilis


# ----------------------------------------------------------------- együtthatók
def wilson(k, n, z=Z):
    """Wilson-féle megbízhatósági intervallum arányra (0..1)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z / d) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, centre - half), min(1.0, centre + half))


def chi2_2x2(a, b, c, d, yates=False):
    """
    2x2 kontingencia-tábla khi-négyzet próbája.
        a, b : 1. csoport  (siker, kudarc)
        c, d : 2. csoport  (siker, kudarc)
    Visszaad: (chi2, p, df=1)
    A dolgozatban Yates-korrekció NÉLKÜLI érték szerepel.
    """
    n = a + b + c + d
    if n == 0:
        return (0.0, 1.0, 1)
    if yates:
        num = n * (abs(a * d - b * c) - n / 2.0) ** 2
    else:
        num = n * (a * d - b * c) ** 2
    den = (a + b) * (c + d) * (a + c) * (b + d)
    if den == 0:
        return (0.0, 1.0, 1)
    chi2 = num / den
    # df = 1  ->  p = erfc(sqrt(chi2/2))
    p = math.erfc(math.sqrt(chi2 / 2.0))
    return (chi2, p, 1)


def cohens_h(p1, p2):
    """
    Cohen h két arányra, arcsin-transzformációval.
        h = |2*arcsin(sqrt(p1)) - 2*arcsin(sqrt(p2))|
    Értelmezés (Cohen 1988): 0,20 kicsi · 0,50 közepes · 0,80 nagy
    """
    return abs(2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2)))


def h_label(h):
    if h < 0.20:
        return 'elhanyagolható'
    if h < 0.50:
        return 'kicsi'
    if h < 0.80:
        return 'közepes'
    return 'nagy'


def fmt_p(p):
    return '<0,001' if p < 0.001 else f'{p:.3f}'.replace('.', ',')


def fmt(x, d=2):
    return f'{x:.{d}f}'.replace('.', ',')


# ----------------------------------------------------------------- adatbetöltés
with open(MANIFEST, encoding='utf-8') as f:
    manifest = json.load(f)
with open(VERDICTS, encoding='utf-8') as f:
    verdicts = json.load(f)

# A 17 kizárt futás (néma szimulátor) nem számít bele az értékelésbe.
EX_LIST = os.path.join(BASE, 'data', 'exclusion-list.json')
EXCLUDED = set()
if os.path.exists(EX_LIST):
    with open(EX_LIST, encoding='utf-8') as f:
        EXCLUDED = set(json.load(f))
print(f'Kizárt futás: {len(EXCLUDED)}  →  {len(verdicts)} rögzített, '
      f'{len(verdicts) - len(EXCLUDED)} értékelt')
verdicts = {k: v for k, v in verdicts.items() if k not in EXCLUDED}

runs = {r['run_id']: r for r in manifest}
ARMS = list('ABCDE')

# ------------------------------------------------------- 1. karonkénti teljesülés
tot = defaultdict(lambda: {'met': 0, 'n': 0})
for rid, wants in verdicts.items():
    m = runs.get(rid)
    if m is None:
        continue
    for w, v in wants.items():
        if v in ('MET', 'VIOL'):
            tot[m['arm']]['n'] += 1
            if v == 'MET':
                tot[m['arm']]['met'] += 1

print('=' * 74)
print('1. TELJESÜLÉS KARONKÉNT  (összes elvárás, minden feladat)')
print('=' * 74)
print(f"{'Kar':<5}{'Teljesült':>11}{'Összes':>9}{'Arány':>9}{'95% CI (Wilson)':>22}")
arm_p = {}
for a in ARMS:
    d = tot[a]
    p = d['met'] / d['n'] if d['n'] else 0
    lo, hi = wilson(d['met'], d['n'])
    arm_p[a] = p
    print(f"{a:<5}{d['met']:>11}{d['n']:>9}{fmt(p*100):>8}%   "
          f"[{fmt(lo*100,1)}; {fmt(hi*100,1)}]".rjust(22))
print(f"\nÖsszes futás: {len(manifest)}")

# --------------------------------------------- 2. khi-négyzet + Cohen h (A alap)
print('\n' + '=' * 74)
print('2. PÁRONKÉNTI ÖSSZEVETÉSEK  (kiindulás: A kar)')
print('=' * 74)
print(f"{'Összevetés':<12}{'Δ (pp)':>9}{'χ²':>9}{'p':>9}{'Cohen h':>10}  {'Hatás':<16}{'Szign.'}")
pair_rows = []
for b in 'BCDE':
    a_, b_ = tot['A'], tot[b]
    chi2, p, df = chi2_2x2(a_['met'], a_['n'] - a_['met'],
                           b_['met'], b_['n'] - b_['met'])
    h = cohens_h(arm_p['A'], arm_p[b])
    sig = 'igen' if p < 0.05 else 'nem'
    print(f"A → {b:<8}{(arm_p[b]-arm_p['A'])*100:>+8.2f}{chi2:>9.2f}{fmt_p(p):>9}"
          f"{fmt(h):>10}  {h_label(h):<16}{sig}")
    pair_rows.append({'comparison': f'A vs {b}', 'delta_pp': round((arm_p[b]-arm_p['A'])*100, 3),
                      'chi2': round(chi2, 4), 'p': p, 'cohens_h': round(h, 4),
                      'significant': p < 0.05})

# a dolgozatban külön szereplő összevetések
print('\n— a dolgozatban kiemelt további összevetések —')
extra = [('C', 'A'), ('E', 'B'), ('E', 'C'), ('B', 'D')]
for x, y in extra:
    a_, b_ = tot[x], tot[y]
    chi2, p, df = chi2_2x2(a_['met'], a_['n'] - a_['met'],
                           b_['met'], b_['n'] - b_['met'])
    h = cohens_h(arm_p[x], arm_p[y])
    print(f"  {x} vs {y}:  Δ={(arm_p[x]-arm_p[y])*100:+.2f} pp   "
          f"χ²={chi2:.2f}  p={fmt_p(p)}  h={fmt(h)} ({h_label(h)})  "
          f"{'szignifikáns' if p < 0.05 else 'nem szignifikáns'}")

# ------------------------------------------------------------- 3. T5 hamis premissza
print('\n' + '=' * 74)
print('3. T5 — NEM LÉTEZŐ 1989-ES CIKK, W1 elvárás (a premissza felismerése)')
print('=' * 74)
t5 = defaultdict(lambda: {'met': 0, 'n': 0})
for rid, wants in verdicts.items():
    m = runs.get(rid)
    if m is None or m['item_id'] != 'T5':
        continue
    v = wants.get('W1')
    if v in ('MET', 'VIOL'):
        t5[m['arm']]['n'] += 1
        if v == 'MET':
            t5[m['arm']]['met'] += 1
print(f"{'Kar':<6}{'Helyes':>8}{'Összes':>8}{'Arány':>9}")
t5p = {}
for a in ARMS:
    d = t5.get(a, {'met': 0, 'n': 0})
    if d['n'] == 0:
        continue
    t5p[a] = d['met'] / d['n']
    print(f"{a:<6}{d['met']:>8}{d['n']:>8}{fmt(t5p[a]*100,1):>8}%")

if 'A' in t5p and 'E' in t5p:
    a_, e_ = t5['A'], t5['E']
    chi2, p, _ = chi2_2x2(a_['met'], a_['n'] - a_['met'],
                          e_['met'], e_['n'] - e_['met'])
    print(f"\n  A vs E:  χ²={chi2:.3f}  p={fmt_p(p)}  "
          f"h={fmt(cohens_h(t5p['A'], t5p['E']))}  "
          f"→ {'SZIGNIFIKÁNS' if p < 0.05 else 'nem szignifikáns'}")

# --------------------------------------------- 4. T5 W1 modellenként (A kar)
print('\n' + '=' * 74)
print('4. T5 W1 MODELLENKÉNT — csak A kar (segítség nélkül)')
print('=' * 74)
per_model = defaultdict(lambda: {'met': 0, 'n': 0})
for rid, wants in verdicts.items():
    m = runs.get(rid)
    if m is None or m['item_id'] != 'T5' or m['arm'] != 'A':
        continue
    v = wants.get('W1')
    if v in ('MET', 'VIOL'):
        per_model[m['label']]['n'] += 1
        if v == 'MET':
            per_model[m['label']]['met'] += 1
for lab in sorted(per_model, key=lambda k: -per_model[k]['met']):
    d = per_model[lab]
    print(f"  {lab:<24}{d['met']:>3}/{d['n']:<3}  {fmt(d['met']/d['n']*100,0):>5}%")

# ------------------------------------------------- 5. modellenkénti C − A különbség
print('\n' + '=' * 74)
print('5. MODELLENKÉNTI TELJESÜLÉS ÉS C − A KÜLÖNBSÉG')
print('=' * 74)
mm = defaultdict(lambda: defaultdict(lambda: {'met': 0, 'n': 0}))
for rid, wants in verdicts.items():
    m = runs.get(rid)
    if m is None:
        continue
    for w, v in wants.items():
        if v in ('MET', 'VIOL'):
            mm[m['label']][m['arm']]['n'] += 1
            if v == 'MET':
                mm[m['label']][m['arm']]['met'] += 1
print(f"{'Modell':<24}{'A':>7}{'C':>8}{'C−A':>9}")
cap = {}
for lab in sorted(mm):
    a_ = mm[lab]['A']; c_ = mm[lab]['C']
    if a_['n'] == 0 or c_['n'] == 0:
        continue
    pa, pc = a_['met'] / a_['n'], c_['met'] / c_['n']
    cap[lab] = (pa, pc)
    print(f"{lab:<24}{fmt(pa*100):>7}{fmt(pc*100):>8}{(pc-pa)*100:>+8.2f}")

# ----------------------------------------------------------------- összegzés
summary = {
    'n_runs': len(manifest),
    'arms': {a: {'met': tot[a]['met'], 'n': tot[a]['n'],
                 'pct': round(arm_p[a] * 100, 2),
                 'ci95': [round(v * 100, 2) for v in wilson(tot[a]['met'], tot[a]['n'])]}
             for a in ARMS},
    'pairwise_vs_A': pair_rows,
    't5_w1': {a: round(v * 100, 1) for a, v in t5p.items()},
    't5_w1_per_model_armA': {k: {'met': v['met'], 'n': v['n']} for k, v in per_model.items()},
    'per_model_CA': {k: {'A': round(v[0] * 100, 2), 'C': round(v[1] * 100, 2),
                         'delta': round((v[1] - v[0]) * 100, 2)} for k, v in cap.items()},
}
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=1)
print(f"\n→ {OUT_JSON}")
