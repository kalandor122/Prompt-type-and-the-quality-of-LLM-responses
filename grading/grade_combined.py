"""Grade every run across the three combined sources, all five arms.

Sources
  ot     321 runs  arms A,B,E  items T1-T9       (20261001-180200)
  hat     72 runs  arms A,B,E  items T11,T13     (20261006-175139)
  nyolc  261 runs  arms C,D    items T1-T13      (20261013-173607)

The same want rules are applied to every arm. Arm C receives the full
specification, so it is the CEILING: whatever C scores is the recoverable
intent the other arms either found or missed.
"""
from __future__ import annotations
import csv, json, re, sys, pathlib, collections
import os

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'harness' / 'src'))

BASE = pathlib.Path(os.environ.get('DATA_DIR') or pathlib.Path(__file__).resolve().parent.parent / 'data')
from itemloader import load_items, hidden_wants
import want_grader as WG
import coding_rules
import agentic_rules

RULES = dict(WG.RULES)
RULES.update({'T1': coding_rules.t1_rules(), 'T2': coding_rules.t2_rules(),
              'T3': coding_rules.t3_rules()})
RULES.update({'T11': agentic_rules.t11_rules(), 'T13': agentic_rules.t13_rules()})

ITEMS = {i['id']: i for i in load_items(str(pathlib.Path(__file__).resolve().parent.parent / 'harness' / 'items'))}
UW = {t: hidden_wants(ITEMS[t]) for t in ITEMS}

EMOJI = re.compile('[\U0001F300-\U0001FAFF]')
THROAT = re.compile(r"\b(great question|good question|certainly!|of course!|"
                    r"happy to help|that'?s a great)\b", re.I)
BULLET = re.compile(r"^\s*([-*•]|\d+[.)])\s+", re.M)
TABLE = re.compile(r"^\s*\|.*\|\s*$", re.M)


def run_paths(row):
    rd = pathlib.Path(row['_run_dir']) / row['run_id']
    p = row['response_path'].replace('\\', '/')
    rel = p.split('/' + row['run_id'] + '/', 1)[-1]
    return rd, rd / rel


def gather(row):
    rd, rp = run_paths(row)
    text = rp.read_text(encoding='utf-8', errors='replace') if rp.exists() else ''
    arts = {}
    for base in (rd / 'artifacts', pathlib.Path(row['_run_dir']).parent / '_go' / ('pilot-' + row['run_id'])):
        if base.is_dir():
            for f in base.rglob('*'):
                if f.is_file() and f.suffix.lower() in {'.md','.txt','.html','.css','.js',
                                                        '.json','.py','.svg','.webmanifest'}:
                    arts.setdefault(str(f.relative_to(base)),
                                    f.read_text(encoding='utf-8', errors='replace'))
    return text, arts


def main():
    rows = json.load(open(BASE / 'combined-manifest.json'))
    excl = set(json.load(open(BASE / 'exclusion-list.json')))

    results, obj = {}, []
    for r in rows:
        text, arts = gather(r)
        body = WG.strip_status(text)
        full = body + "\n" + "\n".join(arts.values())
        blob = text + "\n" + "\n".join(arts.values())

        v = {}
        for n, fn in RULES.get(r['item_id'], {}).items():
            try:
                out = fn(body, full, arts)
            except Exception:
                out = 'NA'
            if isinstance(out, bool): out = 'MET' if out else 'VIOL'
            elif isinstance(out, int): out = 'MET' if out == 1 else 'VIOL'
            v[f'W{n}'] = out
        results[r['run_id']] = v

        obj.append({
            'run_id': r['run_id'], 'source': r['_source'], 'item': r['item_id'],
            'arm': r['arm'], 'model': r['model_id'], 'rep': r['rep'],
            'category': r['category'], 'chars': len(blob),
            'emoji': len(EMOJI.findall(blob)), 'throat': len(THROAT.findall(blob)),
            'list_form': int(len(BULLET.findall(full)) >= 3 or len(TABLE.findall(full)) >= 2),
            'artifacts_written': int(r['artifacts_written'] or 0),
            'wants_delivered': int(r['wants_delivered'] or 0),
            'sim_ok': int(r['simulator_ok'] or 0) if r['simulator_ok'] != '' else None,
            'sim_attempts': int(r['simulator_attempts'] or 0),
            'elapsed_s': float(r['elapsed_s'] or 0),
            'out_tokens': int(r['output_tokens'] or 0),
            'excluded': r['run_id'] in excl,
        })

    json.dump(results, open(BASE / 'want-verdicts.json', 'w'), indent=1)
    json.dump(obj, open(BASE / 'objective.json', 'w'), indent=1)

    # ---------- report
    def pct(sel, skip_excluded=True):
        tot = met = 0
        for r in sel:
            if skip_excluded and r['run_id'] in excl: continue
            for k, ver in results.get(r['run_id'], {}).items():
                if ver != 'NA':
                    tot += 1; met += (ver == 'MET')
        return (100*met/tot if tot else 0), met, tot

    print(f"graded {len(results)} runs\n")
    print("=== % WANTS MET by item x arm  (excludes 17 silent-simulator runs) ===")
    print(f"  {'item':6} {'cat':10}" + "".join(f"{a:>8}" for a in 'ABCDE'))
    for tid in sorted(ITEMS):
        line = f"  {tid:6} {ITEMS[tid]['category']:10}"
        for arm in 'ABCDE':
            p,_,_ = pct([r for r in rows if r['item_id']==tid and r['arm']==arm])
            line += f"{p:7.0f}%" if p else f"{'--':>8}"
        print(line)

    print("\n=== % WANTS MET by group x arm ===")
    groups = {'format-only      (T7,T8,T9)': ('T7','T8','T9'),
              'false-premise    (T4,T5)':    ('T4','T5'),
              'data-integrity   (T6)':       ('T6',),
              'coding/agentic   (T1,T2,T3)': ('T1','T2','T3'),
              'realworld agentic(T11,T13)':  ('T11','T13')}
    print(f"  {'group':30}" + "".join(f"{a:>8}" for a in 'ABCDE') + "   ceiling gap (C-E)")
    for g, tids in groups.items():
        line = f"  {g:30}"
        vals = {}
        for arm in 'ABCDE':
            p,_,_ = pct([r for r in rows if r['item_id'] in tids and r['arm']==arm])
            vals[arm] = p
            line += f"{p:7.0f}%" if p else f"{'--':>8}"
        line += f"   {vals['C']-vals['E']:+6.1f}" if vals['C'] and vals['E'] else ""
        print(line)

    print("\n=== arm C is the CEILING: wants met, all items ===")
    for arm in 'ABCDE':
        p,m,t = pct([r for r in rows if r['arm']==arm])
        print(f"  arm {arm}: {m}/{t} = {p:.1f}%")


if __name__ == '__main__':
    main()
