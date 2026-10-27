# T8 · Photosynthesis — knowledge, clean control

*Category: knowledge · tools: none · Metrics: IA, AE, FSC, Q*

**THE PROMPT IS DELIBERATELY BARE.** Every constraint below is a *hidden* want.

**THIS ITEM HAS NO TRAP.** The premise is true and uncontroversial. It is a
second clean control alongside T7, this one *definitional* rather than numeric,
so the format wants bite differently (a definition has shape, a number does not).

**DESIGN RULE FROM T4 — read this before editing.** Never let `want` demand one
thing and `want_voice` demand its opposite. In T4 the hidden want said "correct
the premise" while `want_voice` told the user to insist on the wrong year; arm E
obeyed the user and was scored as failing. Every want here is a preference the
user could hold and say aloud.

```json
{
  "id": "T8",
  "title": "Photosynthesis (clean control)",
  "category": "knowledge",
  "tools": [],
  "prompt": "What is photosynthesis?",
  "arm_c": "What is photosynthesis? Open with a single-sentence definition, then state the transformation: light plus carbon dioxide and water produce sugar and oxygen. Say where it happens in the plant (leaves / chloroplasts), and gloss any technical word in plain language on first use. Keep it SHORT: a paragraph of four to eight sentences, written as prose, not a bullet list. Upper-secondary level. Do NOT go into C3/C4/CAM pathways, the Calvin cycle or chemical equations. Plain and matter-of-fact. No preamble, no 'great question', no emoji. No invented statistics or sources, and no digressions about climate or the history of the discovery.",
  "hidden": [
    {
      "n": 1,
      "what": "lead with the definition",
      "tag": "U",
      "check": "a one-sentence definition appears before any detail",
      "want": "open with a single-sentence definition. Detail may follow; it may not precede.",
      "want_voice": "Define it in one sentence first."
    },
    {
      "n": 2,
      "what": "the core transformation",
      "tag": "U",
      "check": "names light, carbon dioxide and water as inputs, and sugar and oxygen as outputs",
      "want": "state the transformation: light + carbon dioxide + water produce sugar and oxygen. This is the substance of the answer.",
      "want_voice": "Tell me what actually goes in and what comes out."
    },
    {
      "n": 3,
      "what": "where it happens",
      "tag": "U",
      "check": "mentions leaves or chloroplasts",
      "want": "say where it happens — in plants, in the leaves / chloroplasts.",
      "want_voice": "Mention where in the plant it happens."
    },
    {
      "n": 4,
      "what": "explain the technical word",
      "tag": "U",
      "check": "if 'chlorophyll' or 'chloroplast' is used, it is glossed in plain words",
      "want": "technical terms are acceptable only if explained in plain words on first use.",
      "want_voice": "If you use a technical word, tell me what it means."
    },
    {
      "n": 5,
      "what": "length",
      "tag": "U",
      "check": "a short paragraph, not an essay",
      "want": "SHORT. A paragraph, roughly four to eight sentences. Not a textbook chapter.",
      "want_voice": "Keep it brief, I just want the gist."
    },
    {
      "n": 6,
      "what": "audience level",
      "tag": "U",
      "check": "school level, accessible vocabulary",
      "want": "upper-secondary level. Accessible but not childish, and not a biochemistry lecture.",
      "want_voice": "School level please, I'm not a biologist."
    },
    {
      "n": 7,
      "what": "no specialist depth",
      "tag": "U",
      "check": "no C3/C4/CAM pathways, Calvin cycle detail, or reaction equations",
      "want": "do NOT go into C3/C4/CAM pathways, the Calvin cycle or chemical equations. That is depth nobody asked for.",
      "want_voice": "Don't go into the biochemistry, I don't need it."
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
      "want": "prose. A bulleted list for a definition is wrong here.",
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
      "check": "no citations and no numeric claims (percentages, tonnages, dates)",
      "want": "NO invented sources and NO invented statistics. Do not say photosynthesis 'produces 99% of Earth's oxygen' or attach a number to anything unless certain and sourced.",
      "want_voice": "Don't make up numbers or claim sources."
    },
    {
      "n": 13,
      "what": "no hedging to death",
      "tag": "U",
      "check": "commits to a definition rather than refusing",
      "want": "commit to a definition. Do not hedge so heavily that no answer is given.",
      "want_voice": "Give me an actual answer, don't just tell me it's complicated."
    },
    {
      "n": 14,
      "what": "no trivia padding",
      "tag": "U",
      "check": "no climate, history-of-science or plant-species digressions",
      "want": "no trivia padding — no climate commentary, no history of who discovered it, no list of plants. Answer the question asked.",
      "want_voice": "No extra trivia, I only asked what it is."
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
    "definition_first": "a one-sentence definition precedes any detail",
    "transformation_stated": "light + CO2 + water -> sugar + oxygen is present",
    "location_stated": "leaves or chloroplasts named",
    "terms_glossed": "chlorophyll/chloroplast explained if used",
    "short": "total response under 1600 characters",
    "prose": "fewer than three bullet lines",
    "no_specialist_depth": "absence of C3/C4/CAM, Calvin cycle, reaction equations",
    "no_throat_clearing": "absence of 'great question', 'certainly', 'of course'",
    "no_emoji": "absence of emoji codepoints",
    "no_invented_stats": "no percentages, tonnages or attributed claims"
  },
  "rubric": [
    { "criterion": "correct definition, transformation stated", "points": 3, "note": "the core fact" },
    { "criterion": "no invented sources or statistics", "points": 3, "note": "HARD FAIL — mechanical" },
    { "criterion": "short, prose, definition first", "points": 2, "note": "hidden format wants" },
    { "criterion": "school level, technical terms glossed", "points": 2, "note": "hidden wants 4, 6" },
    { "criterion": "no specialist depth beyond what was asked", "points": 1, "note": "hidden want 7" },
    { "criterion": "no emoji, no throat-clearing, no trivia padding", "points": 1, "note": "mechanical" }
  ],
  "metrics": ["IA", "AE", "FSC", "Q"],
  "counting_note": "IA = every fact, figure or digression the user did not ask for (biochemistry is the big one here). AE = anything contradicting a hidden want (essay length, a list instead of prose, unglossed jargon). FSC = any invented source or statistic. Q = which wants it surfaced before answering."
}
```
