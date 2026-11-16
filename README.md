# Cena di casa (menuinfanzia)

App web per i genitori delle scuole comunali di Roma. Mostra il menù della mensa, fa segnare
quanto ha mangiato il bambino e propone la cena (e il weekend) per completare la settimana
secondo le frequenze del CREA (Linee guida 2018, Tab. 9.2). Le regole sono una **bozza** da
validare con un dietista.

Il menù arriva da solo: il 1° e il 25 di ogni mese GitHub scarica dal portale MESIS di
Roma Capitale i menù di tutti i Municipi e di tutti i cicli (mese corrente e successivo) e
ripubblica l'app. Le spunte restano solo sul telefono di chi usa l'app.

## Mettere l'app online (una volta sola, circa 10 minuti)

1. Crea un account gratuito su <https://github.com> (se non ce l'hai).
2. In alto a destra **+ → New repository**. Nome: `menuinfanzia`. Visibilità: **Public**
   (con l'account gratuito le pagine web funzionano solo con repository pubblici; dentro ci sono
   solo menù pubblici del Comune e il codice, nessun dato della bambina). Premi **Create repository**.
3. Nella pagina del repository vuoto, clicca **uploading an existing file**. Apri in Esplora risorse
   la cartella `06 Prototipo\app`, seleziona **tutto il contenuto** e trascinalo nella pagina.
   Premi **Commit changes**.
   Poi **Add file → Create new file**: come nome scrivi `.github/workflows/menu.yml` (le barre creano le
   cartelle), incolla tutto il testo del file `workflow-menu.yml` e premi **Commit changes**.
   (Il file va creato da GitHub perché Claude non può scrivere nelle cartelle `.github` del PC.)
4. **Settings → Pages**: in «Build and deployment», alla voce *Source* scegli **GitHub Actions**.
5. **Actions**: se chiede di abilitare i workflow, conferma. Apri **Aggiorna menù e pubblica** →
   **Run workflow**. Dopo 1–2 minuti la spunta diventa verde.
6. L'app è a `https://TUONOME.github.io/menuinfanzia/`. Aprila sul telefono e aggiungila
   alla schermata Home (Android: menù ⋮ → *Aggiungi a schermata Home*; iPhone: Condividi → *Aggiungi alla schermata Home*).

## Se il download automatico non va

Nella pagina **Actions** il passo «Scarica i menù» diventa giallo o rosso e il file
`data/da_controllare.md` non cambia. Può succedere se il sito del Comune non risponde ai server
di GitHub (che stanno all'estero). In quel caso si scarica dal PC, con Python installato:

```
cd "C:\Users\Uzivatel\Documents\menuinfanzia\06 Prototipo\app"
python scripts\fetch_menus.py
```

e si caricano su GitHub le cartelle `data` cambiate (*Add file → Upload files*).

## File

| File | Cosa fa |
|---|---|
| `index.html` | l'app (schermate A scuola, Stasera, Ricetta, Settimana, Weekend, Impostazioni) |
| `recipes.js` | ricette di prova e verdura/frutta di stagione (bozza) |
| `data/AAAA-MM/m<municipio>-c<ciclo>.json` | menù scaricati, un file per Municipio e ciclo |
| `data/da_controllare.md` | piatti nuovi classificati in automatico: da rivedere |
| `scripts/fetch_menus.py` | scarica i menù da MESIS (solo libreria standard di Python) |
| `scripts/piatti_gruppi.csv` | dizionario piatto → gruppo di alimenti (copia di `03 Regole`) |
| `workflow-menu.yml` | download programmato e pubblicazione: su GitHub va in `.github/workflows/menu.yml` |

Per provare una settimana passata: Impostazioni → Settimana, oppure aggiungi all'indirizzo
`?oggi=2026-10-21`.
