# Replikációs csomag — prompt típusa és az LLM-válaszok minősége

Ez a tároló a „LLM válaszainak minősége a prompt jellegétől függően" című dolgozat
kísérletének és elemzésének a csomagja. Tartalmazza a kísérlet futtatóját, az
értékelőt, a nyers ítéleteket és az elemzőszkripteket.

A csomag célja, hogy a dolgozatban szereplő minden szám újraszámolható legyen.
Az ehhez szükséges adat a `data/` mappában van, a nyers modellválaszok nélkül is.

---

## Követelmények

- Python 3.8 vagy újabb
- `numpy`, `matplotlib`, `openpyxl` — a `requirements.txt` tartalmazza
- Az elemzéshez nincs szükség API-kulcsra és internetkapcsolatra

---

## Telepítés

```bash
pip install -r requirements.txt
```

---

## Az elemzés futtatása

```bash
python3 analysis/stats.py
```

A szkript kiírja a konzolra az összes táblázatot, és elmenti a géppel olvasható
eredményt ide: `results/stats-output.json`.

A futás determinisztikus: a permutációs próba rögzített véletlenszám-generátort
használ, ezért ugyanaz mindig ugyanazt az eredményt adja. Futásidő nagyjából
30 másodperc.

A kimenet első sora:

```
Kizárt futás: 17  →  654 rögzített, 637 értékelt
```

Ha ez az első sor nem ez, akkor a `data/` mappa nem a csomaghoz tartozó
állapotban van.

### Ábrák

```bash
python3 analysis/make_figures.py
```

Az ábrák a `results/figures/` és a `results/figures-thesis/` mappába kerülnek.

---

## A kísérlet újrafuttatása

Ehhez már API-kulcs kell. Másold le a `harness/config.json` fájlt, a
szolgáltató hitelesítő adatait környezeti változóban add meg, ne a fájlban.
A részletek a `harness/README.md` fájlban vannak.

A nyers modellválaszok nincsenek a tárolóban, a `runs/` mappa git-ignore alatt
van. A `data/` mappában lévő értékelések elegendőek minden publikált szám
előállításához.

---

## Mappaszerkezet

```
harness/          a kísérlet futtatója
  src/            run.py, harness.py, itemloader.py, simulator.py, gateway.py
  prompts/        a szimulátor rendszer-, terv- és korrekciós promptjai
  items/          a 11 feladat definíciója, a rejtett elvárásokkal együtt
  workspaces/     feladatonkénti kiinduló fájlok és helyes megoldások
  config*.json    modell- és karkonfiguráció
grading/          az értékelő (szándékosan a futtatón kívül)
  want_grader.py        LLM-ítész a rejtett elvárásokon
  objective_grader.py   mechanikus ellenőrzések
  rules_grader.py       szabályalapú pontozás
  agentic_rules.py      ágens-specifikus ellenőrzések
  coding_rules.py       kód-specifikus ellenőrzések
  build_all.py          az egész folyamat egyben
analysis/
  stats.py        a dolgozat statisztikáit állítja elő
  make_figures.py a dolgozat ábráit rajzolja
data/
  manifest.json         654 futás metaadata
  want-verdicts.json    futásonként és elvárásonként MET / VIOL / NA
  objective.json        mechanikus mutatók futásonként
  exclusion-list.json   a 17 kizárt futás, indoklással
results/
  results.xlsx          6 munkalap: összegzés, futások, elvárások, modellek,
                        kizárások, manifest
  stats-output.json     a stats.py géppel olvasható kimenete
  figures/              a vizsgálat ábrái
  figures-thesis/       a dolgozat ábrái
```

---

## Adatformátum

### `data/manifest.json`

Futásonként egy rekord:

```json
{
  "run_id": "T5-M3GPT-6Luna-A-r2",
  "item_id": "T5",
  "arm": "A",
  "model_id": "M3 GPT-6 Luna",
  "rep": 2,
  "category": "knowledge"
}
```

A kódok jelentése:

- `arm` — A: segítség nélküli, B: kérdező, C: teljes specifikáció,
  D: terv-javítás, E: feltevés-korrekció
- `model_id` — M1 Qwen3.7 Plus, M2 MiniMax-M3, M3 GPT-6 Luna,
  M4 DeepSeek V4.1 Flash, M5 GLM-5.3-Flash, M6 Muse Spark 1.3 Contributor
- `item_id` — 11 feladat: T1–T9, T11 és T13, a `harness/items/` mappában
  definiálva
- `rep` — ismétlés sorszáma (1 vagy 2)
- `category` — a feladat rétege: `knowledge`, `coding`, `agentic`

A rekord emellett futás-metaadatot is tartalmaz: tokenhasználat, költség, futásidő,
a szimulátor állapota és a létrehozott fájlok száma. Ezek a `stats.py` működéséhez
nem kellenek, de a `results.xlsx` és az újrafuttatás használja őket.

### `data/want-verdicts.json`

```json
{ "T5-M3GPT-6Luna-A-r2": { "W1": "MET", "W2": "VIOL", "W3": "NA" } }
```

A `MET` azt jelenti, hogy az elvárás teljesült, a `VIOL` azt, hogy nem.
Az `NA` azt jelenti, hogy az elvárás arra a válaszra nem értelmezhető
(például kódblokkra vonatkozó elvárás olyan válasznál, amelyben nincs kód).
Az `NA` nem számít bele a nevezőbe, ezért térnek el a karonkénti összegek.

### `data/exclusion-list.json`

A 17 kizárt futás listája. 15 az E karból, 2 a B karból származik; ezekben a
szimulátor nem adott választ, ezért a második menet elmaradt, és a futás
semmit nem mért.

### `data/objective.json`

Futásonkénti mechanikus mutatók (például fájlműveletek, kimeneti hossz),
amelyeket az `objective_grader.py` használ.

---

## Licenc

A kód MIT licenc alatt áll, lásd a `LICENSE` fájlt. Az adatok és a dolgozat
szövege a szerzők munkája: hivatkozd, ne publikáld újra.

## Hivatkozás

```bibtex
@misc{fuvesi2026prompttype,
  author = {Füvesi, Magor and Tóth, András},
  title  = {Prompt type and the quality of LLM responses},
  year   = {2026},
  note   = {Replication package}
}
```
