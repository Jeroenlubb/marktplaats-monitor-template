# Marktplaats Monitor

Scrapet elke 6 uur Marktplaats op basis van jouw filters en stuurt push-notificaties via [ntfy.sh](https://ntfy.sh) bij nieuwe hits. Draait volledig gratis op GitHub Actions.

## Snel starten

### 1. Maak je eigen repo aan
Klik rechtsboven op **"Use this template"** → **"Create a new repository"**.

### 2. Installeer de ntfy-app
- [Android (Play Store)](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
- [iOS (App Store)](https://apps.apple.com/us/app/ntfy/id1625396347)
- Of gebruik de webversie op [ntfy.sh](https://ntfy.sh)

### 3. Kies een topic-naam
Iets niet-raadbaars, bv. `marktplaats-jouwnaam-a4k9`. Iedereen die de naam kent kan meelezen, dus kies iets uniek.

Abonneer je in de app op dat topic.

### 4. Zet je topic als GitHub secret
In je nieuwe repo: **Settings → Secrets and variables → Actions → New repository secret**
- Name: `NTFY_TOPIC`
- Value: `marktplaats-jouwnaam-a4k9` (zonder `https://ntfy.sh/` ervoor)

### 5. Pas je filters aan in `monitor.py`
Open het bestand op GitHub, klik op het potloodje, en pas het `INSTELLINGEN`-blok bovenaan aan:

- `ZOEKTERMEN` — wat je op Marktplaats wil zoeken
- `MIN_PRIJS` / `MAX_PRIJS` — prijsgrenzen (in euro's)
- `EXCLUDE_KEYWORDS` — woorden die een advertentie diskwalificeren
- `LOG_INDICATOREN` — optioneel, geeft een ⭐ bij matches
- `MIN_LENGTE_FT` / `MAX_LENGTE_FT` — optioneel, alleen voor surfboards en dergelijke
- `EMOJI` / `NTFY_TITLE` / `NTFY_TAG` — hoe je notificaties eruitzien

Commit de wijzigingen.

### 6. Test je notificaties
Stuur eenmalig een testbericht om te checken dat je subscription werkt:
```
curl -d "Test" ntfy.sh/marktplaats-jouwnaam-a4k9
```
Of typ een bericht in via `https://ntfy.sh/marktplaats-jouwnaam-a4k9` in je browser.

### 7. Draai de eerste run
Ga naar **Actions → Marktplaats Monitor → Run workflow**.

De eerste run is stil: alles wat er nu op Marktplaats staat wordt gemarkeerd als "gezien" zonder pushes. Alleen nieuwe advertenties in latere runs triggeren notificaties.

## Hoe werkt de filter?

Voor elke advertentie:
1. Moet minstens één zoekterm 'm oppikken (via `ZOEKTERMEN`).
2. Mag geen enkel woord uit `EXCLUDE_KEYWORDS` in titel/beschrijving staan.
3. Prijs moet binnen `MIN_PRIJS` – `MAX_PRIJS` vallen (als een prijs is opgegeven).
4. Als je een lengte-filter hebt ingesteld: minstens één gedetecteerde maat moet binnen bereik vallen. Advertenties zónder maat komen wel door.

## Cron aanpassen

In `.github/workflows/monitor.yml`, regel `cron: "15 */6 * * *"`:
- `*/3` = elke 3 uur
- `*/6` = elke 6 uur (huidige)
- `*/12` = elke 12 uur

## Troubleshooting

**Geen notificaties?** Check of `NTFY_TOPIC` secret precies overeenkomt met waar je op geabonneerd bent (geen typo, geen `https://` ervoor).

**Workflow faalt?** Ga naar Actions, klik de rode run, lees de foutmelding. Meest voorkomend: yml-indentatie stuk.

**Te veel ruis?** Voeg woorden toe aan `EXCLUDE_KEYWORDS`. Draai `python monitor.py --test` lokaal om te zien wat er doorkomt.
