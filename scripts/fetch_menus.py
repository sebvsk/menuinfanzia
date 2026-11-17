"""Download the monthly school menus from MESIS (Roma Capitale) and write them as JSON for the app.

Usage:
  python scripts/fetch_menus.py                  # current month and next month, all Municipi and cycles
  python scripts/fetch_menus.py 2026-11          # one month
  python scripts/fetch_menus.py 2026-11 --only 6:4   # one Municipio:cycle (6 = Municipio V, 4 = infanzia)
  python scripts/fetch_menus.py 2026-10 --from-html page.html --only 6:4   # parse a saved page (test)
  python scripts/fetch_menus.py 2026-10 --from-csv "02 Menu/2026-10"       # import the old CSV files

One request per menu (page "Menu del mese"); the site needs the session cookie from the form page.
Output: data/AAAA-MM/m<mun>-c<cycle>.json, data/index.json, data/da_controllare.md (dishes classified by guess).
Only the standard library is used, so it runs on GitHub Actions and on Windows without installing anything.
"""
import csv
import datetime as dt
import html
import http.cookiejar
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FETCHED = dt.date.today().isoformat()
BASE = "https://www.comune.roma.it/servizi/mesis-portal-reports-war"
WEEKDAYS = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
MUNICIPI = {1: "I", 2: "II", 4: "III", 5: "IV", 6: "V", 8: "VI", 9: "VII", 11: "VIII", 12: "IX",
            13: "X", 15: "XI", 16: "XII", 18: "XIII", 19: "XIV", 20: "XV"}
CICLI = {1: "Nido medi", 2: "Nido grandi", 3: "Ponte", 4: "Infanzia", 5: "Primaria", 6: "Secondaria I grado"}
SLOTS = ["spuntino", "primo", "secondo", "contorno", "pane", "frutta_dolce", "merenda"]

# ---------------------------------------------------------------- classification
# The CREA table for children does not split white and red meat (Tab. 9.2).
ALIAS = {"carne_bianca": "carne", "carne_rossa": "carne", "cereali_integrali": "cereali"}

# Keyword fallback for dishes not in piatti_gruppi.csv (draft, to be checked by a dietitian).
KW = {
    "pesce": ["merluzzo", "nasello", "platessa", "limanda", "salmone", "tonno", "orata", "spigola", "branzino",
              "pesce", "sogliola", "palombo", "trota", "alici", "halibut", "cernia", "persico", "totano", "seppi"],
    "uova": ["uova", "uovo", "frittata", "omelette"],
    "legumi": ["lenticch", "ceci", "fagioli", "piselli", "legumi", "cannellini", "borlotti", "fave", "hummus",
               "cicerchie"],
    "carne": ["pollo", "tacchino", "bovino", "manzo", "vitello", "vitellone", "maiale", "suino", "lonza",
              "prosciutto", "hamburger", "coniglio", "carne", "petto", "cosce", "fuso", "ragù", "ragu'", "agnello",
              "lasagn", "bologn"],
    "formaggi": ["mozzarella", "crescenza", "robiola", "asiago", "stracchino", "ricotta", "parmigiano", "caciotta",
                 "emmental", "fontina", "provol", "formaggio", "grana", "primo sale", "scamorza", "montasio",
                 "caprino", "fiocchi di latte", "bocconcini di latte", "quartirolo", "pecorino"],
    "patate": ["patate", "purè", "pure'", "purea di patate"],
    "verdura": ["carot", "zucchin", "fagiolini", "bieta", "biete", "spinaci", "insalata", "pomodor", "finocch",
                "cavolfior", "broccol", "cavolo", "verza", "zucca", "verdur", "ortagg", "minestrone", "cicoria",
                "carciof", "melanzan", "peperon", "cappuccio", "lattuga", "radicchio", "erbette", "porri",
                "sedano", "cetriol", "ortolana", "piselli e carote"],
    "frutta": ["frutta", "banana", "mela", "mele", "pera", "pere", "arancia", "arance", "mandarin", "clementin",
               "kiwi", "uva", "cachi", "ananas", "pesca", "pesche", "albicocc", "fragol", "macedonia"],
    "dolci": ["gelato", "crostat", "ciambell", "biscott", "plumcake", "plum cake", "torta", "budino", "dolce", "cioccolat",
              "merendina", "muffin", "marmellata", "crema spalmabile", "pan di spagna", "strudel", "cornetto"],
    "latte": ["yogurt", "latte"],
    "cereali": ["pasta", "riso", "risotto", "farro", "orzo", "gnocch", "pane", "pizza", "focaccia", "cracker",
                "schiacciatin", "fette biscottate", "grissini", "tortellin", "ravioli", "lasagn", "polenta",
                "cous cous", "couscous", "crostini", "pancarr", "gallett", "cereali", "fusilli", "penne",
                "spaghetti", "maccheroni", "tagliatelle", "ditalini", "pastina", "cannelloni", "crespelle",
                "piadina", "tramezzino", "panino", "bruschett", "agnolott", "tortellon", "cappellett",
                "timballo", "maccheroncin", "conchigli", "farfalle", "rigatoni", "sedanini", "mezze maniche"],
}
# Order of checks for each slot: the first group whose keyword appears wins.
ORDER = {
    "primo": ["legumi", "cereali", "verdura"],
    "secondo": ["pesce", "uova", "legumi", "carne", "formaggi", "verdura", "patate", "cereali"],
    "contorno": ["patate", "legumi", "verdura"],
    "frutta_dolce": ["dolci", "frutta"],
    "spuntino": ["dolci", "latte", "frutta", "cereali"],
    "merenda": ["dolci", "latte", "frutta", "cereali"],
    "pane": ["cereali"],
}
SECONDARY = ["legumi", "carne", "pesce", "uova", "formaggi", "verdura", "cereali", "latte"]


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def load_dictionary():
    out = {}
    with open(Path(__file__).with_name("piatti_gruppi.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            main = ALIAS.get(row["gruppo_principale"], row["gruppo_principale"])
            sec = [ALIAS.get(g, g) for g in row["gruppi_secondari"].split(";") if g]
            out[norm(row["piatto"])] = (main, [g for g in sec if g != main])
    return out


DICT = load_dictionary()


def has(name, group):
    if group == "legumi":
        name = name.replace("fagiolini", "")  # green beans are vegetables, not legumes
    return any(k in name for k in KW[group])


def classify(name, slot):
    """Return (main group, secondary groups, guessed?)."""
    n = norm(name)
    if n in DICT:
        main, sec = DICT[n]
        return main, sec, False
    for alt in n.split("/"):  # "X/Y" alternatives: use the first one known
        if alt.strip() in DICT:
            main, sec = DICT[alt.strip()]
            return main, sec, False
    main = next((g for g in ORDER.get(slot, ORDER["secondo"]) if has(n, g)), None)
    sec = [g for g in SECONDARY if g != main and has(n, g)]
    return main, sec, True


# ---------------------------------------------------------------- download
def opener():
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [("User-Agent", "Mozilla/5.0 (menuinfanzia; menu scolastico per genitori)")]
    return op


def get(op, url, post=False, tries=5):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, data=b"" if post else None, method="POST" if post else "GET")
            with op.open(req, timeout=60) as r:
                return r.read().decode("latin-1")
        except Exception as e:  # the city network sometimes drops connections
            if n == tries - 1:
                raise
            print(f"  rete: {e}; riprovo fra 10 s", file=sys.stderr)
            time.sleep(10)


def fetch_page(op, mun, ciclo, year, month):
    get(op, f"{BASE}/loadMenuRistorazione.do")  # opens the session
    return get(op, f"{BASE}/loadMenuMese.do?municipio={mun}&cicloScolastico={ciclo}"
                   f"&dataSelezionata=01/{month:02d}/{year}", post=True)


# ---------------------------------------------------------------- parsing
DESSERT = ["frutta", "spremuta", "succo", "gelato", "budino", "macedonia", "dolce", "torta", "crostata", "yogurt",
           "mela", "banana", "arancia", "mandarin", "clementin", "pera", "kiwi", "uva", "cachi"]


def lunch_slots(items):
    """MESIS order: primo, secondo, contorno, [pane], frutta/gelato.
    Pizza days have no bread; piatto unico days (lasagna, pasta al ragù) have no secondo."""
    r, rest = {}, []
    for v in items:
        (r.__setitem__("pane", v) if v.lower().startswith("pane") else rest.append(v))
    if len(rest) >= 2 and any(w in rest[-1].lower() for w in DESSERT):
        r["frutta_dolce"] = rest.pop()
    if len(rest) == 2:                       # piatto unico + contorno
        r["primo"], r["contorno"], r["unico"] = rest[0], rest[1], True
        return r
    for key, v in zip(["primo", "secondo", "contorno"], rest):
        r[key] = v
    if rest[3:]:
        r["contorno"] = " + ".join([r.get("contorno", "")] + rest[3:])
    return r


def parse_page(page, year, month):
    cells = [re.sub(r"\s+", " ", html.unescape(x)).strip() for x in re.sub(r"<[^>]+>", "\n", page).split("\n")]
    cells = [c for c in cells if c and c != "Menu mensile"]
    days, d, kind = {}, None, None
    for c in cells:
        m = re.search(r"(\d\d)/(\d\d)/(\d{4})$", c)
        if m and c.split()[0] in WEEKDAYS:
            d = dt.date(int(m[3]), int(m[2]), int(m[1]))
            days.setdefault(d, {})
            kind = None
        elif c.startswith("In caso di chiusura") or c == "INDIETRO":
            if d:
                break
        elif d and c in ("Spuntino", "Pranzo", "Merenda", "Note"):
            kind = c
        elif d and kind:
            lst = days[d].setdefault(kind, [])
            if not lst or lst[-1] != c or kind != "Pranzo":  # page breaks repeat some lines
                lst.append(c)
    rows = []
    for d in sorted(days):
        if (d.year, d.month) != (year, month):
            continue
        k = days[d]
        row = {"spuntino": " · ".join(k.get("Spuntino", [])), "merenda": " · ".join(k.get("Merenda", [])),
               "note": " · ".join(k.get("Note", []))}
        row.update(lunch_slots(k.get("Pranzo", [])))
        rows.append((d, row))
    return rows


def to_json(rows, mun, ciclo, year, month, guessed):
    days = []
    for d, row in rows:
        items = []
        for slot in SLOTS:
            name = re.sub(r"\s+", " ", row.get(slot) or "").strip()
            if not name:
                continue
            g, sec, guess = classify(name, slot)
            if slot == "primo" and row.get("unico"):      # piatto unico: it is also the secondo
                g2, sec2, _ = classify(name, "secondo")
                if g2 and g2 not in ("cereali", "verdura", "patate"):
                    g, sec, guess = g2, [x for x in dict.fromkeys(sec2 + ["cereali"]) if x != g2], True
            it = {"slot": slot, "name": name[0].upper() + name[1:], "group": g}
            if sec:
                it["also"] = sec
            if slot == "primo" and row.get("unico"):
                it["unico"] = True
            if guess:
                it["guess"] = True
                guessed.setdefault(name, (slot, g, sec))
            items.append(it)
        day = {"date": d.isoformat(), "weekday": WEEKDAYS[d.weekday()], "items": items}
        if row.get("note"):
            day["note"] = row["note"]
        days.append(day)
    return {"source": f"MESIS Roma Capitale · Municipio {MUNICIPI[mun]} · {CICLI[ciclo]}",
            "municipio": mun, "ciclo": ciclo, "month": f"{year}-{month:02d}",
            "fetched": FETCHED, "days": days}


def write_menu(obj):
    folder = DATA / obj["month"]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"m{obj['municipio']}-c{obj['ciclo']}.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if old and old["days"] == obj["days"] and old.get("fetched") <= obj["fetched"]:
        return False  # unchanged: keep the old "fetched" date, so git sees no change
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return True


def write_index():
    months = sorted(p.name for p in DATA.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d\d", p.name))
    idx = {"municipi": {str(k): v for k, v in MUNICIPI.items()}, "cicli": {str(k): v for k, v in CICLI.items()},
           "months": {m: sorted(p.stem for p in (DATA / m).glob("m*-c*.json")) for m in months}}
    (DATA / "index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")


def write_guessed(guessed):
    path = DATA / "da_controllare.md"
    old = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines()[4:]:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) == 4:
                old[parts[0]] = line
    for name, (slot, g, sec) in guessed.items():
        old[name] = f"| {name} | {slot} | {g or '**?**'} | {', '.join(sec)} |"
    lines = ["# Piatti classificati in automatico (da controllare)", "",
             "| Piatto | Portata | Gruppo stimato | Anche |", "|---|---|---|---|"] + sorted(old.values())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def from_csv(folder, year, month):
    names = {v: k for k, v in MUNICIPI.items()}
    cycles = {v: k for k, v in CICLI.items()}
    out = []
    for p in sorted(Path(folder).glob("*.csv")):
        m = re.match(r"\d{4}-\d\d Municipio (\w+) (.+)\.csv$", p.name)
        if not m:
            continue
        with open(p, encoding="utf-8-sig", newline="") as f:
            rows = [(dt.date.fromisoformat(r["data"]), r) for r in csv.DictReader(f)]
        out.append((names[m[1]], cycles[m[2]], rows))
    return out


def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("month", nargs="?")
    ap.add_argument("--only")
    ap.add_argument("--from-html")
    ap.add_argument("--from-csv")
    ap.add_argument("--fetched", help="date to record as download date (for imported files)")
    a = ap.parse_args(argv)
    opt = {f"--{k.replace('_', '-')}": v for k, v in vars(a).items() if v and k != "month"}
    global FETCHED
    FETCHED = a.fetched or dt.date.today().isoformat()
    today = dt.date.today()
    if a.month:
        months = [tuple(map(int, a.month.split("-")))]
    else:
        nxt = (today.replace(day=1) + dt.timedelta(days=32))
        months = [(today.year, today.month), (nxt.year, nxt.month)]
    pairs = [(m, c) for m in MUNICIPI for c in CICLI]
    if "--only" in opt:
        pairs = [tuple(map(int, p.split(":"))) for p in opt["--only"].split(",")]

    guessed, written, found, failed = {}, 0, 0, []
    for year, month in months:
        if "--from-csv" in opt:
            batches = from_csv(opt["--from-csv"], year, month)
        else:
            batches = []
            op = opener()
            for mun, ciclo in pairs:
                label = f"{year}-{month:02d} Municipio {MUNICIPI[mun]} {CICLI[ciclo]}"
                try:
                    page = (Path(opt["--from-html"]).read_text(encoding="utf-8") if "--from-html" in opt
                            else fetch_page(op, mun, ciclo, year, month))
                except Exception as e:
                    failed.append(f"{label}: {e}")
                    continue
                rows = parse_page(page, year, month)
                print(f"{label}: {len(rows)} giorni")
                if rows:
                    batches.append((mun, ciclo, rows))
                if "--from-html" not in opt:
                    time.sleep(1)  # be gentle with the city server
        for mun, ciclo, rows in batches:
            found += 1
            written += write_menu(to_json(rows, mun, ciclo, year, month, guessed))
    write_index()
    write_guessed(guessed)
    print(f"menù trovati: {found}, cambiati: {written}, piatti stimati: {len(guessed)}, errori: {len(failed)}")
    for f in failed[:10]:
        print("  errore:", f, file=sys.stderr)
    if not found and failed:
        sys.exit("nessun menù scaricato: il sito del Comune non risponde o ha cambiato pagina")


if __name__ == "__main__":
    main(sys.argv[1:])
