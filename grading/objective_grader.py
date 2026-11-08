"""Objective (scriptable) grading layer for the 20261001-180200 run.

Everything here is a mechanical signal, not a judgement call. The subjective
wants are graded separately from reading the outputs, so that the same rule
gets applied to all three arms.
"""
from __future__ import annotations
import csv, json, re, sys, collections, pathlib
import os

RUN = pathlib.Path(os.environ.get('RUN_DIR') or pathlib.Path(__file__).resolve().parent.parent / 'runs')
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'harness' / 'src'))
from itemloader import load_items, hidden_wants

ITEMS = {i['id']: i for i in load_items(str(pathlib.Path(__file__).resolve().parent.parent / 'harness' / 'items'))}

EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\u2190-\u21FF\u2B00-\u2BFF]")
THROAT = re.compile(r"\b(great question|good question|certainly!|of course!|happy to help|"
                    r"i'd be happy|great choice|absolutely!)\b", re.I)
BULLET = re.compile(r"^\s*([-*•]|\d+[.)])\s+", re.M)
CITE = re.compile(r"(according to|as reported by|wikipedia|britannica|nasa (reports|says|measured)|"
                  r"study (in|of) \d{4}|et al\.|doi:|pmid|https?://)", re.I)
STAT = re.compile(r"\b\d{1,3}(?:[.,]\d+)?\s?(%|percent|billion|million|tonnes|tons|km|miles)\b", re.I)


def resp_path(r):
    p = r['response_path'].replace('\\', '/')
    run = r['run_id']
    return RUN / run / p.split('/' + run + '/', 1)[-1]


def truthy(v): return v in ('1', 'True', 'true', 'TRUE')


def load_rows():
    return list(csv.DictReader(open(RUN / 'manifest.csv')))


def objective_signals(text: str, artifacts: dict[str, str]) -> dict:
    """Signals computable from text alone. artifacts = filename -> content."""
    alltext = text + "\n" + "\n".join(artifacts.values())
    bullets = len(BULLET.findall(alltext))
    return {
        'chars': len(alltext),
        'emoji': len(EMOJI.findall(alltext)),
        'throat_clearing': len(THROAT.findall(alltext)),
        'bullet_lines': bullets,
        'is_list': bullets >= 3,
        'citation_markers': len(CITE.findall(alltext)),
        'statistic_markers': len(STAT.findall(alltext)),
        'first_is_answer': bool(alltext.strip()),
    }


def main():
    rows = load_rows()
    out = []
    for r in rows:
        run_dir = RUN / r['run_id']
        rp = resp_path(r)
        text = rp.read_text(encoding='utf-8', errors='replace') if rp.exists() else ''
        arts = {}
        adir = run_dir / 'artifacts'
        if adir.is_dir():
            for f in adir.rglob('*'):
                if f.is_file():
                    arts[str(f.relative_to(adir))] = f.read_text(encoding='utf-8', errors='replace')
        # artefacts also live in the sandbox
        sand = RUN / '_go' / ('pilot-' + r['run_id'])
        if sand.is_dir():
            for f in sand.rglob('*'):
                if f.is_file() and f.suffix.lower() in {'.md', '.txt', '.html', '.css', '.js', '.json', '.py'}:
                    arts.setdefault(str(f.relative_to(sand)),
                                    f.read_text(encoding='utf-8', errors='replace'))
        sig = objective_signals(text, arts)
        sig.update({
            'run_id': r['run_id'], 'item': r['item_id'], 'arm': r['arm'],
            'model': r['model_id'], 'rep': r['rep'],
            'artifacts_written': int(r['artifacts_written'] or 0),
            'artifacts_changed': int(r['artifacts_changed'] or 0),
            'wants_delivered': int(r['wants_delivered'] or 0),
            'asked': truthy(r['asked_questions']),
            'corrected': truthy(r['correction_applied']),
            'sim_ok': truthy(r['simulator_ok']),
            'elapsed_s': float(r['elapsed_s'] or 0),
            'out_tokens': int(r['output_tokens'] or 0),
        })
        out.append(sig)

    json.dump(out, open(str(pathlib.Path(__file__).resolve().parent / 'objective.json'), 'w'), indent=1)

    print(f"scored {len(out)} runs\n")
    print("=== objective signals by arm (all items) ===")
    print(f"  arm    n   emoji  throat  list%  cite   stat   chars_med")
    for arm in ('A', 'B', 'E'):
        s = [x for x in out if x['arm'] == arm]
        print(f"  {arm}  {len(s):4}  {sum(x['emoji'] for x in s):5}  "
              f"{sum(x['throat_clearing'] for x in s):6}  "
              f"{100*sum(x['is_list'] for x in s)/len(s):5.0f}%  "
              f"{sum(x['citation_markers'] for x in s):5}  "
              f"{sum(x['statistic_markers'] for x in s):5}  "
              f"{sorted(x['chars'] for x in s)[len(s)//2]:6}")

    print("\n=== fabricated-content red flags (knowledge items only) ===")
    for arm in ('A', 'B', 'E'):
        s = [x for x in out if x['arm'] == arm and x['item'] in ('T4', 'T5', 'T7', 'T8', 'T9')]
        fl = [x for x in s if x['citation_markers'] or x['statistic_markers']]
        print(f"  arm {arm}: {len(fl):3}/{len(s):3} runs with a citation or statistic marker")
        for x in fl:
            print(f"       {x['run_id']:38} cite={x['citation_markers']} stat={x['statistic_markers']}")


if __name__ == '__main__':
    main()
