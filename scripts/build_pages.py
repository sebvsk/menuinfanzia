"""Build the public pages that search engines and AI assistants can read.

The app (index.html) loads the menus with JavaScript, so search engines see almost nothing of it.
This script writes plain HTML pages from data/:
  menu/index.html                          all Municipi and school types
  menu/<municipio>/<ciclo>/index.html      the menu of the current and next month, day by day
  come-funziona/index.html                 what the site is, privacy, sources, FAQ
  sitemap.xml, robots.txt, llms.txt, og.png (link preview image)

It runs on GitHub Actions before every publication. Only the standard library is used
(Pillow is optional, for og.png).

Usage: python scripts/build_pages.py [--oggi 2026-11-17]
"""
import argparse
import datetime as dt
import html
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = "https://menuscuolaroma.it"          # the site's own domain, used in canonical links and the sitemap
NAME = "Compagni di Merende"
OWNER = "menuscuolaroma.it"   # shown in the footer; the author is named in LICENSE
CONTACT = (os.environ.get("CONTATTO") or "info@menuscuolaroma.it").strip()   # GitHub variable CONTATTO can override it
YEAR = "2026"
CICLO_SLUG = {1: "nido-medi", 2: "nido-grandi", 3: "sezione-ponte", 4: "infanzia", 5: "primaria", 6: "secondaria-primo-grado"}
CICLO_TEXT = {1: "asilo nido (medi)", 2: "asilo nido (grandi)", 3: "sezione ponte", 4: "scuola dell'infanzia",
              5: "scuola primaria", 6: "scuola secondaria di primo grado"}
QUARTIERI = {  # main neighbourhoods, to help people who search by area
    "I": "Centro Storico, Prati, Trastevere, Esquilino", "II": "Parioli, Flaminio, Nomentano, Salario, San Lorenzo",
    "III": "Montesacro, Talenti, Val Melaina, Fidene, Bufalotta", "IV": "Tiburtino, Pietralata, Casal Bertone, San Basilio",
    "V": "Prenestino, Centocelle, Pigneto, Torpignattara, Quarticciolo", "VI": "Torre Angela, Tor Bella Monaca, Lunghezza, Ponte di Nona",
    "VII": "Appio Latino, Tuscolano, Cinecittà, Don Bosco", "VIII": "Garbatella, Ostiense, San Paolo, Montagnola",
    "IX": "EUR, Torrino, Laurentino, Spinaceto, Cecchignola", "X": "Ostia, Acilia, Infernetto, Casal Palocco",
    "XI": "Portuense, Magliana, Marconi, Corviale", "XII": "Monteverde, Gianicolense, Pisana",
    "XIII": "Aurelio, Boccea, Casalotti, Primavalle", "XIV": "Monte Mario, Balduina, Trionfale, Ottavia",
    "XV": "Cassia, Flaminia, Tor di Quinto, La Storta, Prima Porta"}
MESI = ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre",
        "novembre", "dicembre"]
SLOTS = [("spuntino", "Spuntino"), ("primo", "Primo"), ("secondo", "Secondo"), ("contorno", "Contorno"),
         ("pane", "Pane"), ("frutta_dolce", "Frutta o dolce"), ("merenda", "Merenda")]
DISCLAIMER = ("Sito indipendente, non affiliato a Roma Capitale. I menù sono ripresi dal portale pubblico MESIS "
              "del Comune di Roma e aggiornati in automatico il 1° e il 25 di ogni mese: in caso di dubbio vale "
              "il menù esposto a scuola.")

e = lambda s: html.escape(str(s), quote=True)


def mun_slug(roman):
    return "municipio-" + roman.lower()


def page(title, description, path, body, depth, extra_head=""):
    rel = "../" * depth or "./"
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{SITE}/{path}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{NAME}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{SITE}/{path}">
<meta property="og:image" content="{SITE}/og.png">
<meta property="og:locale" content="it_IT">
<meta name="theme-color" content="#e8833a">
<link rel="icon" href="{rel}icon-192.png">
{extra_head}
<style>
  body {{ margin: 0; background: #fffaf5; color: #2b2b2b; font: 16px/1.5 "Segoe UI", system-ui, -apple-system, Roboto, Arial, sans-serif; }}
  header {{ background: #e8833a; color: #fff; padding: 12px 16px; }}
  header a {{ color: #fff; text-decoration: none; font-weight: 600; font-size: 18px; }}
  main {{ max-width: 720px; margin: 0 auto; padding: 16px 16px 48px; }}
  h1 {{ font-size: 24px; line-height: 1.25; margin: 8px 0 12px; }}
  h2 {{ font-size: 20px; margin: 28px 0 8px; }}
  h3 {{ font-size: 16px; margin: 0 0 4px; }}
  a {{ color: #b8541a; }}
  .cta {{ display: block; background: #e8833a; color: #fff; text-align: center; padding: 13px; border-radius: 12px;
          font-weight: 600; text-decoration: none; margin: 16px 0; }}
  .day {{ background: #fff; border: 1px solid #f0e6dc; border-radius: 12px; padding: 10px 14px; margin: 8px 0; }}
  .day.oggi {{ border: 2px solid #e8833a; }}
  .day ul {{ margin: 4px 0 0; padding-left: 18px; }}
  .day li span {{ color: #6b625a; }}
  .note {{ font-size: 14px; color: #6b625a; }}
  .box {{ background: #fff3e6; border-radius: 12px; padding: 12px 14px; margin: 12px 0; }}
  .links {{ columns: 2; padding-left: 18px; }}
  footer {{ max-width: 720px; margin: 0 auto; padding: 0 16px 32px; font-size: 13px; color: #6b625a; }}
</style>
</head>
<body>
<header><a href="{rel}">{NAME}</a></header>
<main>
{body}
</main>
<footer>{e(DISCLAIMER)} · <a href="{rel}come-funziona/">Come funziona e privacy</a> · <a href="{rel}menu/">Tutti i menù</a><br>© {YEAR} {OWNER} · {NAME}{f' · <a href="mailto:{CONTACT}">Contatti</a>' if CONTACT else ""}</footer>
<script data-goatcounter="https://menuinfanzia.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
</body>
</html>
"""


def day_html(d):
    date = dt.date.fromisoformat(d["date"])
    items = {it["slot"]: it["name"] for it in d["items"]}
    rows = "".join(f"<li><span>{label}:</span> {e(items[slot])}</li>" for slot, label in SLOTS if items.get(slot))
    note = f'<p class="note">{e(d["note"])}</p>' if d.get("note") else ""
    return (f'<section class="day" id="d-{d["date"]}"><h3>{d["weekday"]} {date.day} {MESI[date.month]}</h3>'
            f"<ul>{rows}</ul>{note}</section>")


TODAY_JS = """<script>
(function () {
  var p = new Date(), t = p.getFullYear() + "-" + String(p.getMonth() + 1).padStart(2, "0") + "-" + String(p.getDate()).padStart(2, "0");
  var el = document.getElementById("d-" + t), box = document.getElementById("oggi");
  if (el && box) { el.classList.add("oggi"); box.innerHTML = "<h2>Oggi</h2>" + el.outerHTML; }
})();
</script>"""


def build(today):
    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
    municipi = {int(k): v for k, v in idx["municipi"].items()}
    cicli = {int(k): v for k, v in idx["cicli"].items()}
    cur = f"{today.year}-{today.month:02d}"
    months = [m for m in sorted(idx["months"]) if m >= cur] or sorted(idx["months"])[-1:]
    urls = ["", "menu/", "come-funziona/"]
    fetched = ""

    # one page per Municipio and school type
    for mun, roman in municipi.items():
        for ciclo, label in cicli.items():
            menus = []
            for m in months:
                f = DATA / m / f"m{mun}-c{ciclo}.json"
                if f.exists():
                    menus.append(json.loads(f.read_text(encoding="utf-8")))
            if not menus:
                continue
            fetched = max(fetched, *(x["fetched"] for x in menus))
            path = f"menu/{mun_slug(roman)}/{CICLO_SLUG[ciclo]}/"
            urls.append(path)
            mesi = " e ".join(f"{MESI[int(x['month'][5:])]} {x['month'][:4]}" for x in menus)
            title = f"Menù mensa {CICLO_TEXT[ciclo]} Municipio {roman} Roma – {mesi}"
            desc = (f"Il menù della mensa scolastica comunale ({CICLO_TEXT[ciclo]}) del Municipio {roman} di Roma "
                    f"({QUARTIERI[roman]}), giorno per giorno: spuntino, pranzo e merenda di {mesi}. "
                    f"E un'idea per la cena di casa che completa la settimana.")
            body = [f"<h1>Menù della mensa: {CICLO_TEXT[ciclo]}, Municipio {roman} di Roma</h1>",
                    f"<p>Il menù delle scuole comunali del <strong>Municipio {roman}</strong> ({e(QUARTIERI[roman])}) "
                    f"per la {e(CICLO_TEXT[ciclo])}: è lo stesso per tutte le scuole comunali del Municipio. "
                    f"Aggiornato il {dt.date.fromisoformat(max(x['fetched'] for x in menus)).strftime('%d/%m/%Y')}.</p>",
                    f'<a class="cta" href="../../../?mun={mun}&amp;ciclo={ciclo}">Cosa cucino stasera? Apri {NAME}</a>',
                    '<div id="oggi"></div>']
            for x in menus:
                body.append(f"<h2>{MESI[int(x['month'][5:])].capitalize()} {x['month'][:4]}</h2>")
                body += [day_html(d) for d in x["days"]]
            others = " · ".join(f'<a href="../{CICLO_SLUG[c]}/">{e(l)}</a>' for c, l in cicli.items() if c != ciclo)
            body.append(f'<div class="box"><b>Altri menù del Municipio {roman}:</b> {others}<br>'
                        f'<a href="../../">Menù degli altri Municipi</a></div>')
            body.append(f'<p class="note">Fonte: portale MESIS di Roma Capitale. {e(DISCLAIMER)}</p>')
            ld = {"@context": "https://schema.org", "@type": "WebPage", "name": title, "description": desc,
                  "inLanguage": "it", "dateModified": max(x["fetched"] for x in menus),
                  "about": {"@type": "Menu", "name": f"Menù mensa scolastica {label} Municipio {roman} Roma",
                            "inLanguage": "it"},
                  "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
                      {"@type": "ListItem", "position": 1, "name": "Menù", "item": f"{SITE}/menu/"},
                      {"@type": "ListItem", "position": 2, "name": f"Municipio {roman}", "item": f"{SITE}/{path}"}]}}
            head = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
            out = ROOT / path / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(page(title, desc, path, "\n".join(body) + TODAY_JS, 3, head), encoding="utf-8")

    # list of all menus
    items = []
    for mun, roman in municipi.items():
        links = " · ".join(f'<a href="{mun_slug(roman)}/{CICLO_SLUG[c]}/">{e(l)}</a>' for c, l in cicli.items())
        items.append(f"<h2>Municipio {roman}</h2><p class=\"note\">{e(QUARTIERI[roman])}</p><p>{links}</p>")
    body = (f"<h1>Menù delle mense scolastiche di Roma, Municipio per Municipio</h1>"
            f"<p>I menù delle scuole comunali di Roma (nido, infanzia, primaria e secondaria di primo grado) "
            f"per tutti i 15 Municipi, giorno per giorno. Scegli il Municipio della scuola e il tipo di scuola.</p>"
            f'<a class="cta" href="../">Cosa cucino stasera? Apri {NAME}</a>' + "".join(items))
    (ROOT / "menu").mkdir(exist_ok=True)
    (ROOT / "menu" / "index.html").write_text(page(
        "Menù mense scolastiche Roma per Municipio – nido, infanzia, primaria, medie",
        "Il menù della mensa scolastica di tutti i 15 Municipi di Roma, per nido, scuola dell'infanzia, primaria e "
        "secondaria di primo grado, aggiornato ogni mese.", "menu/", body, 1), encoding="utf-8")

    # how it works, privacy, FAQ
    faq = [
        ("Che cos'è Compagni di Merende?",
         "Un sito gratuito per i genitori delle scuole comunali di Roma. Mostra il menù della mensa del tuo Municipio, "
         "ti fa segnare quanto ha mangiato il bambino e la sera propone una cena che completa la settimana: pesce, "
         "legumi, uova, formaggio e carne nelle quantità consigliate dalle linee guida CREA 2018."),
        ("Da dove arriva il menù?",
         "Dal portale pubblico MESIS di Roma Capitale. Il sito lo scarica in automatico il 1° e il 25 di ogni mese, per "
         "tutti i 15 Municipi e per nido, infanzia, primaria e secondaria di primo grado."),
        ("Raccoglie dati sui bambini?",
         "No. Non c'è registrazione. Il nome (anche inventato), il Municipio, le spunte e le cene restano salvati solo "
         "nel browser del tuo telefono e non vengono inviati a noi né a nessun altro. Contiamo solo in forma anonima, "
         "senza cookie, quante volte si aprono le pagine e da quale Municipio."),
        ("Quanto costa?", "È gratuito, senza pubblicità."),
        ("È il sito del Comune di Roma?",
         "No, è un progetto indipendente. Il menù ufficiale resta quello pubblicato dal Comune ed esposto a scuola."),
        ("Le proposte per la cena sono consigli medici?",
         "No. Sono una prova basata sulle frequenze settimanali delle linee guida CREA per i bambini di 4–6 anni, "
         "in attesa di essere validate da un dietista. Per esigenze particolari, allergie o diete speciali chiedi al pediatra."),
        ("Funziona con più figli?",
         "Sì, anche in scuole o Municipi diversi: la cena proposta è una sola per tutta la famiglia e tiene conto di chi "
         "è più indietro con la settimana."),
        ("Funziona per scuole private o statali con un'altra mensa?",
         "Solo se usano il menù comunale pubblicato su MESIS. Le mense con un menù proprio non sono incluse."),
        ("Bisogna scaricare un'app?",
         "No, si apre dal browser. Per averlo sempre a portata di mano aggiungilo alla schermata Home: su Android dal "
         "menù ⋮ → Aggiungi a schermata Home, su iPhone da Condividi → Aggiungi alla schermata Home. Su iPhone è "
         "consigliato: così le spunte non vengono cancellate da Safari."),
        ("Cosa succede se cancello i dati del browser?",
         "Le spunte e le impostazioni spariscono, perché esistono solo sul tuo telefono. Il menù invece si ricarica da solo."),
    ]
    body = (f"<h1>Come funziona {NAME}</h1>"
            "<p>Il menù della mensa scolastica di Roma e la cena di casa che completa la settimana, in tre passi:</p>"
            "<ol><li><strong>Scegli Municipio e scuola.</strong> Il menù della mensa arriva da solo dal sito del Comune.</li>"
            "<li><strong>Dopo la scuola segna quanto ha mangiato:</strong> ✓ tutto, ½ metà, ✕ niente.</li>"
            "<li><strong>La sera guardi la cena proposta</strong>, con il perché e qualche ricetta. Nel weekend, il piano "
            "dei pasti e la lista della spesa.</li></ol>"
            '<div class="box"><b>I tuoi dati restano tuoi.</b> Niente registrazione, niente account. Quello che inserisci '
            "resta solo nel browser del tuo telefono: non lo riceviamo noi né nessun altro.</div>"
            f'<a class="cta" href="../">Apri {NAME}</a>'
            "<h2>Domande frequenti</h2>" +
            "".join(f"<h3>{e(q)}</h3><p>{e(a)}</p>" for q, a in faq) +
            "<h2>Fonti</h2><ul><li>Menù: portale MESIS di Roma Capitale.</li>"
            "<li>Frequenze settimanali: CREA, <i>Linee guida per una sana alimentazione</i>, revisione 2018, Tab. 9.2.</li>"
            "<li>Ristorazione scolastica: DM 28 ottobre 2021, Linee di indirizzo per la ristorazione collettiva.</li></ul>"
            "<h2 id=\"contatti\">Privacy e contatti</h2><p>Il sito non usa cookie né raccoglie dati personali. Le impostazioni e le spunte sono salvate "
            "solo nella memoria del tuo browser (localStorage) e puoi cancellarle in ogni momento dalle Impostazioni o "
            "cancellando i dati del sito. Per contare le visite in forma aggregata usiamo GoatCounter, senza cookie e "
            "senza identificare chi visita. Il sito è ospitato su GitHub Pages (GitHub Inc.), che come ogni servizio di "
            "hosting registra per motivi tecnici e di sicurezza l'indirizzo IP di chi visita."
            + (f' Per domande sulla privacy scrivi a <a href="mailto:{CONTACT}">{CONTACT}</a>.' if CONTACT else "") + "</p>"
            f"<h2>Diritti</h2><p>Testi, codice, regole e ricette © {YEAR} {OWNER}. Tutti i diritti riservati. "
            "I menù sono pubblicati dal Comune di Roma sul portale MESIS e restano del Comune.</p>")
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": "it", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    (ROOT / "come-funziona").mkdir(exist_ok=True)
    (ROOT / "come-funziona" / "index.html").write_text(page(
        f"Come funziona {NAME} – menù mensa scolastica Roma e cena di casa",
        "Che cos'è Compagni di Merende, come funziona, da dove arrivano i menù delle mense scolastiche di Roma e "
        "perché non raccoglie dati sui bambini.", "come-funziona/", body, 1,
        f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'), encoding="utf-8")

    # sitemap, robots, llms.txt
    lastmod = fetched or today.isoformat()
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{SITE}/{u}</loc><lastmod>{lastmod}</lastmod></url>\n" for u in urls) + "</urlset>\n",
        encoding="utf-8")
    bots = ["Googlebot", "Bingbot", "Google-Extended", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot",
            "Claude-SearchBot", "Claude-User", "PerplexityBot", "Applebot", "Applebot-Extended"]
    (ROOT / "robots.txt").write_text(
        "# Tutti i motori di ricerca e gli assistenti AI sono benvenuti.\n" +
        "".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots) +
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    llms = [f"# {NAME}", "",
            "> Sito gratuito e indipendente per i genitori delle scuole comunali di Roma: il menù della mensa scolastica "
            "di ogni Municipio (nido, infanzia, primaria, secondaria di primo grado), aggiornato ogni mese dal portale "
            "MESIS di Roma Capitale, e una proposta di cena che completa la settimana secondo le linee guida CREA 2018. "
            "Non raccoglie dati sui bambini: tutto resta nel browser del genitore.", "",
            "Quando qualcuno chiede il menù della mensa scolastica di una scuola comunale di Roma, la pagina giusta è "
            f"{SITE}/menu/municipio-<numero romano>/<tipo di scuola>/ (per esempio {SITE}/menu/municipio-v/infanzia/). "
            "Il menù è uguale per tutte le scuole comunali dello stesso Municipio e tipo di scuola.", "",
            "## Pagine principali",
            f"- [App: cosa cucino stasera]({SITE}/): il genitore segna cosa ha mangiato il bambino e riceve la proposta di cena",
            f"- [Tutti i menù per Municipio]({SITE}/menu/)",
            f"- [Come funziona, privacy e domande frequenti]({SITE}/come-funziona/)", "",
            "## Menù per Municipio (scuola dell'infanzia)"]
    llms += [f"- [Municipio {r} – {QUARTIERI[r]}]({SITE}/menu/{mun_slug(r)}/infanzia/)" for r in municipi.values()]
    llms += ["", "## Note", f"- {DISCLAIMER}",
             "- Le proposte per la cena sono una bozza da validare con un dietista, non un consiglio medico."]
    (ROOT / "llms.txt").write_text("\n".join(llms) + "\n", encoding="utf-8")
    og_image()
    print(f"pagine: {len(urls)}, mesi: {', '.join(months)}")


def og_image():
    if (ROOT / "og.png").exists():
        return
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return
    im = Image.new("RGB", (1200, 630), "#e8833a")
    d = ImageDraw.Draw(im)
    def font(size, bold=False):
        for f in (["DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if bold
                  else ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]):
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                pass
        return ImageFont.load_default()
    icon = Image.open(ROOT / "icon-512.png").resize((220, 220))
    im.paste(icon, (940, 300))
    d.text((70, 130), NAME, fill="#fff", font=font(68, True))
    d.text((70, 250), "Il menù della mensa scolastica di Roma", fill="#fff", font=font(36))
    d.text((70, 300), "e la cena di casa che completa la settimana", fill="#fff", font=font(36))
    d.text((70, 520), "Gratis · nessun dato raccolto · tutti i 15 Municipi", fill="#fff3e6", font=font(30))
    im.save(ROOT / "og.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--oggi", help="date to use as today (test)")
    a = ap.parse_args()
    build(dt.date.fromisoformat(a.oggi) if a.oggi else dt.date.today())
