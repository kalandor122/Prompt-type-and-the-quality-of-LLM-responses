#!/usr/bin/env python3
"""
Statisztikai számítások — "LLM válaszainak minősége a prompt jellegétől függően"

Bemenet:
    data/manifest.json                654 futás metaadata
    data/want-verdicts.json           elvárásonkénti MET / VIOL / NA ítélet

Kimenet: konzolriport + stats-output.json

Függőség: numpy (a matplotlib már úgyis behúzza); scipy nem kell.

Statisztika:
    A megfigyelés egysége a futás, nem az elvárás. Egy futás 13-20 elvárása
    ugyanabból a beszélgetésből származik, ezért nem függetlenek egymástól.
    A páronkénti szignifikanciát futásszintű permutációs próba adja
    20 000 újrakeveréssel, Holm-korrekcióval. A khi-négyzet érték csak
    összehasonlításul szerepel.
    Khi-négyzet 2x2-re, df=1:  p = erfc(sqrt(chi2 / 2))

Futtatás:
    python3 stats.py
"""
import json, math, os

try:
    import numpy as np
except ImportError:
    raise SystemExit(
        "Ehhez a szkripthez numpy kell (a matplotlib úgyis behúzza):\n"
        "    pip install -r requirements.txt\n"
        "A permutációs próba a dolgozatéval azonos véletlenszám-generátort használ,\n"
        "ezért nem helyettesíthető standard könyvtárral."
    )
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
    # fél-felfelé kerekítés: 0,0385 -> 0,039 (a Python formázása fél-egészre kerekít)
    from decimal import Decimal, ROUND_HALF_UP
    if p < 0.001:
        return '<0,001'
    d = Decimal(str(p)).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
    return f'{d:.3f}'.replace('.', ',')


def fmt(x, d=2):
    return f'{x:.{d}f}'.replace('.', ',')


def permutation_test(group_a, group_b, rng, n_perm=20000):
    """
    Futásszintű permutációs próba két karra.

    group_*: [(met, total), ...] — karonként egy elem futásonként.
    A futásokat újrakeverjük a két csoport között, a csoportméreteket
    megtartva, és megszámoljuk, milyen gyakran adódik a mértnél nagyobb
    különbség. Ez a p-érték. A klaszterezést ez kezeli: a futás mozdul,
    nem az egyes elvárás.

    rng: numpy Generator. A hívó adja át, hogy a véletlenszám-sorozat
    ugyanaz legyen, mint a dolgozat számításában.
    """
    A = np.array([m for m, _ in group_a], dtype=np.int64)
    An = np.array([n for _, n in group_a], dtype=np.int64)
    B = np.array([m for m, _ in group_b], dtype=np.int64)
    Bn = np.array([n for _, n in group_b], dtype=np.int64)

    obs = B.sum() / Bn.sum() - A.sum() / An.sum()
    M = np.concatenate([A, B])
    N = np.concatenate([An, Bn])
    k = len(A)
    idx = np.arange(len(M))

    hits = 0
    for _ in range(n_perm):
        perm = rng.permutation(idx)
        d = (M[perm[k:]].sum() / N[perm[k:]].sum()
             - M[perm[:k]].sum() / N[perm[:k]].sum())
        if abs(d) >= abs(obs) - 1e-12:
            hits += 1
    return obs, (hits + 1) / (n_perm + 1)


def holm(pairs):
    """Holm-Bonferroni korrekció. pairs: [(név, p), ...] -> {név: p_holm}"""
    m = len(pairs)
    out, prev = {}, 0.0
    for i, (name, pv) in enumerate(sorted(pairs, key=lambda x: x[1])):
        adj = max(min(1.0, (m - i) * pv), prev)
        out[name] = adj
        prev = adj
    return out


def design_effect(per_arm):
    """
    ICC és design effect: mennyivel kevesebb a tényleges információ,
    mint az elvárások puszta száma.
    """
    rec = [x for rows in per_arm.values() for x in rows]
    rates = [m / n for m, n in rec if n]
    mean = sum(rates) / len(rates)
    obs_var = sum((r - mean) ** 2 for r in rates) / (len(rates) - 1)
    exp_var = sum((m / n) * (1 - m / n) / n for m, n in rec if n) / len(rec)
    icc = max(0.0, (obs_var - exp_var) / obs_var) if obs_var > 0 else 0.0
    mbar = sum(n for _, n in rec) / len(rec)
    return icc, 1 + (mbar - 1) * icc, mbar


def fisher_exact(a, b, c, d):
    """Kétoldali Fisher-féle egzakt p 2x2 táblára (a/b, c/d)."""
    n = a + b + c + d
    r1, c1 = a + b, a + c
    if n == 0:
        return 1.0

    def prob(k):
        return math.comb(r1, k) * math.comb(n - r1, c1 - k) / math.comb(n, c1)

    p_obs = prob(a)
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    p = sum(prob(k) for k in range(lo, hi + 1) if prob(k) <= p_obs + 1e-12)
    return min(1.0, p)


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

# ------------------------------------ 2. klaszter-hatás (a futás a megfigyelés)
print('\n' + '=' * 74)
print('2. KLASZTER-HATÁS  (miért nem függetlenek az elvárások)')
print('=' * 74)

per_run = defaultdict(list)          # kar -> [(met, total)] futásonként
# manifest-sorrendben építjük, hogy a permutáció ugyanazt adja, mint a dolgozatban
for rid, m in runs.items():
    wants = verdicts.get(rid)
    if not wants:
        continue
    met = sum(1 for v in wants.values() if v == 'MET')
    n = sum(1 for v in wants.values() if v in ('MET', 'VIOL'))
    if n:
        per_run[m['arm']].append((met, n))

icc, deff, mbar = design_effect(per_run)
print(f"  ICC (futáson belüli korreláció)   = {icc:.3f}")
print(f"  átlagos klaszterméret             = {mbar:.1f} elvárás / futás")
print(f"  design effect                     = {deff:.2f}")
print(f"  → {tot['A']['n']} elvárás ≈ {tot['A']['n'] / deff:.0f} független megfigyelés")
print("  Az elvárások egy futáson belül együtt mozognak, ezért a khi-négyzet")
print("  próba alábecsüli a p-értéket. A továbbiakban a futás a megfigyelés.")

# ------------------------------------- 3. páronkénti összevetések (permutáció)
print('\n' + '=' * 74)
print('3. PÁRONKÉNTI ÖSSZEVETÉSEK  (futásszintű permutációs próba + Holm)')
print('=' * 74)
print(f"{'Összevetés':<12}{'Δ (pp)':>9}{'χ² p':>9}{'perm. p':>10}{'Holm p':>9}{'Cohen h':>10}  Szign.")

PAIRS = [('A', 'B'), ('A', 'D'), ('A', 'E'), ('A', 'C'),
         ('E', 'C'), ('B', 'E'), ('B', 'D'), ('D', 'E')]
SEED = 20261104
rng = np.random.default_rng(SEED)      # egy generator, végig ugyanaz
pair_rows = []
for x, y in PAIRS:
    ax, ay = tot[x], tot[y]
    chi2, p_chi, _ = chi2_2x2(ax['met'], ax['n'] - ax['met'],
                              ay['met'], ay['n'] - ay['met'])
    obs, p_perm = permutation_test(per_run[x], per_run[y], rng)
    pair_rows.append({'comparison': f'{x} vs {y}', 'delta_pp': round(obs * 100, 2),
                      'chi2': round(chi2, 2), 'p_chi2': round(p_chi, 4),
                      'p_perm': round(p_perm, 4),
                      'cohens_h': round(cohens_h(arm_p[x], arm_p[y]), 3),
                      '_perm_raw': p_perm})

# a Holm-korrekciót a KEREKÍTETLEN p-értékekből kell számolni
adj = holm([(r['comparison'], r['_perm_raw']) for r in pair_rows])
for r in pair_rows:
    r['p_holm'] = round(adj[r['comparison']], 4)
    r['significant'] = adj[r['comparison']] < 0.05
    r.pop('_perm_raw', None)
    print(f"{r['comparison']:<12}{r['delta_pp']:>+9.2f}{fmt_p(r['p_chi2']):>9}"
          f"{fmt_p(r['p_perm']):>10}{fmt_p(r['p_holm']):>9}{fmt(r['cohens_h']):>10}"
          f"  {'igen' if r['significant'] else 'nem'}")
print("\n  A χ² p csak összehasonlításul; a döntés a Holm-korrigált permutációs p.")

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

if 'A' in t5p:
    for other in ('E', 'C'):
        if other not in t5p:
            continue
        a_, o_ = t5['A'], t5[other]
        p = fisher_exact(a_['met'], a_['n'] - a_['met'],
                         o_['met'], o_['n'] - o_['met'])
        print(f"\n  A vs {other}:  Fisher p={fmt_p(p)}  "
              f"h={fmt(cohens_h(t5p['A'], t5p[other]))}  "
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
    'clustering': {'icc': round(icc, 3), 'design_effect': round(deff, 2),
                   'avg_cluster_size': round(mbar, 1),
                   'effective_n_armA': round(tot['A']['n'] / deff),
                   'method': 'run-level permutation test, Holm-corrected'},
    'pairwise': pair_rows,
    't5_w1': {a: round(v * 100, 1) for a, v in t5p.items()},
    't5_w1_per_model_armA': {k: {'met': v['met'], 'n': v['n']} for k, v in per_model.items()},
    'per_model_CA': {k: {'A': round(v[0] * 100, 2), 'C': round(v[1] * 100, 2),
                         'delta': round((v[1] - v[0]) * 100, 2)} for k, v in cap.items()},
}
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=1)
print(f"\n→ {OUT_JSON}")
