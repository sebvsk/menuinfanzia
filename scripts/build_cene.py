"""Build recipes_comune.js: dinners taken from Roma Capitale's official school recipe book.

Reads scripts/ricettario_comune.json (extracted from Allegato C, contract 2021-2026) and writes
recipes_comune.js next to index.html. Nothing is invented here: names, grams per age band and method
come from the recipe book. The editorial choices are ours and are marked as a draft in the app:
which recipes suit a home dinner, their food group, which side dishes are raw, which first courses
are "in brodo". Rules: 03 Regole/Regole della cena.md (R1-R5).

Usage: python scripts/build_cene.py [--names]     (--names lists every ingredient name, to spot dirty ones)
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "ricettario_comune.json"
OUT = HERE.parent / "recipes_comune.js"
BANDS = ["ponte", "infanzia", "primaria_1_2", "primaria_3_5", "secondaria"]
# Nido (13-36 months): grams from the nido tables of the same contract (Allegato 02, pp. 74-104), only where the
# nido has a recipe with the same name. Extracted into scripts/ricettario_nido.json.
NIDO_SRC = HERE / "ricettario_nido.json"
NIDO_BANDS = ["nido_13_18", "nido_19_24", "nido_25_36"]
# Same dish, different title in the two recipe books (checked on the ingredients).
NIDO_ALIAS = {"231": "N225", "319": "N312", "311": "N309", "328": "N319"}


def codes(*parts):
    out = []
    for p in parts:
        if isinstance(p, tuple):
            out += [str(n) for n in range(p[0], p[1] + 1)]
        else:
            out.append(str(p))
    return out


# Second courses, by food group. Every variant is kept (same preparation, different food): rule R3.
SECONDI = {
    "pesce": codes(209, 212, "212bis", 213, (226, 230), 241, 245, 246, 248),
    "carne": codes((201, 208), 210, 211, 224, 225, (232, 237), 239, 240, (242, 244)),
    "uova": codes((220, 223), 250),
    "formaggi": codes((214, 219), 231, 238),
    "legumi": codes(247),
}
# First courses that are a full legume dish (at least 3/4 of a portion in the recipe book).
PRIMI_LEGUMI = codes(102, 103, "103bis", (104, 107), 109, 141)
# Vegetable soups with pasta, for "dry at lunch, in broth at dinner" (rule G4).
PRIMI_BRODO = codes(110, 111)
# Side dishes: vegetables only (potatoes and peas do not count as vegetables in the app).
CONTORNI = [c for c in codes((301, 334)) if c not in codes((320, 323), 325)]
CRUDI = codes(305, (315, 319))
# Main vegetables when the title does not say them.
VEG = {"109": ["zucchine", "bieta"], "110": ["zucchine", "carote"], "111": ["carote", "bieta"]}
SEASON = {"110": "estate", "111": "inverno", "317": "estate", "318": "inverno"}

# Names broken by the PDF extraction (a word pushed onto the next row, cut names).
STRAY = ("surg.", "UHT", "secchi", "secche")
FIX = {
    "borlotti/cannellini Carote": "Carote",
    "cannellini Carote": "Carote",
    "Fagioli secchi": "Fagioli secchi borlotti/cannellini",
    "Fagioli secchi borlotti/": "Fagioli secchi borlotti/cannellini",
    "Fagioli secchi borlotti/cannelli": "Fagioli secchi borlotti/cannellini",
    "di bufala o Mozzarella fiordi Latte": "Mozzarella di bufala o fiordilatte vaccina",
    "Fiori di zucca pastellati surgelato (1, 3,": "Fiori di zucca pastellati surgelati",
    "extravergine": "Olio extravergine",
    "Arista/ lombata maiale": "Arista/lombata maiale",
    "Sovra coscio pollo (fuso e (peso lordo (peso lordo (peso lordo": "Sovracoscio di pollo (fuso e coscio), peso lordo",
    "coscio) Rosmarino": "Rosmarino",
    "G Petto di pollo": "Petto di pollo",
    "G Petto pollo": "Petto di pollo",
    "G Spalla bovino": "Spalla bovino",
    "G g Spalla bovino": "Spalla bovino",
    "lombata noce/ Scamone di bovino": "Lombata/noce/scamone di bovino",
    "Lombata/ noce/ Scamone di": "Lombata/noce/scamone di bovino",
    "bovino Farina": "Farina",
}
# Two ingredients merged on one row: the grams belong to the one marked True, the other is "q.b.".
SPLIT = {
    "Finocchi Brodo": [("Finocchi", True), ("Brodo vegetale", False)],
    "Aglio Olio extravergine": [("Aglio", False), ("Olio extravergine", True)],
}


def clean_ingredients(rows):
    out = []
    for name, grams in rows:
        name = name.strip()
        for w in STRAY:
            if name.startswith(w + " ") and out:
                out[-1][0] += " " + w
                name = name[len(w):].strip()
        out.append([name, grams])
    final = []
    for name, grams in out:
        n = name.replace("surg.", "surgelato").replace("extrav.", "extravergine").replace("’", "'")
        n = re.sub(r"\s+", " ", n).strip()
        if n in SPLIT:
            final += [[part, grams if keep else {}] for part, keep in SPLIT[n]]
        else:
            final.append([FIX.get(n, n), grams])
    return final


def steps(text):
    parts = re.split(r"(?<=[.!])\s+(?=[A-ZÈ])", (text or "").strip())
    return [p if p.endswith(".") else p + "." for p in (x.strip() for x in parts) if p]


def norm(text):
    t = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    t = re.sub(r"\(.*?\)", "", t)
    return " ".join(re.sub(r"[^a-z ]", " ", t).split())


NOISE = {"di", "surg", "surgelato", "surgelati", "extrav", "extravergine", "per", "secchi", "secche", "freschi",
         "intero", "uht", "filetto", "filetti", "succo", "acqua", "impanatura", "panatura", "parboiled"}


def tokens(name):
    # crude singular/plural folding: carota = carote, cavolfiore = cavolfiori
    return {re.sub(r"[aeio]$", "", w) if len(w) > 4 else w for w in norm(name).split() if w not in NOISE}


def add_nido(code, title, ing, nido, report):
    """Add the nido grams to the ingredients of a school recipe that the nido cooks too."""
    key = lambda t: norm(re.sub("[()'’]", " ", t))      # keep "(estate)" / "(inverno)" in the title
    by_name = {key(v["nome"]): k for k, v in nido.items()}
    ncode = NIDO_ALIAS.get(code) or by_name.get(key(title))
    if not ncode:
        return None
    rows = [(tokens(n), g) for n, g in nido[ncode]["ingredienti"]]
    used, matched_main = set(), False
    for pos, (name, grams) in enumerate(ing):
        want = tokens(name)
        best = None
        for j, (have, g) in enumerate(rows):
            if j in used or not want or not have or not (want <= have or have <= want):
                continue
            if best is None or len(want & have) > len(want & rows[best][0]):
                best = j
        if best is None and pos == 0 and 0 not in used and want & rows[0][0]:
            best = 0                 # same dish, another cut of the same meat (fesa / noce di bovino)
        if best is None:
            if grams:
                report.append(f"{code} {title}: «{name}» non c'è nella ricetta del nido {ncode}")
            continue
        used.add(best)
        grams.update(rows[best][1])
        matched_main = matched_main or pos == 0
    left = [nido[ncode]["ingredienti"][j][0] for j in range(len(rows)) if j not in used and rows[j][1]]
    if left:
        report.append(f"{code} {title}: nel nido ({ncode}) ci sono anche {left}, non contati")
    if not matched_main:          # the main food does not match: not the same dish, drop the nido grams
        for _, grams in ing:
            for b in NIDO_BANDS:
                grams.pop(b, None)
        report.append(f"{code} {title}: ingrediente principale diverso da {ncode}, dosi del nido scartate")
        return None
    return {"code": ncode, "page": nido[ncode]["pagina"]}


def main_food(group, ing):
    """The food that changes between two variants of the same preparation (merluzzo / nasello)."""
    if group == "legumi":
        for name, _ in ing:
            if re.search(r"ceci|fagioli|lenticchie|cannellini", name, re.I):
                return name
    return ing[0][0] if ing else ""


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    plan = [(c, g, "secondo") for g, cs in SECONDI.items() for c in cs]
    plan += [(c, "legumi", "primo") for c in PRIMI_LEGUMI]
    plan += [(c, "verdura", "brodo") for c in PRIMI_BRODO]
    plan += [(c, "verdura", "contorno") for c in CONTORNI]
    nido = json.loads(NIDO_SRC.read_text(encoding="utf-8"))["ricette"] if NIDO_SRC.exists() else {}
    recipes, names, report = [], set(), []
    for code, group, kind in plan:
        r = data["ricette"][code]
        ing = [[n, {b: g[b] for b in BANDS if g.get(b) is not None}] for n, g in clean_ingredients(r["ingredienti"])]
        names.update(n for n, _ in ing)
        title = r["nome"].replace("’", "'").replace("–", "-")
        x = {"id": "comune-" + code, "code": code, "page": r["pagina"], "group": group, "kind": kind,
             "title": title, "main": main_food(group, ing), "ing": ing, "steps": steps(r["procedimento"])}
        twin = add_nido(code, title, ing, nido, report)
        if twin:
            x["nido"] = twin
        if code in VEG:
            x["veg"] = VEG[code]
        if code in SEASON:
            x["season"] = SEASON[code]
        if kind == "contorno":
            x["raw"] = code in CRUDI
        if kind == "brodo" or (kind == "primo" and title.startswith("Crema")):
            x["broth"] = True
        recipes.append(x)
    head = ("// GENERATED by scripts/build_cene.py from scripts/ricettario_comune.json: do not edit by hand.\n"
            "// Official recipes of Roma Capitale (Allegato C, contract 2021-2026). ing = [name, grams per age band];\n"
            "// no grams = \"q.b.\" in the recipe book. The band \"secondaria\" is also the adults' portion.\n"
            "// nido_* bands: grams from the nido tables (Allegato 02, pp. 74-104) where the nido has the same recipe; nido = its code and page.\n"
            "// kind: secondo | primo (legume dish) | brodo (vegetable soup) | contorno. raw/broth/season: our classification.\n")
    body = ",\n".join("  " + json.dumps(x, ensure_ascii=False) for x in recipes)
    OUT.write_text(head + "const RECIPES_COMUNE = [\n" + body + "\n];\n", encoding="utf-8", newline="\n")
    if "--names" in sys.argv:
        print("\n".join(sorted(names)))
    count = {}
    for x in recipes:
        key = x["group"] + "/" + x["kind"]
        count[key] = count.get(key, 0) + 1
        missing = [b for b in BANDS if not any(b in g for _, g in x["ing"])]
        if missing or not x["steps"]:
            print(x["code"], x["title"], "| fasce mancanti:", missing or "nessuna", "| senza procedimento" if not x["steps"] else "")
    print(count)
    print("con dosi del nido:", sum(1 for x in recipes if "nido" in x), "su", len(recipes))
    print("\n".join(report))
    print(len(recipes), "ricette ->", OUT.name)


if __name__ == "__main__":
    main()
