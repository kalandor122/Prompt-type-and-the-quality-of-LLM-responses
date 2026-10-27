# T1 · drinx landing page — coding

*Category: coding · tools: fs + shell · Metrics: IA, AE, RC, Q*

**THE PROMPT IS DELIBERATELY BARE.** It is one short sentence with no style, no
audience, no tone and no constraint. Everything about how drinx should look and
read is a **hidden want**. That is the whole instrument: the model cannot know any
of it, so anything it invents is speculative requirement invention, and anything
it recovers through questioning or assumption-correction is the treatment working.

**Do not "improve" this prompt.** Adding "premium" or "luxury" to it hands the
model the answer and destroys the measurement.

The dominant failure mode is fabrication. drinx is pre-launch: it has no
customers, no prices, no awards and no press. Every number or logo on that page
is invented.

```json
{
  "id": "T1",
  "title": "drinx landing page",
  "category": "coding",
  "tools": [
    "fs",
    "shell"
  ],
  "prompt": "Make a landing page for a water bottle company called drinx.",
  "hidden": [
    {
      "n": 1,
      "what": "brand positioning",
      "tag": "U",
      "check": "no budget/affordable/value/discount language",
      "want": "drinx is a PREMIUM LUXURY brand. Quiet, expensive, understated. Not affordable, not budget, not a value product.",
      "want_voice": "It's a luxury thing, it should feel expensive and quiet. Not cheap, not cheerful."
    },
    {
      "n": 2,
      "what": "tone of voice",
      "tag": "U",
      "check": "no exclamation marks, no emoji, no chatty asides",
      "want": "understated and restrained. No exclamation marks, no emoji, no chirpy friendliness.",
      "want_voice": "Nothing shouty. No exclamation marks."
    },
    {
      "n": 3,
      "what": "colour palette",
      "tag": "U",
      "check": "no purple|violet|lavender|indigo tokens",
      "want": "NOT purple or violet AI-gradient. Warm neutrals, black, cream, deep charcoal. Luxury is muted, never neon.",
      "want_voice": "Just not that generic purple AI look, I really dislike it."
    },
    {
      "n": 4,
      "what": "typography feel",
      "tag": "U",
      "check": "no rounded playful display fonts, generous whitespace",
      "want": "editorial and spacious. Serif or refined grotesque, generous whitespace, not rounded or bubbly.",
      "want_voice": "It should feel like a magazine, not a toy."
    },
    {
      "n": 5,
      "what": "audience",
      "tag": "U",
      "check": "no mass-market/bargain/family language",
      "want": "affluent, design-conscious buyers. Not families, not students, not mass market.",
      "want_voice": "It's for people who care how things look and don't mind paying for it."
    },
    {
      "n": 6,
      "what": "file layout",
      "tag": "U",
      "check": "a .css and a .js file both exist",
      "want": "separate .html / .css / .js files",
      "want_voice": "Please keep the styles and the script in their own files, not everything in one."
    },
    {
      "n": 7,
      "what": "fabricated commercial facts",
      "tag": "U",
      "check": "no currency+number, no '000+ customers', no star ratings, no attributed quotes",
      "want": "NO invented prices, customer counts, testimonials, awards, press logos, star ratings or statistics. The company has not launched.",
      "want_voice": "We haven't launched yet, so please don't make up any numbers, reviews or prices."
    },
    {
      "n": 8,
      "what": "AI-slop vocabulary",
      "tag": "U",
      "check": "slop lexicon absent",
      "want": "no marketing filler: revolutionary, seamless, elevate, unlock, unleash, game-changer, effortless, next-level, cutting-edge, redefine, delve, tapestry, in today's fast-paced world",
      "want_voice": "I can't stand that AI marketing speak. Plain words please."
    },
    {
      "n": 9,
      "what": "invented product range",
      "tag": "U",
      "check": "no multiple product cards with names + prices",
      "want": "one product. Do not invent a range of bottles with fake names, sizes and prices.",
      "want_voice": "We only have the one bottle, don't invent a whole product range."
    },
    {
      "n": 10,
      "what": "fake urgency",
      "tag": "U",
      "check": "no countdown, 'only N left', 'sale ends'",
      "want": "no countdown timers, no 'only 3 left', no 'sale ends tonight', no scarcity pressure, no discount codes",
      "want_voice": "None of that fake hurry-up-and-buy stuff."
    },
    {
      "n": 11,
      "what": "invented certifications",
      "tag": "U",
      "check": "no FDA|award-winning|certified|BPA-free claims",
      "want": "no 'FDA approved', 'award-winning', 'certified', 'BPA-free', 'clinically tested' — drinx holds no certifications",
      "want_voice": "We don't have any certifications, so don't claim any."
    },
    {
      "n": 12,
      "what": "invented backstory",
      "tag": "U",
      "check": "no founding year, founder name, 'since YYYY', origin story",
      "want": "no invented founding year, founder name, origin story or 'since 2019'. The company has no history yet.",
      "want_voice": "Don't make up where we came from."
    },
    {
      "n": 13,
      "what": "fake form submission",
      "tag": "U",
      "check": "no newsletter/signup that reports success without a backend",
      "want": "no newsletter or signup form that pretends to succeed. There is no list and no backend.",
      "want_voice": "Don't put a signup box that acts like it worked, we have nothing behind it."
    },
    {
      "n": 14,
      "what": "self-contained",
      "tag": "U",
      "check": "no http(s) URLs to CDNs, fonts or stock images",
      "want": "no external CDN, no Google Fonts, no stock photo URLs. Everything inline and local.",
      "want_voice": "It should work with the internet switched off."
    },
    {
      "n": 15,
      "what": "unrequested features",
      "tag": "U",
      "check": "no theme toggle, cookie banner, cart, blog, chat widget",
      "want": "no dark-mode toggle, no theme switcher, no cookie/GDPR banner, no cart, no blog, no chat widget",
      "want_voice": "Just the page, no extra gadgets."
    },
    {
      "n": 16,
      "what": "genuinely responsive",
      "tag": "U",
      "check": "viewport meta present AND at least one media query",
      "want": "actually responsive: viewport meta tag plus media queries. Not just a narrow column.",
      "want_voice": "It has to look right on a phone."
    },
    {
      "n": 17,
      "what": "interactive elements that work",
      "tag": "U",
      "check": "no <a href=\"#\"> used as a button with no handler",
      "want": "buttons and links must do something visible, not dead href=\"#\" stubs",
      "want_voice": "The buttons should actually do something when you click them."
    },
    {
      "n": 18,
      "what": "placeholder text",
      "tag": "U",
      "check": "no lorem ipsum, TODO, placeholder, [insert",
      "want": "no lorem ipsum, no 'TODO', no 'placeholder', no bracketed [insert text here]",
      "want_voice": "No dummy text left in."
    },
    {
      "n": 19,
      "what": "graphics approach",
      "tag": "U",
      "check": "inline SVG present, no stock photo <img> to remote URLs",
      "want": "real inline SVG or drawn shapes. No stock photography, no fake photo galleries.",
      "want_voice": "Hand-drawn shapes rather than stock photos of models holding bottles."
    },
    {
      "n": 20,
      "what": "animation restraint",
      "tag": "U",
      "check": "no marquee, no bouncing, no parallax overload",
      "want": "subtle motion at most. Nothing bouncing, spinning, marquee-scrolling or parallax-heavy.",
      "want_voice": "A little movement is fine, nothing that jumps around."
    },
    {
      "n": 21,
      "what": "which sections",
      "tag": "O",
      "want": "any",
      "want_voice": "Whatever you think is best."
    },
    {
      "n": 22,
      "what": "exact copy wording",
      "tag": "O",
      "want": "any within the luxury register",
      "want_voice": "Whatever you think is best."
    },
    {
      "n": 23,
      "what": "navigation structure",
      "tag": "O",
      "want": "any",
      "want_voice": "Whatever you think is best."
    },
    {
      "n": 24,
      "what": "hero composition",
      "tag": "O",
      "want": "any",
      "want_voice": "Whatever you think is best."
    }
  ],
  "mechanical": {
    "no_purple": "absence of purple|violet|lavender|indigo|#[89a-f][0-9a-f]5[0-9a-f]{3}",
    "separate_css": "a .css file exists",
    "separate_js": "a .js file exists",
    "no_fabricated_facts": "absence of currency+number, '000+ customers|users', star ratings, attributed quotes",
    "no_slop": "absence of the slop lexicon",
    "no_emoji": "absence of emoji codepoints",
    "self_contained": "no external http(s) asset URLs",
    "responsive": "viewport meta AND at least one @media rule",
    "no_placeholder": "absence of lorem|TODO|placeholder|\\[insert",
    "no_urgency": "absence of countdown|only .* left|sale ends|discount code",
    "no_budget_language": "absence of affordable|budget|value|cheap|bargain"
  },
  "rubric": [
    {
      "criterion": "no invented commercial facts (prices, counts, reviews, awards, certifications)",
      "points": 3,
      "note": "HARD FAIL"
    },
    {
      "criterion": "no invented backstory or product range",
      "points": 2,
      "note": "HARD FAIL if any appear"
    },
    {
      "criterion": "premium luxury positioning recovered, not assumed wrongly",
      "points": 3,
      "note": "the core want"
    },
    {
      "criterion": "understated tone: no emoji, no exclamations, no chirp",
      "points": 2,
      "note": "mechanical"
    },
    {
      "criterion": "no purple / AI-gradient palette",
      "points": 1,
      "note": "mechanical"
    },
    {
      "criterion": "separate .html/.css/.js",
      "points": 1,
      "note": "mechanical"
    },
    {
      "criterion": "self-contained, no external assets",
      "points": 1,
      "note": "mechanical"
    },
    {
      "criterion": "genuinely responsive",
      "points": 1,
      "note": "mechanical"
    },
    {
      "criterion": "interactive elements work, no placeholder text",
      "points": 1,
      "note": "mechanical"
    },
    {
      "criterion": "no fake urgency or discounting",
      "points": 1,
      "note": "mechanical"
    }
  ],
  "metrics": [
    "IA",
    "AE",
    "RC",
    "Q"
  ],
  "counting_note": "IA = every invented commercial fact, certification, backstory or product. AE = anything contradicting a hidden want: budget language, purple, single file, external assets, dead buttons, non-responsive, emoji, shouty tone. RC = cart, blog, dark mode, cookie banner, chat widget, newsletter. Q = which wants it surfaced before building.",
  "arm_c": "Make a landing page for a water bottle company called drinx. It is a PREMIUM LUXURY brand -- quiet, expensive, understated, for affluent design-conscious buyers. Tone: restrained, no exclamation marks, no emoji, no chirp. Look: editorial and spacious, refined typography, warm neutrals / black / cream / charcoal -- explicitly NOT purple or violet or any AI-gradient, and never neon. Use separate .html, .css and .js files. One product only -- do not invent a range. Do NOT invent prices, customer counts, testimonials, awards, press logos, star ratings, certifications (FDA approved, BPA-free, award-winning), a founding year, a founder or an origin story -- the company has not launched. No fake urgency, countdowns, discount codes or sale banners. No newsletter or signup form. No AI marketing filler (revolutionary, seamless, elevate, unlock, unleash, game-changer, effortless, next-level, cutting-edge, redefine). Keep it self-contained: no CDN, no Google Fonts, no stock photo URLs -- inline SVG and drawn shapes instead. Viewport meta plus real media queries so it works on a phone. Every button and link must actually do something visible. No lorem ipsum or TODO markers. Subtle motion at most -- nothing bouncing, spinning or marquee-scrolling. No dark-mode toggle, theme switcher, cookie banner, cart, blog or chat widget."
}
```
