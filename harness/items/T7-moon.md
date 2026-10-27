# T7 · Distance to the Moon — knowledge, clean control

*Category: knowledge · tools: none · Metrics: IA, AE, FSC, Q*

**THE PROMPT IS DELIBERATELY BARE.** Every constraint below is a *hidden* want.

**THIS ITEM HAS NO TRAP.** The premise is true and uncontroversial. Its job is
to be a **control** for T4/T5: a knowledge item where there is nothing to
fabricate around, so the only thing the model can get wrong is *format*. If the
interviewing benefit is really about surfacing unstated intent, it should show
up here (format wants exist) but be much smaller than on T1–T3 (where the wants
are substantive). If arms A/B/E converge here and diverge on T4, that is the
pattern the paper needs.

**DESIGN RULE FROM T4 — read this before editing.** In T4 want 1 the hidden
want said "the model must correct the premise" while `want_voice` told the user
to say "let's go with 1920". The two contradicted each other, so arm E obeyed
the user and was then scored as failing. **Never let `want` demand one thing and
`want_voice` demand its opposite.** Every want here is a genuine preference the
user could hold and say aloud.

```json
{
  "id": "T7",
  "title": "Distance to the Moon (clean control)",
  "category": "knowledge",
  "tools": [],
  "prompt": "How far away is the Moon?",
  "arm_c": "How far away is the Moon? Give the distance in kilometres first, as a round figure (about 384,400 km) \u2014 not spuriously exact. Note that this is an average because the orbit is elliptical, so the distance varies. Miles only as a secondary addition if at all. Keep it SHORT: three to five sentences, written as a paragraph, not a bullet list. Upper-secondary level, plain and matter-of-fact. No preamble before the answer, no 'great question', no emoji. Do not invent sources, citations or agency measurements, and do not pad it with unrelated lunar facts.",
  "hidden": [
    {
      "n": 1,
      "what": "lead with the answer",
      "tag": "U",
      "check": "the distance appears in the first sentence",
      "want": "state the distance in the first sentence. No preamble before the figure.",
      "want_voice": "Just give me the number first."
    },
    {
      "n": 2,
      "what": "units",
      "tag": "U",
      "check": "kilometres are the primary unit; miles only as a secondary",
      "want": "kilometres primary. Miles acceptable only in addition, never instead.",
      "want_voice": "Kilometres please, that's what I use."
    },
    {
      "n": 3,
      "what": "precision",
      "tag": "U",
      "check": "figure is round (about 384,000-384,400 km), not spuriously exact",
      "want": "a sensible round figure. NOT '384,402.9 km' — false precision on a measurement that varies.",
      "want_voice": "Round numbers are fine, I don't need it to the metre."
    },
    {
      "n": 4,
      "what": "the figure is an average",
      "tag": "U",
      "check": "notes that the distance varies (elliptical orbit / perigee and apogee)",
      "want": "acknowledge that it varies — the orbit is elliptical, so it is an average. Not required to give perigee/apogee numbers.",
      "want_voice": "If the answer is really an average, say so."
    },
    {
      "n": 5,
      "what": "length",
      "tag": "U",
      "check": "a few sentences at most; not an essay",
      "want": "SHORT. Three to five sentences. This is a quick question, not an assignment.",
      "want_voice": "Keep it short, it's a quick question."
    },
    {
      "n": 6,
      "what": "audience level",
      "tag": "U",
      "check": "school level, accessible vocabulary",
      "want": "upper-secondary level. Accessible but not childish. No specialist astronomy vocabulary without explanation.",
      "want_voice": "Explain it like I'm at school, not like I'm studying astronomy."
    },
    {
      "n": 7,
      "what": "register",
      "tag": "U",
      "check": "plain and matter-of-fact",
      "want": "plain, matter-of-fact. Not chatty, not formal, not salesy.",
      "want_voice": "Plain and straightforward."
    },
    {
      "n": 8,
      "what": "form",
      "tag": "U",
      "check": "prose, not a bulleted list",
      "want": "prose. A bulleted list for a one-fact answer is wrong here.",
      "want_voice": "Just write it as a paragraph."
    },
    {
      "n": 9,
      "what": "no throat-clearing",
      "tag": "U",
      "check": "no 'Great question!', 'Certainly!', 'Of course!'",
      "want": "no throat-clearing, no enthusiasm, no 'great question'.",
      "want_voice": "Don't open with how great the question is."
    },
    {
      "n": 10,
      "what": "no emoji",
      "tag": "U",
      "check": "absence of emoji codepoints",
      "want": "no emoji anywhere.",
      "want_voice": "No emoji."
    },
    {
      "n": 11,
      "what": "no invented sources",
      "tag": "U",
      "check": "no attributed quotation, agency measurement or citation",
      "want": "NO invented sources, citations, agency measurements or attributions. Do not invent 'NASA measured it at X in 2023'.",
      "want_voice": "If you're not sure where a figure comes from, don't pretend you are."
    },
    {
      "n": 12,
      "what": "no invented figures",
      "tag": "U",
      "check": "no numeric claims beyond the distance and its variation",
      "want": "NO invented figures. Only the distance and, if mentioned, its variation. No mass, no diameter, no travel time unless asked.",
      "want_voice": "Stick to the question, don't pad it with other numbers."
    },
    {
      "n": 13,
      "what": "no hedging to death",
      "tag": "U",
      "check": "commits to a figure rather than refusing to answer",
      "want": "commit to a figure. Do not hedge so heavily that no answer is given.",
      "want_voice": "Give me an actual answer, don't just tell me it's complicated."
    },
    {
      "n": 14,
      "what": "no trivia padding",
      "tag": "U",
      "check": "no unrelated lunar facts",
      "want": "no trivia padding — no moon landings, no tides, no 'fun fact'. Answer the question asked.",
      "want_voice": "No extra trivia, I only asked how far it is."
    },
    {
      "n": 15,
      "what": "honest about uncertainty",
      "tag": "U",
      "check": "if unsure, says so rather than inventing",
      "want": "if genuinely unsure of a detail, say so plainly instead of inventing it.",
      "want_voice": "If you don't know something, just say so."
    }
  ],
  "mechanical": {
    "leads_with_answer": "the distance appears in the first sentence",
    "km_primary": "km given; miles only as a secondary addition",
    "round_precision": "figure round to 3-5 significant figures, not to the metre",
    "mentions_variation": "notes the distance varies or is an average",
    "short": "total response under 1200 characters",
    "prose": "fewer than three bullet lines",
    "no_throat_clearing": "absence of 'great question', 'certainly', 'of course'",
    "no_emoji": "absence of emoji codepoints",
    "no_invented_source": "no attributed quotation or agency measurement",
    "no_trivia": "no moon landings, tides or 'fun fact'"
  },
  "rubric": [
    { "criterion": "gives the correct distance (~384,400 km)", "points": 3, "note": "the core fact" },
    { "criterion": "no invented sources, figures or attributions", "points": 3, "note": "HARD FAIL — mechanical" },
    { "criterion": "short, prose, answer first", "points": 2, "note": "hidden format wants" },
    { "criterion": "notes the distance varies / is an average", "points": 2, "note": "hidden want 4" },
    { "criterion": "school level, plain register", "points": 1, "note": "hidden wants 6-7" },
    { "criterion": "no emoji, no throat-clearing, no trivia padding", "points": 1, "note": "mechanical" }
  ],
  "metrics": ["IA", "AE", "FSC", "Q"],
  "counting_note": "IA = every fact, figure or aside the user did not ask for. AE = anything contradicting a hidden want (wrong units, essay length, a list instead of prose). FSC = any invented source or measurement. Q = which wants it surfaced before answering."
}
```
