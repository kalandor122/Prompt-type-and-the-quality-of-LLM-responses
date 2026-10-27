# OpenRouter quickstart

One API key covers all eight test models and the simulator. Nothing else needs
signing up.

## 1. Get a key

https://openrouter.ai/settings/keys — then put it in one of:

    ~/.hermes/.env      ~/.env      ./.env

as a plain line:

    OPENROUTER_API_KEY=sk-or-v1-...

(or `export` it). The harness reads whichever it finds first and does not
overwrite a real exported value.

## 2. Verify the models before spending anything

    python src/probe_models.py

This hits `GET /models`, which is public and needs no key. It checks that every
slug in config.json actually exists, prints the **live** price per model, and
flags any price that has drifted from what config.json claims. A slug that is
not in that catalogue does not exist — this is the check that stops a typo from
becoming a wasted evening.

You can also look up arbitrary slugs:

    python src/probe_models.py --extra openai/gpt-6-sol nvidia/nemotron-3.5-lightning

## 3. Measure before you budget

    python src/run.py --items T6 --arms A

One agentic run per model. Then read `input_tokens`, `output_tokens` and
`cost_usd` out of `runs/<stamp>/manifest.csv` and work out the real per-run cost
rather than trusting an estimate. `cost_source` says whether that figure is the
actual dollars OpenRouter charged (`reported`) or our arithmetic from list
prices (`estimated`) — the former is what you want.

## 4. Run

    python src/run.py                       # full matrix
    python src/run.py --resume              # continue an interrupted run
    python src/report.py                    # grading sheets for the newest run

## What changed vs. the OpenCode build

- `mode` is `gateway`, `engine` is `openrouter`. All eight models go through the
  same endpoint with the same three tools (`list_dir`, `read_file`,
  `write_file`), so the serving stack is constant across the capability axis —
  that removes provider differences as a confound.
- No local inference. Qwen3.5 9B is served like everything else.
- Each run can do up to `max_tool_turns` (default 40) tool calls, looped inside
  one `complete()` call the way `opencode run` did. Files land in the run's
  sandbox and are copied to `runs/<stamp>/<run_id>/artifacts/` afterwards.
- `usage.include` asks OpenRouter for the real cost of every call; the manifest
  prefers that over the estimate.
- Nemotron 3 Ultra is in (AA index 47.7, $0.60/$2.40) — it was previously
  excluded only because its price was unknown.

## Caveats worth keeping in mind

- OpenRouter may route one request to one upstream provider and the next to
  another. It records which provider served the call; if you need strict
  provider pinning, that is not available here and belongs in the limitations.
- Muse Spark 1.3 *Contributor* is cheap because Meta trains on the conversation
  data. That is a disclosure in the paper, and it raises a contamination
  question for anyone replicating the study later.
- The "heavy" cost scenario (400k in / 110k out per agentic run) is a guess.
  Measure it — see step 3.
