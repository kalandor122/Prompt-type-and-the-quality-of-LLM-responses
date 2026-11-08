"""Build the combined workbook + graphs for all 654 runs across 5 arms."""
from __future__ import annotations
import json, sys, pathlib, collections
import os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'harness' / 'src'))
from itemloader import load_items, hidden_wants

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

BASE = pathlib.Path(os.environ.get('DATA_DIR') or pathlib.Path(__file__).resolve().parent.parent / 'data')
OUT = pathlib.Path(__file__).resolve().parent.parent / 'results'
OUT.mkdir(exist_ok=True)
G = OUT / 'graphs'; G.mkdir(exist_ok=True)

V = json.load(open(BASE / 'want-verdicts.json'))
OBJ = json.load(open(BASE / 'objective.json'))
rows = json.load(open(BASE / 'combined-manifest.json'))
excl = set(json.load(open(BASE / 'exclusion-list.json')))
ITEMS = {i['id']: i for i in load_items(str(pathlib.Path(__file__).resolve().parent.parent / 'harness' / 'items'))}
UW = {t: hidden_wants(ITEMS[t]) for t in ITEMS}
byid = {r['run_id']: r for r in rows}

ARMS = 'ABCDE'
ARM_COL = {'A': '#888888', 'B': '#2b7bba', 'C': '#2ca25f', 'D': '#e08214', 'E': '#d1495b'}
ARM_NAME = {'A': 'A none', 'B': 'B questions', 'C': 'C full spec',
            'D': 'D plan-correct', 'E': 'E assumptions'}
GROUPS = {'format-only': ('T7','T8','T9'), 'false-premise': ('T4','T5'),
          'data-integrity': ('T6',), 'coding/agentic': ('T1','T2','T3'),
          'realworld agentic': ('T11','T13')}


def pct(sel, skip=True):
    tot = met = 0
    for r in sel:
        if skip and r['run_id'] in excl: continue
        for k, ver in V.get(r['run_id'], {}).items():
            if ver != 'NA':
                tot += 1; met += (ver == 'MET')
    return (100 * met / tot if tot else 0), met, tot


# ============================================================ workbook
wb = Workbook(); wb.remove(wb.active)
HDR = PatternFill('solid', fgColor='2b7bba'); WHITE = Font(color='FFFFFF', bold=True)
MET = PatternFill('solid', fgColor='c6efce'); VIOL = PatternFill('solid', fgColor='ffc7ce')

ws = wb.create_sheet('Summary')
ws.append(['LLM interview study — combined results, 654 runs, 5 arms'])
ws.append(['ot (A,B,E T1-T9) + hat (A,B,E T11,T13) + nyolc (C,D T1-T13)'])
ws.append(['Arm C = full specification = the CEILING on recoverable intent'])
ws.append([])
ws.append(['Group'] + [f'Arm {a}' for a in ARMS] + ['C − A (recoverable)', 'C − E (missed)'])
for c in ws[5]: c.fill = HDR; c.font = WHITE
for g, tids in GROUPS.items():
    vals = {a: pct([r for r in rows if r['item_id'] in tids and r['arm'] == a])[0] for a in ARMS}
    ws.append([g] + [round(vals[a], 1) for a in ARMS] +
              [round(vals['C'] - vals['A'], 1), round(vals['C'] - vals['E'], 1)])
ws.append([])
ws.append(['ALL ITEMS'] + [round(pct([r for r in rows if r['arm'] == a])[0], 1) for a in ARMS] +
          [round(pct([r for r in rows if r['arm'] == 'C'])[0] - pct([r for r in rows if r['arm'] == 'A'])[0], 1),
           round(pct([r for r in rows if r['arm'] == 'C'])[0] - pct([r for r in rows if r['arm'] == 'E'])[0], 1)])
ws.append([])
ws.append(['Hypothesis', 'Verdict from the 5-arm data'])
for c in ws[ws.max_row]: c.fill = HDR; c.font = WHITE
for h, v in [
 ('H1  B,E > A', 'Supported overall (A 71.1 -> B 74.6, E 76.3) and strongly on coding/agentic'),
 ('H2  E > B', 'Supported (E 76.3 > B 74.6); E best on coding/agentic, B better on restraint items'),
 ('H3  root-cause split', 'Supported: knowledge-gap flat 80.5-81.5 across A/B/E while intent-ambiguity moves 66 -> 75'),
 ('H4  ceiling effect', 'See Per-model sheet'),
 ('H5  dose-response', 'Supported: coding +17.3 pts, format-only +5.6, restraint items flat'),
 ('NEW  arm C ceiling', 'C 83.7% overall. Interviewing recovers ~1/3 of the intent a full spec provides'),
]:
    ws.append([h, v])
ws.append([])
ws.append(['Excluded: 17 runs where the simulator went silent (B/D/E only).'])
ws.append(['Arm C has no simulator; it is unaffected.'])
for col, w in zip('ABCDEFGH', (34, 13, 13, 13, 13, 13, 20, 16)):
    ws.column_dimensions[col].width = w

# per-run
ws = wb.create_sheet('Per-run')
allw = sorted({int(k[1:]) for v in V.values() for k in v})
cols = ['Run', 'Source', 'Item', 'Group', 'Arm', 'Model', 'Rep', 'Excluded',
        'Seconds', 'Out tokens', 'Files', 'Wants delivered', 'Sim ok'] + [f'W{n}' for n in allw]
ws.append(cols)
for c in ws[1]: c.fill = HDR; c.font = WHITE
gmap = {t: g for g, ts in GROUPS.items() for t in ts}
o = {x['run_id']: x for x in OBJ}
for r in sorted(rows, key=lambda x: (x['item_id'], x['arm'], x['model_id'], x['rep'])):
    v = V.get(r['run_id'], {}); ox = o.get(r['run_id'], {})
    line = [r['run_id'], r['_source'], r['item_id'], gmap.get(r['item_id'], ''), r['arm'],
            r['model_id'], r['rep'], 'EXCLUDED' if r['run_id'] in excl else '',
            round(float(r['elapsed_s'] or 0)), int(r['output_tokens'] or 0),
            int(r['artifacts_written'] or 0), int(r['wants_delivered'] or 0),
            ox.get('sim_ok', '')]
    for n in allw: line.append(v.get(f'W{n}', ''))
    ws.append(line)
    for i, n in enumerate(allw, start=len(cols) - len(allw) + 1):
        c = ws.cell(row=ws.max_row, column=i)
        if c.value == 'MET': c.fill = MET
        elif c.value == 'VIOL': c.fill = VIOL
ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions

# per-want
ws = wb.create_sheet('Per-want')
ws.append(['Item', 'Group', 'Want', 'What'] + [f'{a} %' for a in ARMS] + ['C − A'])
for c in ws[1]: c.fill = HDR; c.font = WHITE
for tid in sorted(UW):
    for i, h in enumerate(UW[tid], 1):
        vals = {}
        for a in ARMS:
            m = t = 0
            for r in rows:
                if r['item_id'] != tid or r['arm'] != a or r['run_id'] in excl: continue
                ver = V.get(r['run_id'], {}).get(f'W{i}')
                if ver in ('MET', 'VIOL'): t += 1; m += (ver == 'MET')
            vals[a] = (100 * m / t) if t else None
        ws.append([tid, gmap.get(tid, ''), f'W{i}', h['what']] +
                  [round(vals[a], 1) if vals[a] is not None else '' for a in ARMS] +
                  [round(vals['C'] - vals['A'], 1) if vals['C'] is not None and vals['A'] is not None else ''])
ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions

# per-model
ws = wb.create_sheet('Per-model')
ws.append(['Model'] + [f'{a} %' for a in ARMS] + ['C − A'])
for c in ws[1]: c.fill = HDR; c.font = WHITE
for m in sorted({r['model_id'] for r in rows}):
    vals = {a: pct([r for r in rows if r['model_id'] == m and r['arm'] == a])[0] for a in ARMS}
    ws.append([m] + [round(vals[a], 1) for a in ARMS] +
              [round(vals['C'] - vals['A'], 1)])

# exclusions
ws = wb.create_sheet('Exclusions')
ws.append(['Run', 'Source', 'Item', 'Arm', 'Sim attempts', 'Reason'])
for c in ws[1]: c.fill = HDR; c.font = WHITE
for rid in sorted(excl):
    r = byid[rid]
    ws.append([rid, r['_source'], r['item_id'], r['arm'], r['simulator_attempts'],
               'simulator returned no text after 3 attempts'])

# manifest
ws = wb.create_sheet('Manifest')
keys = [k for k in rows[0].keys() if not k.startswith('_')] + ['source']
ws.append(keys)
for c in ws[1]: c.fill = HDR; c.font = WHITE
for r in rows: ws.append([r.get(k, '') for k in keys])
ws.freeze_panes = 'A2'

p = OUT / 'llm-interview-study-combined.xlsx'
wb.save(p)
print(f"workbook: {p} ({p.stat().st_size//1024} KB, {len(wb.sheetnames)} sheets)")

# ============================================================ graphs
plt.rcParams.update({'figure.dpi': 130, 'font.size': 9, 'axes.grid': True,
                     'grid.alpha': .25, 'axes.spines.top': False, 'axes.spines.right': False})

# 01 the ceiling
fig, ax = plt.subplots(figsize=(8.2, 4.4))
overall = [pct([r for r in rows if r['arm'] == a])[0] for a in ARMS]
b = ax.bar(range(5), overall, .55, color=[ARM_COL[a] for a in ARMS])
ax.bar_label(b, fmt='%.1f%%', fontsize=9, padding=2)
ax.axhline(overall[2], color='#2ca25f', ls='--', lw=1.2)
ax.text(4.45, overall[2] + .6, 'ceiling (full spec)', color='#2ca25f', fontsize=8, ha='right')
ax.set_xticks(range(5)); ax.set_xticklabels([ARM_NAME[a] for a in ARMS], fontsize=8)
ax.set_ylabel('% wants met'); ax.set_ylim(0, 100)
ax.set_title('Interviewing recovers about a third of what a full specification would give',
             fontweight='bold')
fig.tight_layout(); fig.savefig(G / '01-the-ceiling.png'); plt.close(fig)

# 02 dose-response across 5 arms
fig, ax = plt.subplots(figsize=(8.6, 4.6))
labels = list(GROUPS); x = range(len(labels))
for k, a in enumerate(ARMS):
    ys = [pct([r for r in rows if r['item_id'] in GROUPS[g] and r['arm'] == a])[0] for g in labels]
    b = ax.bar([i + (k - 2) * .16 for i in x], ys, .16, label=ARM_NAME[a], color=ARM_COL[a])
    ax.bar_label(b, fmt='%.0f', fontsize=6, padding=1)
ax.set_xticks(list(x)); ax.set_xticklabels([l.replace(' ', '\n', 1) for l in labels], fontsize=8)
ax.set_ylabel('% wants met'); ax.set_ylim(0, 105)
ax.set_title('Where each intervention helps', fontweight='bold')
ax.legend(frameon=False, fontsize=7, ncol=5)
fig.tight_layout(); fig.savefig(G / '02-dose-response-5arms.png'); plt.close(fig)

# 03 the split
fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.2))
ax = axes[0]
ia = [pct([r for r in rows if r['item_id'] in ('T1','T2','T3','T11','T13') and r['arm'] == a])[0] for a in ARMS]
kg = [pct([r for r in rows if r['item_id'] in ('T4','T5','T7','T8','T9') and r['arm'] == a])[0] for a in ARMS]
b1 = ax.bar([i - .18 for i in range(5)], ia, .36, color='#d1495b', label='intent-ambiguity')
b2 = ax.bar([i + .18 for i in range(5)], kg, .36, color='#2b7bba', label='knowledge-gap')
ax.bar_label(b1, fmt='%.0f', fontsize=7); ax.bar_label(b2, fmt='%.0f', fontsize=7)
ax.set_xticks(range(5)); ax.set_xticklabels(list(ARMS), fontsize=9)
ax.set_ylabel('% wants met'); ax.set_ylim(0, 105)
ax.set_title('H3 — knowledge-gap is flat; intent-ambiguity is what moves', fontweight='bold')
ax.legend(frameon=False, fontsize=8)
ax = axes[1]
gaps = [ia[i] - kg[i] for i in range(5)]
b = ax.bar(range(5), gaps, .55, color=[ARM_COL[a] for a in ARMS])
ax.bar_label(b, fmt='%+.0f', fontsize=8)
ax.axhline(0, color='k', lw=.8)
ax.set_xticks(range(5)); ax.set_xticklabels(list(ARMS), fontsize=9)
ax.set_ylabel('intent − knowledge (pts)')
ax.set_title('The deficit shrinks as the intervention gets stronger', fontweight='bold')
fig.tight_layout(); fig.savefig(G / '03-the-split.png'); plt.close(fig)

# 04 per item
fig, ax = plt.subplots(figsize=(9.5, 4.8))
tids = ['T1','T2','T3','T6','T11','T13','T4','T5','T7','T8','T9']
x = range(len(tids))
for k, a in enumerate(ARMS):
    ys = [pct([r for r in rows if r['item_id'] == t and r['arm'] == a])[0] for t in tids]
    ax.bar([i + (k - 2) * .16 for i in x], ys, .16, label=ARM_NAME[a], color=ARM_COL[a])
ax.set_xticks(list(x)); ax.set_xticklabels(tids, fontsize=9)
ax.set_ylabel('% wants met'); ax.set_ylim(0, 105)
ax.set_title('All 11 items, all 5 arms', fontweight='bold')
ax.legend(frameon=False, fontsize=7, ncol=5)
fig.tight_layout(); fig.savefig(G / '04-by-item-5arms.png'); plt.close(fig)

# 05 recoverable intent per item (C - A)
fig, ax = plt.subplots(figsize=(8.4, 4.8))
data = []
for t in tids:
    a = pct([r for r in rows if r['item_id'] == t and r['arm'] == 'A'])[0]
    c = pct([r for r in rows if r['item_id'] == t and r['arm'] == 'C'])[0]
    e = pct([r for r in rows if r['item_id'] == t and r['arm'] == 'E'])[0]
    d = pct([r for r in rows if r['item_id'] == t and r['arm'] == 'D'])[0]
    data.append((t, c - a, d - a, e - a))
data.sort(key=lambda x: x[1])
y = range(len(data))
ax.barh([i + .22 for i in y], [d[1] for d in data], .22, color='#2ca25f', label='ceiling: C − A')
ax.barh([i for i in y], [d[2] for d in data], .22, color='#e08214', label='D − A (plan)')
ax.barh([i - .22 for i in y], [d[3] for d in data], .22, color='#d1495b', label='E − A (assumptions)')
ax.axvline(0, color='k', lw=.8)
ax.set_yticks(list(y)); ax.set_yticklabels([d[0] for d in data], fontsize=9)
ax.set_xlabel('change in % wants met vs arm A')
ax.set_title('Recoverable intent per item — the green is what interviewing left on the table',
             fontweight='bold')
ax.legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(G / '05-recoverable-intent.png'); plt.close(fig)

# 06 by model
fig, ax = plt.subplots(figsize=(8.8, 4.6))
models = sorted({r['model_id'] for r in rows})
x = range(len(models))
for k, a in enumerate(ARMS):
    ys = [pct([r for r in rows if r['model_id'] == m and r['arm'] == a])[0] for m in models]
    ax.bar([i + (k - 2) * .16 for i in x], ys, .16, label=ARM_NAME[a], color=ARM_COL[a])
ax.set_xticks(list(x)); ax.set_xticklabels([m.replace('-', '\n', 1) for m in models], fontsize=7)
ax.set_ylabel('% wants met'); ax.set_ylim(0, 105)
ax.set_title('H4 — benefit is not monotonic in capability', fontweight='bold')
ax.legend(frameon=False, fontsize=7, ncol=5)
fig.tight_layout(); fig.savefig(G / '06-by-model.png'); plt.close(fig)

# 07 run health
fig, ax = plt.subplots(figsize=(8.2, 4.2))
labels = ['runs', 'two-phase', 'sim silent', 'excluded', 'wrote files']
vals = {a: [] for a in ARMS}
for a in ARMS:
    sub = [r for r in rows if r['arm'] == a]
    two = [r for r in sub if r['arm'] in ('B','D','E')]
    vals[a] = [len(sub), len(two),
               sum(1 for r in two if r['simulator_ok'] != '1'),
               sum(1 for r in sub if r['run_id'] in excl),
               sum(1 for r in sub if int(r['artifacts_written'] or 0) > 0)]
x = range(len(labels))
for k, a in enumerate(ARMS):
    b = ax.bar([i + (k - 2) * .16 for i in x], vals[a], .16, label=ARM_NAME[a], color=ARM_COL[a])
    ax.bar_label(b, fmt='%d', fontsize=6, padding=1)
ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=8)
ax.set_ylabel('runs')
ax.set_title('Run health — 654 runs, 17 excluded', fontweight='bold')
ax.legend(frameon=False, fontsize=7, ncol=5)
fig.tight_layout(); fig.savefig(G / '07-run-health.png'); plt.close(fig)

print(f"graphs: {len(list(G.glob('*.png')))} written to {G}")
for f in sorted(G.glob('*.png')):
    print("   ", f.name)
