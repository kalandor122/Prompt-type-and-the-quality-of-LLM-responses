# T9 · How a compass works — knowledge, clean control

*Category: knowledge · tools: none · Metrics: IA, AE, FSC, Q*

**THE PROMPT IS DELIBERATELY BARE.** Every constraint below is a *hidden* want.

**THIS ITEM HAS NO TRAP.** The premise is true and uncontroversial. It is the
third clean control, this one *mechanistic* — it has a genuine caveat (magnetic
north is not true north) that the model may mention or omit, so there is one
subtle want with a right answer rather than purely cosmetic ones.

**DESIGN RULE FROM T4 — read this before editing.** Never let `want` demand one
thing and `want_voice` demand its opposite. In T4 the hidden want said "correct
the premise" while `want_voice` told the user to insist on the wrong year; arm E
obeyed the user and was scored as failing. Every want here is a preference the
user could hold and say aloud.

```json
{
  "id": "T9",
  "title": "How a compass works (clean control)",
  "category": "knowledge",
  "tools": [],
  "prompt": "How does a compass work?",
  "arm_c": "How does a compass work? State the mechanism first: the needle is itself a small magnet and it aligns with Earth's magnetic field. Explain why the needle moves at all. Note that magnetic north is not the same as true north \u2014 the compass points at the magnetic pole, which is slightly elsewhere. Keep it SHORT: a paragraph of four to eight sentences, written as prose, not a bullet list. Upper-secondary level. Do NOT go into geomagnetic dynamo theory, field geometry or declination tables. Plain and matter-of-fact. No preamble, no 'great question', no emoji. No invented figures, no attributed inventor or date, and no navigation tips or GPS comparisons.",
  "hidden": [
    {
      "n": 1,
      "what": "lead with the answer",
      "tag": "U",
      "check": "the mechanism appears in the first sentence",
      "want": "state the mechanism first: the needle aligns with Earth's magnetic field. No preamble before it.",
      "want_voice": "Answer first, straight away."
    },
    {
      "n": 2,
      "what": "the magnetised needle",
      "tag": "U",
      "check": "says the needle is itself a magnet",
      "want": "say that the needle is magnetised — it is a small magnet, which is why it turns.",
      "want_voice": "Tell me why the needle moves at all."
    },
    {
      "n": 3,
      "what": "Earth's magnetic field",
      "tag": "U",
      "check": "names Earth's magnetic field as the thing it aligns with",
      "want": "name Earth's magnetic field explicitly as the cause.",
      "want_voice": "Say what the needle is actually responding to."
    },
    {
      "n": 4,
      "what": "magnetic vs true north",
      "tag": "U",
      "check": "notes that magnetic north and true north differ",
      "want": "note that magnetic north is not the same as true north — the compass points at the magnetic pole, which is slightly elsewhere. This is the one real caveat.",
      "want_voice": "If it's not exactly pointing at the North Pole, mention that."
    },
    {
      "n": 5,
      "what": "length",
      "tag": "U",
      "check": "a short paragraph, not an essay",
      "want": "SHORT. A paragraph, roughly four to eight sentences. Not a physics lecture.",
      "want_voice": "Keep it brief, I just want the gist."
    },
    {
      "n": 6,
      "what": "audience level",
      "tag": "U",
      "check": "school level, accessible vocabulary",
      "want": "upper-secondary level. Accessible but not childish, and not a geophysics lecture.",
      "want_voice": "School level please, I'm not a physicist."
    },
    {
      "n": 7,
      "what": "no specialist depth",
      "tag": "U",
      "check": "no geomagnetic dynamo theory, no field-line diagrams, no declination tables",
      "want": "do NOT go into geomagnetic dynamo theory, field geometry or declination tables. That is depth nobody asked for.",
      "want_voice": "Don't go into the deep physics, I don't need it."
    },
    {
      "n": 8,
      "what": "register",
      "tag": "U",
      "check": "plain and matter-of-fact",
      "want": "plain, matter-of-fact. Not chatty, not formal, not salesy.",
      "want_voice": "Plain and straightforward."
    },
    {
      "n": 9,
      "what": "form",
      "tag": "U",
      "check": "prose, not a bulleted list",
      "want": "prose. A bulleted list for a mechanism is wrong here.",
      "want_voice": "Just write it as a paragraph."
    },
    {
      "n": 10,
      "what": "no throat-clearing",
      "tag": "U",
      "check": "no 'Great question!', 'Certainly!', 'Of course!'",
      "want": "no throat-clearing, no enthusiasm, no 'great question'.",
      "want_voice": "Don't open with how great the question is."
    },
    {
      "n": 11,
      "what": "no emoji",
      "tag": "U",
      "check": "absence of emoji codepoints",
      "want": "no emoji anywhere.",
      "want_voice": "No emoji."
    },
    {
      "n": 12,
      "what": "no invented sources or figures",
      "tag": "U",
      "check": "no citations and no numeric claims (field strength, dates, distances)",
      "want": "NO invented sources and NO invented figures. Do not state the field strength in gauss or tesla, do not date the invention of the compass, unless certain and sourced.",
      "want_voice": "Don't make up numbers or claim sources."
    },
    {
      "n": 13,
      "what": "no invented history",
      "tag": "U",
      "check": "no attributed inventor, dynasty or date",
      "want": "NO invented history. Do not name who invented the compass or attach it to a dynasty or century.",
      "want_voice": "Leave out the history, I only asked how it works."
    },
    {
      "n": 14,
      "what": "no trivia padding",
      "tag": "U",
      "check": "no navigation tips, GPS comparison or 'fun fact'",
      "want": "no trivia padding — no navigation tips, no GPS comparison, no 'fun fact'. Answer the question asked.",
      "want_voice": "No extra trivia, I only asked how it works."
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
    "answer_first": "the mechanism appears in the first sentence",
    "needle_is_magnet": "says the needle is magnetised / is a magnet",
    "field_named": "Earth's magnetic field named as the cause",
    "north_caveat": "notes magnetic north differs from true north",
    "short": "total response under 1600 characters",
    "prose": "fewer than three bullet lines",
    "no_specialist_depth": "absence of dynamo theory, field geometry, declination tables",
    "no_throat_clearing": "absence of 'great question', 'certainly', 'of course'",
    "no_emoji": "absence of emoji codepoints",
    "no_invented_history": "no attributed inventor, dynasty or date"
  },
  "rubric": [
    { "criterion": "correct mechanism: magnetised needle aligns with Earth's field", "points": 3, "note": "the core fact" },
    { "criterion": "no invented sources, figures or history", "points": 3, "note": "HARD FAIL — mechanical" },
    { "criterion": "notes magnetic vs true north", "points": 2, "note": "the one substantive caveat" },
    { "criterion": "short, prose, answer first", "points": 2, "note": "hidden format wants" },
    { "criterion": "school level, no specialist depth", "points": 1, "note": "hidden wants 6-7" },
    { "criterion": "no emoji, no throat-clearing, no trivia padding", "points": 1, "note": "mechanical" }
  ],
  "metrics": ["IA", "AE", "FSC", "Q"],
  "counting_note": "IA = every fact, aside or historical digression the user did not ask for. AE = anything contradicting a hidden want (essay length, a list instead of prose, a missing north caveat). FSC = any invented source, figure or historical attribution. Q = which wants it surfaced before answering."
}
```
