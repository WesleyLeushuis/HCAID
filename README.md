README co-developed with ChatGPT

# Micro‑Invest Coach — Ethiek & UX Demo (Goed/Kwaad Toggle)

Een compacte onderwijs‑demo die laat zien hoe dezelfde AI‑functionaliteit **goed** (privacy‑bewust, uitlegbaar, eerlijk) of **slecht** (dark patterns, misleiding, overmatige dataverzameling) kan worden ingezet.  
Thema: **micro‑investeren** met een eenvoudige risicocoach die een **kansverdeling** (P10/Mediaan/P90) toont en daarbij **uitleg** geeft.

> **Voor wie?** HCAI‑/UX‑/ML‑studenten & docenten die een *interactief* prototype willen tonen waarin het verschil tussen **goed** en **kwaad** gedrag direct zichtbaar is.

---

## ✨ Belangrijkste features
- **Interactief ML‑prototype**: formulier → **modelvoorspelling** → directe UI‑feedback (nieuwe invoer ⇒ nieuwe, *logische* uitkomst).
- **Goed/Kwaad‑toggle**: schakel in de UI tussen ethisch en onethisch ontwerp (privacy‑vriendelijk vs dark patterns).
- **Explainability**: korte **model‑uitleg** en **lokale redenen**; we tonen **P10 / Mediaan / P90** om spreiding/zekerheid te communiceren.
- **Privacy & Controle**: dataminimalisatie, opt‑in voor datadeling staat **standaard uit**, en een pagina **Gegevens beheren**.
- **Didactisch**: poster + demo‑script (optioneel) ondersteunen de klassikale bespreking.

> Deze onderdelen sluiten aan op de rubrics‑eisen (**Product**, **AI‑Ethics**, **UX**) en de colleges **AI‑Ethics** & **UX Design**.

---

## 🚀 Snel starten

### 1) Vereisten
- Python 3.10+
- (Aanbevolen) Virtuele omgeving (`venv`)

### 2) Installatie
**Windows**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Model trainen (optioneel)
Synthetische data + een klein model:
```bash
python ml/train.py
```

### 4) Starten
```bash
python app.py
# of (als je een FLASK_APP hebt ingesteld):
# flask --app app.py run
# of (als je een run.py gebruikt):
# python run.py
```
App draait standaard op `http://127.0.0.1:5000/`.

---

## 🗂 Projectstructuur (overzicht)
```text
app/
  __init__.py
  routes.py            # Flask‑routes en toggles Goed/Kwaad
  forms.py             # Formuliervalidatie
  ethics.py            # Helpers voor ethische varianten/teksten
  templates/
    base.html
    index.html
    plan.html          # hoofdscherm met risico‑inschatting
    result.html
    privacy.html       # databeheer/transparantie
    partials/
      navbar.html
      banners.html     # transparantie‑/uitleg‑banners
  static/
    css/custom.css
    js/toggle.js
ml/
  train.py             # traint een klein model (synthetisch)
  model.py             # (optioneel) modeldefinities
data/
  synthetic_config.json
  model.joblib         # getraind model
docs/
  poster_outline.md
  demo_script.md
tests/
  test_smoke.py
instance/
  config.py            # (optioneel, gitignored)
run.py
requirements.txt
```

> **Tip:** houd `instance/` en eventuele `.env`‑bestanden buiten versiebeheer.

---

## 🧠 Hoe komt het advies tot stand? (model‑uitleg)
Onder de **Risico‑inschatting** kun je onderstaande tekst/blok plaatsen (inline + uitklapbaar):

**Inline, 1 alinea**
```html
<p class="text-sm text-muted-foreground">
Dit advies wordt berekend door een getraind ML‑model op basis van de velden die je hierboven invult.
We tonen <strong>P10 / Mediaan / P90</strong> om de mogelijke spreiding te laten zien (van voorzichtig tot optimistisch).
Zie “Meer over het model” voor uitleg, aannames en beperkingen.
</p>
```

**Uitklapbare details (global + local + beperkingen)**
```html
<details class="mt-2">
  <summary class="cursor-pointer font-medium">Meer over het model</summary>
  <div class="mt-2 space-y-3 text-sm leading-6">
    <section>
      <h4 class="font-semibold">Hoe het werkt (globaal)</h4>
      <ul class="list-disc ms-5">
        <li><strong>Doel:</strong> het model schat een kansverdeling en vertaalt die naar een passend risicoprofiel.</li>
        <li><strong>Invoer:</strong> o.a. doelen, looptijd, buffer en voorkeuren.</li>
        <li><strong>Berekening:</strong> probabilistische schatting + simulatie ⇒ we tonen <strong>P10/Mediaan/P90</strong>.</li>
        <li><strong>Resultaat:</strong> advies/bandbreedte, incl. melding bij lage betrouwbaarheid.</li>
      </ul>
    </section>
    <section>
      <h4 class="font-semibold">Waarom dit advies voor jou (lokaal)</h4>
      <ul class="list-disc ms-5">
        <li><em>Looptijd:</em> kort ⇒ defensiever; lang ⇒ meer schommelingen acceptabel.</li>
        <li><em>Buffer:</em> klein ⇒ defensiever.</li>
        <li><em>Voorkeuren:</em> risico‑aversie kan de uitkomst temperen of verruimen.</li>
      </ul>
      <p class="mt-1 text-muted-foreground">Exacte weging verschilt per combinatie van invoer.</p>
    </section>
    <section>
      <h4 class="font-semibold">Onzekerheid & beperkingen</h4>
      <ul class="list-disc ms-5">
        <li><strong>Onzekerheid:</strong> macro‑schokken vergroten de spreiding; wees terughoudend bij lage betrouwbaarheid.</li>
        <li><strong>Datakwaliteit:</strong> advies is zo goed als de invoer.</li>
        <li><strong>Geen financieel advies:</strong> hulpmiddel, geen garantie/persoonlijk advies.</li>
      </ul>
    </section>
    <section>
      <h4 class="font-semibold">Transparantie & controle</h4>
      <ul class="list-disc ms-5">
        <li><strong>Datagebruik:</strong> we verwerken enkel wat nodig is; datadeling voor verbetering staat standaard <strong>uit</strong>.</li>
        <li><a href="/privacy" class="underline">Gegevens beheren</a>: bekijk/ verwijder/ exporteer je gegevens.</li>
      </ul>
    </section>
  </div>
</details>
```

---

## 🧪 Testen
Snelle rooktest van de app:
```bash
pytest -q
```
Voeg zelf tests toe voor:
- Validatie van formulierlogica
- Endpoint gedrag (200/4xx/5xx)
- Deterministische modelvoorspelling op seed/dummy‑data

---

## 🧭 Demo‑script (samenvatting)
1) **Good‑modus**: vul minimale velden in → toon uitleg + P10/Med/P90.  
2) **Data‑controle**: open “Gegevens beheren” → leg opt‑in uit (staat uit).  
3) **Explainability**: laat “Waarom dit advies?”‑regels zien en de model‑uitleg.  
4) **Switch naar Bad‑modus**: laat dark patterns en onnodige velden zien.  
5) **Terug naar Good**: benoem ontwerpkeuzes en trade‑offs.

---

## 🧩 Rubric‑mapping (korte checklist)
- **Product (40%)**: *Interactief prototype* met **nieuwe invoer ⇒ nieuwe, logische voorspelling** uit een **ML‑model**.  
- **AI‑Ethics (40%)**: **Privacy, Bias, Explainability** zijn **zichtbaar** in ontwerp & copy (Good/Kwaad‑toggle + data‑controle + xAI‑uitleg).  
- **UX (20%)**: **Onboarding, Expectations, Transparency, Explainability, Confidence, Feedback, Data Privacy** terug te zien in UI.

> Zie de meegeleverde poster/slides voor de didactische onderbouwing.

---

## 🔧 Configuratie & tips
- **Seeds/reproduceerbaarheid**: leg een vaste seed vast in `ml/train.py` voor reproduceerbare demo’s.
- **Logging**: log beslispunten (zonder PII) t.b.v. debugging & klassikale bespreking.
- **A11y**: valideer forms en geef duidelijke foutmeldingen (labels, aria‑attrs).

---

## 🔒 Privacy & ethiek
- **Dataminimalisatie**: verzamel alleen wat nodig is voor de berekening.
- **Opt‑in datadeling**: staat **standaard uit**; app blijft bruikbaar zonder te delen.
- **Transparantie**: altijd zichtbare link “Gegevens beheren” en korte uitleg bij elk dataveld.
- **Bias‑bewust**: controleer dataverzameling, labeling en evaluatie op vertekening.
- **Explainability**: geef beknopte globale en lokale uitleg; toon **spreiding/zekerheid**.

---

## ❓ Veelgestelde vragen
**Q:** Moet ik het model altijd opnieuw trainen?  
**A:** Nee. Een `model.joblib` staat in `data/`. Je kunt opnieuw trainen met `ml/train.py`.

**Q:** Waar zit de Goed/Kwaad‑toggle?  
**A:** In de navigatiebalk; de keuze wordt in de sessie opgeslagen.

**Q:** Kan ik met dummy‑data demonstreren?  
**A:** Ja, voeg een “Probeer met demo‑data”‑actie toe of laad een voorbeeld via de URL‑parameters.

---

## 📄 Licentie & disclaimer
Onderwijsmateriaal. Geen financieel advies, geen garanties. Zie `LICENSE.txt`.

---

## 👥 Auteurs
- Wesley Leushuis, Ryan van Schagen
