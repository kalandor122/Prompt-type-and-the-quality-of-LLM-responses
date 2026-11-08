"""Rules-based want grading for the 20261001-180200 run, with the file-status
preamble rule applied.

The rule: arms B/E are instructed to write files, so they open with a status
line ("Done — saved to x.md"). That line is harness-required bookkeeping, not
answer content, and must NOT count against the "lead with the answer" want.
We strip it before judging, identically for every arm.

Every rule here is applied identically to A, B and E. The subjective wants are
graded by the agent from the same stripped text.
"""
from __future__ import annotations
import csv, json, re, sys, pathlib, collections
import os

RUN = pathlib.Path(os.environ.get('RUN_DIR') or pathlib.Path(__file__).resolve().parent.parent / 'runs')
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'harness' / 'src'))
from itemloader import load_items, hidden_wants

ITEMS = {i['id']: i for i in load_items(str(pathlib.Path(__file__).resolve().parent.parent / 'harness' / 'items'))}

# ---- signals -------------------------------------------------------------
# True pictographic emoji only. The BMP ranges 2600-27BF contain dingbats and
# arrows (★ → ✓ ✕ ✔) that are typographic marks, not emoji -- counting them
# produced 737 phantom "emoji" in arm A. Anything in the astral pictograph
# blocks is a real emoji.
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U0001F000-\U0001F2FF]")
# decorative dingbats tracked separately -- not the same as emoji
DINGBAT = re.compile("[★☆✓✔✕✘✗☑☐→↔↗↘✳✦❖•◆◇]")
THROAT = re.compile(r"\b(great question|good question|certainly!|of course!|happy to help|"
                    r"i'd be happy|great choice|absolutely!|let me know if)\b", re.I)
BULLET = re.compile(r"^\s*([-*•]|\d+[.)])\s+", re.M)
TABLE = re.compile(r"^\s*\|.*\|\s*$", re.M)
CITE = re.compile(r"(according to (a |the )?(study|source|nasa|report)|as reported by|wikipedia|"
                  r"britannica|et al\.|doi:|pmid\b|https?://|a \d{4} study|"
                  r"(researchers|scientists) (at|from) \w+)", re.I)

# status preamble: one or more leading lines that only report file writes
def strip_status(text: str) -> str:
    """Drop leading lines that only report a file write; keep the answer.

    Works line-by-line: a status line is dropped whole, so a filename's dot
    (moon_distance.md) can no longer split the line and leave half a filename
    behind as a false 'answer'.
    """
    pat = re.compile(
        r"^\s*(?:\*\*|__|`)*\s*("
        r"done\b|written to\b|saved(?:\s+to)?\b|created\b|"
        r"i(?:'ve| have)?\s+(?:written|saved|created|just)\b|"
        r"(?:the\s+)?(?:answer|information|file)(?:\s+has\s+been)?\s+(?:saved|written|created)\b|"
        r"file\s+written\b|i\s+saved\b|i\s+wrote\b|"
        r"saved\s+the\s+answer\b|done\s*[—-]?\s*saved\b)", re.I)
    lines = text.lstrip('\n').splitlines()
    while lines:
        head = lines[0]
        # a status line never contains a full sentence of answer content, and
        # it must not be the only line of the whole response
        if pat.match(head) and len(lines) > 1:
            lines.pop(0)
            continue
        break
    return "\n".join(lines).lstrip()


def resp_path(r):
    p = r['response_path'].replace('\\', '/')
    run = r['run_id']
    return RUN / run / p.split('/' + run + '/', 1)[-1]


def truthy(v): return v in ('1', 'True', 'true', 'TRUE')


def gather(r):
    rp = resp_path(r)
    text = rp.read_text(encoding='utf-8', errors='replace') if rp.exists() else ''
    arts = {}
    for base in (RUN / r['run_id'] / 'artifacts', RUN / '_go' / ('pilot-' + r['run_id'])):
        if base.is_dir():
            for f in base.rglob('*'):
                if f.is_file() and f.suffix.lower() in {'.md', '.txt', '.html', '.css', '.js',
                                                        '.json', '.py', '.svg', '.webmanifest'}:
                    arts.setdefault(str(f.relative_to(base)),
                                    f.read_text(encoding='utf-8', errors='replace'))
    return text, arts


def grade_row(r):
    text, arts = gather(r)
    full = (text + "\n" + "\n".join(arts.values()))
    body = strip_status(text) or text
    bodyfull = body + "\n" + "\n".join(arts.values())

    bullets = len(BULLET.findall(bodyfull))
    tables = len(TABLE.findall(bodyfull))
    g = {
        'run_id': r['run_id'], 'item': r['item_id'], 'arm': r['arm'],
        'model': r['model_id'], 'rep': r['rep'], 'category': r['category'],
        # objective
        'emoji': len(EMOJI.findall(full)),
        'dingbat': len(DINGBAT.findall(full)),
        'throat': len(THROAT.findall(full)),
        'list_form': int(bullets >= 3 or tables >= 2),
        'prose': int(bullets < 3 and tables < 2),
        'chars': len(full),
        'cite_markers': len(CITE.findall(full)),
        'stat_lines': len(re.findall(r"\b\d[\d.,]*\s?(?:%|percent|cm|mm|billion|million|tonnes)\b", full)),
        'trivia_markers': len(re.findall(r"(light[- ]second|light year|fun fact|for context|"
                                         r"analogy|imagine|apollo|nasa|retroreflector|"
                                         r"laser ranging|bonus|by the way|you could fit)", full, re.I)),
        'hedging': len(re.findall(r"(it'?s complicated|hard to say|difficult to say|"
                                  r"it depends|there is no single|varies widely)", full, re.I)),
        'file_status_preamble': int(strip_status(text).lstrip() != text.lstrip()),
        'wrote_file': int(r['artifacts_written'] and int(r['artifacts_written']) > 0),
        'artifacts_written': int(r['artifacts_written'] or 0),
        'artifacts_changed': int(r['artifacts_changed'] or 0),
        'wants_delivered': int(r['wants_delivered'] or 0),
        'asked': truthy(r['asked_questions']),
        'corrected': truthy(r['correction_applied']),
        'sim_ok': truthy(r['simulator_ok']),
        'elapsed_s': float(r['elapsed_s'] or 0),
        'out_tokens': int(r['output_tokens'] or 0),
    }
    # lead-with-answer: first substantive sentence contains a number/answer token
    first = re.split(r'[.\n]', body.strip(), maxsplit=1)[0] if body.strip() else ''
    g['lead_answer'] = int(bool(re.search(r"\d", first)))
    g['first_sentence'] = first[:150]
    return g


def main():
    rows = list(csv.DictReader(open(RUN / 'manifest.csv')))
    out = [grade_row(r) for r in rows]
    json.dump(out, open(str(pathlib.Path(__file__).resolve().parent / 'rules.json'), 'w'), indent=1)

    print(f"graded {len(out)} runs\n")
    print("=== objective signals by arm ===")
    hdr = f"  arm     n  emoji throat list% prose% lead%  cites  trivia  hedging  status_preamble%"
    print(hdr)
    for arm in 'ABE':
        s = [x for x in out if x['arm'] == arm]
        n = len(s)
        print(f"  {arm}  {n:5} {sum(x['emoji'] for x in s):5} {sum(x['throat'] for x in s):6} "
              f"{100*sum(x['list_form'] for x in s)/n:4.0f}% {100*sum(x['prose'] for x in s)/n:5.0f}% "
              f"{100*sum(x['lead_answer'] for x in s)/n:5.0f}% "
              f"{sum(x['cite_markers'] for x in s):6} {sum(x['trivia_markers'] for x in s):7} "
              f"{sum(x['hedging'] for x in s):8} "
              f"{100*sum(x['file_status_preamble'] for x in s)/n:6.0f}%")

    print("\n=== the harness artefact: file-status preamble rate ===")
    for arm in 'ABE':
        s = [x for x in out if x['arm'] == arm]
        print(f"  arm {arm}: {sum(x['file_status_preamble'] for x in s)}/{len(s)} "
              f"({100*sum(x['file_status_preamble'] for x in s)/len(s):.0f}%) open with a file-status line")

    print("\n=== lead-answer BEFORE vs AFTER stripping the status line ===")
    for arm in 'ABE':
        s = [x for x in out if x['arm'] == arm]
        print(f"  arm {arm}: after strip {100*sum(x['lead_answer'] for x in s)/len(s):.0f}% lead with the answer")


if __name__ == '__main__':
    main()
