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
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "ricettario_comune.json"
OUT = HERE.parent / "recipes_comune.js"
BANDS = ["ponte", "infanzia", "primaria_1_2", "primaria_3_5", "secondaria"]


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
    recipes, names = [], set()
    for code, group, kind in plan:
        r = data["ricette"][code]
        ing = [[n, {b: g[b] for b in BANDS if g.get(b) is not None}] for n, g in clean_ingredients(r["ingredienti"])]
        names.update(n for n, _ in ing)
        title = r["nome"].replace("’", "'").replace("–", "-")
        x = {"id": "comune-" + code, "code": code, "page": r["pagina"], "group": group, "kind": kind,
             "title": title, "main": main_food(group, ing), "ing": ing, "steps": steps(r["procedimento"])}
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
    print(len(recipes), "ricette ->", OUT.name)


if __name__ == "__main__":
    main()
