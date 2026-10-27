"""Verify every model slug against the live OpenRouter catalogue before spending.

`GET /models` is public and unauthenticated, so this runs with no API key. It is
the anti-hallucination step for model selection: a slug that is not in the
catalogue does not exist, and a price that disagrees with config.json is a bug
waiting to become a surprise invoice.

    python src/probe_models.py            # check config.json's models
    python src/probe_models.py --extra some/vendor-slug another/one
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from openrouter import probe_models  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config.json"))
    ap.add_argument("--extra", nargs="*", default=[],
                    help="additional slugs to look up")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    entries = [(m["id"], m["or_slug"], m.get("price_in"), m.get("price_out"))
               for m in cfg.get("models", [])]
    sim = (cfg.get("simulator") or {}).get("id")
    if sim:
        entries.append(("simulator", sim, None, None))
    entries += [(s, s, None, None) for s in args.extra]

    slugs = [e[1] for e in entries]
    try:
        rows = probe_models(slugs)
    except Exception as e:  # network failure is worth reporting, not a traceback
        print(f"could not reach {cfg.get('openrouter', {}).get('base', 'OpenRouter')}: {e}")
        return 2

    by_slug = {r["slug"]: r for r in rows}
    print(f"{'model id':<28}{'slug':<42}{'live $/MTok in/out':<22}"
          f"{'config':<18}{'ctx':>8}  status")
    print("-" * 128)

    missing, mismatched = [], []
    for mid, slug, cfg_in, cfg_out in entries:
        r = by_slug.get(slug, {"found": False})
        if not r.get("found"):
            print(f"{mid:<28}{slug:<42}{'—':<22}{'—':<18}{'—':>8}  NOT FOUND")
            missing.append(slug)
            continue
        live = f"{r['price_in']:.3f} / {r['price_out']:.3f}"
        shown_cfg = (f"{cfg_in:.3f}/{cfg_out:.3f}" if cfg_in is not None else "—")
        status = "ok"
        if cfg_in is not None:
            if abs(r["price_in"] - cfg_in) > 0.005 or abs(r["price_out"] - cfg_out) > 0.005:
                status = "PRICE CHANGED"
                mismatched.append((slug, cfg_in, cfg_out, r["price_in"], r["price_out"]))
        ctx = r.get("context") or 0
        print(f"{mid:<28}{slug:<42}{live:<22}{shown_cfg:<18}{ctx:>8}  {status}")

    print()
    if missing:
        print(f"!! {len(missing)} slug(s) do not exist on OpenRouter:")
        for s in missing:
            print(f"   {s}")
    if mismatched:
        print(f"!! {len(mismatched)} price(s) disagree with config.json:")
        for s, ci, co, li, lo in mismatched:
            print(f"   {s}: config {ci:.3f}/{co:.3f} -> live {li:.3f}/{lo:.3f}")
    if not missing and not mismatched:
        print("all slugs exist and every price matches config.json.")
    return 1 if (missing or mismatched) else 0


if __name__ == "__main__":
    raise SystemExit(main())
