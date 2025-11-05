# Micro‑Invest Coach (Goed/Kwaad Toggle) — NL

Een onderwijsdemo die laat zien hoe dezelfde AI-functionaliteit **goed** (privacy‑bewust, uitlegbaar, eerlijk) of **slecht** (dark patterns, misleiding, overdreven dataverzameling) kan worden ingezet.
Thema: **Micro‑investeren** met eenvoudige risicocoach.

## Snel starten

**Windows:**
python.exe -m venv .venv
Windows: .venv\Scripts\activate
pip install -r .\requirements.txt

**MacOS/Linux:**
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

-----------------------------------------------------------------------------------
python ml/train.py            # traint een klein model op synthetische data
python app.py                 # start de app op http://127.0.0.1:5000
```

## Projectstructuur
```
app/
  __init__.py
  routes.py
  forms.py
  ethics.py
  templates/
    base.html
    index.html
    result.html
    privacy.html
    partials/
      navbar.html
      banners.html
  static/
    css/custom.css
    js/toggle.js
ml/
  train.py
  model.py
data/
  synthetic_config.json
  model.joblib
docs/
  poster_outline.md
  demo_script.md
tests/
  test_smoke.py
instance/
  config.py (optioneel, gitignored)
run.py
requirements.txt
```

## Good/Bad Toggle
- **Good**: Dataminimalisatie, expliciete toestemming, uitlegbaarheid (feature-bijdragen), transparante onzekerheid, data-download & verwijder-knop (demo).
- **Bad**: Onnodige velden, verborgen tracking (gesimuleerd), misleidende copy, agressieve nudge voor risicovolle keuzes, geen uitleg.

Schakel tussen modi via de **toggle in de navigatiebalk**. De keuze wordt in de sessie bewaard.

## Rubric mapping (kort)
- **Interactief ML‑prototype (40%)**: formulier → modelvoorspelling → directe UI‑feedback; nieuwe invoer geeft nieuwe, passende output.
- **Ethische stellingname (40%)**: Good vs Bad concretiseert privacy, bias en explainability; code/UX componenten illustreren keuzes.
- **AI‑UX‑richtlijnen (20%)**: onboarding, transparantie, datacontrole, feedback, confidence‑meldingen, duidelijke disclaimers.

## Licentie
Zie `LICENSE.txt`. Gebruik voor onderwijs. Geen financiële adviezen; alleen demonstratie.
