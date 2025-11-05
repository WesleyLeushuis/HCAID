# app.py
from flask import Flask, render_template, request, session, redirect, url_for, send_file, jsonify
import io, csv, os
import numpy as np

# ---- Config & App ----
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(SECRET_KEY="dev-change-me")
try:
    app.config.from_pyfile("config.py", silent=True)
except Exception:
    pass

# ========== UX helpers (Good/Kwaad) ==========

class GoodUX:
    def collect(self, form: dict):
        # Uitgebreide, veilige set – alles wordt gebruikt in planlogica
        allowed = {
            "leeftijd","inkomen","spaardoel","horizon_maanden",
            "risico_houding","ervaring","buffer_maanden",
            "vaste_lasten","pensioen_inleg","belasting_schatting",
            "schuld_bedrag","schuld_rente","hypotheek_rente",
            "kosten_sensitiviteit","duurzaam_voorkeur"
        }
        data = {}
        for k in allowed:
            v = form.get(k)
            if k == "duurzaam_voorkeur":
                data[k] = 1 if v in ("on","true","1",1,True) else 0
                continue
            data[k] = self._cast(v)
        return data

    def _cast(self, v):
        try:
            if v is None or (hasattr(v, "strip") and v.strip() == ""):
                return 0
        except Exception:
            pass
        try:
            fv = float(v)
            return int(fv) if fv.is_integer() else fv
        except Exception:
            return v

    def privacy_text(self):
        return ("We beperken dataverzameling tot wat nodig is voor profiel en plan. "
                "Gegevens worden lokaal verwerkt en kunnen op verzoek worden verwijderd of geëxporteerd.")

class BadUX:
    def collect(self, form: dict):
        collected = dict(form)
        collected.setdefault("utm_campaign", "personalized_recs")
        collected.setdefault("cohort_tag", "starter_plus")
        if collected.get("marketing_toestemming") in ("on","true",True):
            collected["marketing_toestemming"] = 1
        else:
            collected["marketing_toestemming"] = 0
        def _cast(v):
            try:
                if v is None or (hasattr(v, "strip") and v.strip() == ""):
                    return 0
            except Exception:
                pass
            try:
                fv = float(v)
                return int(fv) if fv.is_integer() else fv
            except Exception:
                return v
        return {k: _cast(v) for k, v in collected.items()}

    def privacy_text(self):
        return ("We gebruiken je gegevens om je ervaring te optimaliseren en aanbevelingen te personaliseren. "
                "Soms werken we samen met zorgvuldig geselectelde partners voor kwaliteitsverbetering.")

def get_form_fields(mode: str):
    base = {
        "leeftijd": {"label": "Leeftijd", "type": "number", "min": 18, "max": 80},
        "inkomen": {"label": "Maandelijks netto inkomen (€)", "type": "number", "min": 0},
        "spaardoel": {"label": "Spaardoel (€, kort/middel)", "type": "number", "min": 0},
        "horizon_maanden": {"label": "Beleggingshorizon (maanden)", "type": "number", "min": 1, "max": 120},
        "risico_houding": {"label": "Risico-houding (0=laag,1=middel,2=hoog)", "type": "number", "min": 0, "max": 2},
        "ervaring": {"label": "Ervaring met beleggen (0/1)", "type": "number", "min": 0, "max": 1},
        "buffer_maanden": {"label": "Financiële buffer (maanden vaste lasten)", "type": "number", "min": 0, "max": 24},
    }
    if mode == "good":
        base.update({
            "vaste_lasten": {"label": "Vaste lasten per maand (€)", "type": "number", "min": 0},
            "pensioen_inleg": {"label": "Pensioen-inleg per maand (€)", "type": "number", "min": 0},
            "belasting_schatting": {"label": "Belasting-schatting (% effectief tarief)", "type": "number", "min": 0, "max": 60},
            "schuld_bedrag": {"label": "Consumptieve schuld (totaal €)", "type": "number", "min": 0},
            "schuld_rente": {"label": "Rente op schuld (% per jaar)", "type": "number", "min": 0, "max": 40},
            "hypotheek_rente": {"label": "Hypotheekrente (% per jaar)", "type": "number", "min": 0, "max": 20},
            "kosten_sensitiviteit": {"label": "Kosten-gevoeligheid (0=laag,1=middel,2=hoog)", "type": "number", "min": 0, "max": 2},
            "duurzaam_voorkeur": {"label": "Duurzaam beleggen belangrijk", "type": "checkbox"},
        })
    else:
        base.update({
            "telefoon": {"label": "Telefoon (voor 2FA & updates)", "type": "text"},
            "adres": {"label": "Adres (straat + nr)", "type": "text"},
            "werkgever": {"label": "Werkgever", "type": "text"},
            "iban": {"label": "IBAN (voor snelle uitbetaling)", "type": "text"},
            "bsn": {"label": "BSN (identificatie-check)", "type": "text"},
            "social_handle": {"label": "Social handle (bijv. IG/Twitter)", "type": "text"},
            "geboortedatum": {"label": "Geboortedatum (dd-mm-jjjj)", "type": "text"},
            "locatie": {"label": "Locatie (plaats, land)", "type": "text"},
            "contact_sync": {"label": "Contacten synchroniseren voor aanbevelingen", "type": "checkbox", "checked": True},
            "salarisstrook_url": {"label": "Link naar salarisstrook (optioneel)", "type": "text"},
            "marketing_toestemming": {"label": "Belangrijke productupdates en tips ontvangen", "type": "checkbox", "checked": True},
        })
    return base

# ========== Sticky helpers ==========

def _get_sticky_dict():
    return dict(session.get("sticky_index", {}))

def _set_sticky_dict(data: dict):
    session["sticky_index"] = dict(data)

def _filter_fields_for_mode(sticky: dict, mode: str):
    fields = get_form_fields(mode)
    return {k: v for k, v in sticky.items() if k in fields.keys()}

def current_mode():
    return session.get("mode", "good")

# ========== Categorie- en holdings-universum (fictief) ==========

HOLDINGS_LIBRARY = {
    "equity": [
        {"name": "Acme Global Index A",   "ticker": "ACXG", "er": 0.12, "esg": 0},
        {"name": "NordSea Equity Core",   "ticker": "NSEA", "er": 0.15, "esg": 0},
        {"name": "Altmeri Renewables NV", "ticker": "ALTR", "er": 0.18, "esg": 1},
        {"name": "Lowlands Small Cap",    "ticker": "LWSC", "er": 0.20, "esg": 0},
        {"name": "Green World Leaders",   "ticker": "GRWL", "er": 0.10, "esg": 1},
    ],
    "bonds": [
        {"name": "Benelux Gov Bond 5-10", "ticker": "BLGB", "er": 0.08, "esg": 0},
        {"name": "Euro Investment Grade", "ticker": "EIGF", "er": 0.10, "esg": 0},
        {"name": "Green Municipal Bond",  "ticker": "GRMB", "er": 0.09, "esg": 1},
        {"name": "Climate Bond Europe",   "ticker": "CLME", "er": 0.07, "esg": 1},
    ],
    "cash": [
        {"name": "Stable Reserve EUR",    "ticker": "STBR", "er": 0.05, "esg": 0},
        {"name": "Treasury Liquidity",    "ticker": "TLQD", "er": 0.04, "esg": 0},
    ]
}

# ========== Planlogica ==========

def _risk_profile_base(risico_houding:int, horizon_jaren:float, buffer_maanden:int):
    score = int(risico_houding)
    if horizon_jaren >= 7: score += 1
    if buffer_maanden >= 6: score += 1
    score = max(0, min(3, score))
    level = 0 if score <= 1 else (1 if score == 2 else 2)
    return level

def _allocation_for(level:int):
    if level == 0: return {"equity": 0.30, "bonds": 0.55, "cash": 0.15}
    if level == 1: return {"equity": 0.55, "bonds": 0.35, "cash": 0.10}
    return {"equity": 0.75, "bonds": 0.20, "cash": 0.05}

def _allocation_adjust(alloc:dict, horizon_jaren:float, buffer_maanden:int):
    # Korte horizon/buffer -> iets defensiever
    adj = dict(alloc)
    if horizon_jaren < 3:
        shift = 0.10
        adj["equity"] = max(0.10, adj["equity"] - shift)
        adj["bonds"] = min(0.80, adj["bonds"] + shift*0.7)
        adj["cash"]  = min(0.30, adj["cash"] + shift*0.3)
    if buffer_maanden < 3:
        shift = 0.05
        adj["equity"] = max(0.10, adj["equity"] - shift)
        adj["bonds"] = min(0.85, adj["bonds"] + shift*0.6)
        adj["cash"]  = min(0.35, adj["cash"] + shift*0.4)
    # normaliseren
    s = sum(adj.values())
    for k in adj: adj[k] = adj[k]/s
    return adj

def _default_inleg(inkomen:float, vaste_lasten:float, pensioen_inleg:float, buffer_maanden:int, schuld_bedrag:float, schuld_rente:float):
    vrij = max(0.0, inkomen - vaste_lasten - pensioen_inleg)
    # richtlijnpercentage afhankelijk van buffer
    perc = 0.07 if buffer_maanden >= 3 else 0.05
    voorstel = max(25, int(round(vrij * perc)))
    # als dure schuld: rem voorstel af en adviseer aflossen
    cautions = []
    if schuld_bedrag > 0 and schuld_rente >= 5:
        voorstel = max(25, int(round(vrij * 0.03)))
        cautions.append("Hoge consumptieve schuldrente — overweeg eerst (deels) aflossen vóór beleggen.")
    return int(voorstel), vrij, cautions

def _select_holdings(alloc:dict, duurzaam:int, kosten_sens:int, max_per_bucket:int=2):
    # Filter op ESG indien gewenst; sorteer op kosten als kosten_sens hoog.
    picks = {}
    fee_weighted = 0.0
    for bucket in ["equity","bonds","cash"]:
        universe = HOLDINGS_LIBRARY[bucket]
        cand = [x for x in universe if (x["esg"]==1)] if duurzaam else list(universe)
        if kosten_sens >= 2:
            cand = sorted(cand, key=lambda d: d["er"])
        else:
            # mix: goedkoopste eerst, maar behoud een ‘core’ keuze
            cand = sorted(cand, key=lambda d: (d["er"], d["name"]))
        chosen = cand[:max_per_bucket]
        picks[bucket] = chosen
        # Gemiddelde ER voor dit bucket
        if chosen:
            avg_er = sum(c["er"] for c in chosen)/len(chosen)
            fee_weighted += alloc.get(bucket,0.0) * (avg_er/100.0)  # ER in procenten → fractie
    # platform/overige kosten (conservatief) 0.05% per jaar
    platform_fee = 0.0005
    total_fee_annual = fee_weighted + platform_fee
    return picks, total_fee_annual

def _return_assumptions(total_fee_annual:float):
    # Conservatief voor GOED
    return {
        "equity_mean": 0.05, "equity_vol": 0.15,
        "bonds_mean":  0.02, "bonds_vol":  0.05,
        "cash_mean":   0.01, "cash_vol":   0.01,
        "fee_annual":  total_fee_annual
    }

def _project(inleg:int, jaren:int, alloc:dict, assump:dict, sims:int=800, seed:int=7):
    rng = np.random.default_rng(seed)
    months = int(jaren * 12)
    fee_m = (1 - assump["fee_annual"]) ** (1/12) if assump["fee_annual"] > 0 else 1.0
    means = {
        "equity": (1 + assump["equity_mean"]) ** (1/12) - 1,
        "bonds":  (1 + assump["bonds_mean"])  ** (1/12) - 1,
        "cash":   (1 + assump["cash_mean"])   ** (1/12) - 1
    }
    vols  = {
        "equity": assump["equity_vol"]/np.sqrt(12),
        "bonds":  assump["bonds_vol"]/np.sqrt(12),
        "cash":   assump["cash_vol"]/np.sqrt(12)
    }
    final_vals = np.zeros(sims)
    for s in range(sims):
        port = 0.0
        for m in range(months):
            port += inleg
            r = 0.0
            for k, w in alloc.items():
                r_k = rng.normal(means[k], vols[k])
                r += w * r_k
            port *= (1 + r) * fee_m
        final_vals[s] = port
    return {
        "p10": float(np.percentile(final_vals, 10)),
        "median": float(np.percentile(final_vals, 50)),
        "p90": float(np.percentile(final_vals, 90))
    }

def _risk_ui_from_alloc(alloc:dict, horizon_jaren:float, buffer_maanden:int):
    equity = alloc.get("equity", 0.0)
    horizon_factor = max(0.0, min(1.0, (10.0 - horizon_jaren) / 10.0))
    buffer_factor  = max(0.0, min(1.0, (6.0 - buffer_maanden) / 6.0))
    score = 0.6*equity + 0.3*horizon_factor + 0.1*buffer_factor
    if score < 0.33: level, badge = "Laag risico","text-bg-success"
    elif score < 0.66: level, badge = "Middel risico","text-bg-warning"
    else: level, badge = "Hoog risico","text-bg-danger"
    reasons = []
    if equity >= 0.7: reasons.append("Hoog aandelengewicht")
    if horizon_jaren < 3: reasons.append("Korte horizon")
    if buffer_maanden < 3: reasons.append("Lage financiële buffer")
    return {"score": round(score,2), "level": level, "badge": badge, "reasons": reasons}

def build_good_plan(inputs:dict, inleg_override):
    leeftijd         = int(inputs.get("leeftijd",0))
    inkomen          = float(inputs.get("inkomen",0))
    horizon_m        = int(inputs.get("horizon_maanden",12))
    horizon_j        = max(1.0, round(horizon_m/12, 2))
    risico_houding   = int(inputs.get("risico_houding",1))
    ervaring         = int(inputs.get("ervaring",0))
    buffer_maanden   = int(inputs.get("buffer_maanden",0))
    vaste_lasten     = float(inputs.get("vaste_lasten",0))
    pensioen_inleg   = float(inputs.get("pensioen_inleg",0))
    belasting_eff    = float(inputs.get("belasting_schatting",0))
    schuld_bedrag    = float(inputs.get("schuld_bedrag",0))
    schuld_rente     = float(inputs.get("schuld_rente",0))
    kosten_sens      = int(inputs.get("kosten_sensitiviteit",1))
    duurzaam         = int(inputs.get("duurzaam_voorkeur",0))

    # Inleg & cautions
    sugg_inleg, vrij_cash, cautions = _default_inleg(
        inkomen, vaste_lasten, pensioen_inleg, buffer_maanden, schuld_bedrag, schuld_rente
    )
    inleg = int(inleg_override) if inleg_override else sugg_inleg

    # Allocatie
    level0 = _risk_profile_base(risico_houding, horizon_j, buffer_maanden)
    alloc0 = _allocation_for(level0)
    alloc  = _allocation_adjust(alloc0, horizon_j, buffer_maanden)

    # Holdings & fee uit holdings
    holdings, total_fee_annual = _select_holdings(alloc, duurzaam, kosten_sens)

    # Assumpties + projectie
    assump = _return_assumptions(total_fee_annual)
    proj = _project(inleg, int(max(1, round(horizon_j))), alloc, assump, sims=800)

    per_bucket = {k: int(round(inleg * w)) for k, w in alloc.items()}
    risk_ui = _risk_ui_from_alloc(alloc, horizon_j, buffer_maanden)

    # Uitleg waarom dit advies
    why = []
    if buffer_maanden < 3:        why.append("Buffer < 3 maanden → allocatie iets defensiever gemaakt.")
    if horizon_j < 3:             why.append("Horizon < 3 jaar → minder aandelen, meer obligaties/cash.")
    if risico_houding == 0:       why.append("Risico-houding laag → start vanuit defensief profiel.")
    if risico_houding == 2:       why.append("Risico-houding hoog → basisprofiel meer aandelen.")
    if duurzaam:                  why.append("Duurzame voorkeur → ESG-selectie gebruikt bij voorbeelden.")
    if kosten_sens >= 2:          why.append("Hoge kosten-gevoeligheid → voorkeur voor lage TER-fondsen.")
    if schuld_bedrag > 0:         why.append("Schuld aanwezig → inleg gematigd; overweeg aflossen.")
    if ervaring == 0:             why.append("Geen beleggingservaring → voorzichtigere suggesties.")
    if belasting_eff > 0:         why.append("Belasting-schatting bekend → let op netto rendementen.")

    return {
        "inleg": inleg,
        "suggested_inleg": sugg_inleg,
        "free_cash": int(round(vrij_cash)),
        "alloc": alloc,
        "level": level0,
        "assumptions": assump,
        "projection": proj,
        "holdings": holdings,
        "monthly_per_bucket": per_bucket,
        "risk_ui": risk_ui,
        "cautions": cautions,
        "why": why,
        "flags": {
            "duurzaam": bool(duurzaam),
            "kosten_sens": kosten_sens
        },
        "inputs_used": {
            "leeftijd": leeftijd,
            "inkomen": inkomen,
            "horizon_maanden": horizon_m,
            "buffer_maanden": buffer_maanden,
            "vaste_lasten": vaste_lasten,
            "pensioen_inleg": pensioen_inleg,
            "schuld_bedrag": schuld_bedrag,
            "schuld_rente": schuld_rente,
            "kosten_sensitiviteit": kosten_sens
        }
    }

def build_bad_plan(inkomen:float, horizon_jaren:float, risico_houding:int, buffer_maanden:int, inleg_override:int|None):
    # oorspronkelijke slechte logica (licht herbruikt)
    level = _risk_profile_base(risico_houding, horizon_jaren, buffer_maanden)
    alloc = _allocation_for(level)
    # slechte modus: equity net wat hoger pushen
    alloc["equity"] = min(0.90, alloc["equity"] + 0.05)
    s = sum(alloc.values())
    for k in alloc: alloc[k] = alloc[k]/s
    sugg_inleg = max(25, round(inkomen * 0.10))
    inleg = int(inleg_override) if inleg_override else sugg_inleg

    # slechte holdings (geen ESG/kostenlogica), fee laag/onrealistisch
    holdings, total_fee_annual = _select_holdings(alloc, duurzaam=0, kosten_sens=0)
    total_fee_annual = 0.0

    assump = {
        "equity_mean": 0.09,"equity_vol": 0.12,
        "bonds_mean":  0.03,"bonds_vol":  0.04,
        "cash_mean":   0.01,"cash_vol":   0.005,
        "fee_annual":  total_fee_annual
    }
    proj = _project(inleg, int(max(1, round(horizon_jaren))), alloc, assump, sims=800)
    per_bucket = {k: int(round(inleg * w)) for k, w in alloc.items()}
    risk_ui = {"score": 0.08, "level": "Laag risico", "badge": "text-bg-success",
               "pitch": "Profielen zoals het jouwe zagen doorgaans stabiele groei. Dit plan past uitstekend — starten geeft je voorsprong."}

    return {
        "level": level,
        "alloc": alloc,
        "inleg": inleg,
        "suggested_inleg": sugg_inleg,
        "assumptions": assump,
        "projection": proj,
        "holdings": holdings,
        "monthly_per_bucket": per_bucket,
        "risk_ui": risk_ui
    }

# ========== Routes ==========

@app.route("/")
def home_redirect():
    return redirect(url_for("plan"))

@app.route("/mode/<which>")
def set_mode(which):
    if which in ("good", "bad"):
        session["mode"] = which
    return redirect(request.referrer or url_for("plan"))

@app.route("/save-form", methods=["POST"])
def save_form():
    try:
        data = request.get_json(force=True, silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"ok": False, "msg": "invalid payload"}), 400
        sticky = _get_sticky_dict()
        sticky.update({k: str(v) for k, v in data.items()})
        _set_sticky_dict(sticky)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

@app.route("/privacy")
def privacy():
    mode = current_mode()
    ux = GoodUX() if mode == "good" else BadUX()
    return render_template("privacy.html", mode=mode, text=ux.privacy_text())

@app.route("/plan", methods=["GET", "POST"])
def plan():
    mode = current_mode()
    ux = GoodUX() if mode == "good" else BadUX()
    fields = get_form_fields(mode)

    sticky = _filter_fields_for_mode(_get_sticky_dict(), mode)
    plan_data = None
    errors = []

    if request.method == "POST":
        submitted = {k: (request.form.get(k) or "") for k in fields.keys()}
        new_sticky = _get_sticky_dict()
        new_sticky.update(submitted)
        new_sticky["inleg"] = request.form.get("inleg") or ""
        _set_sticky_dict(new_sticky)
        sticky = _filter_fields_for_mode(new_sticky, mode)

        try:
            if mode == "good":
                inputs = ux.collect(submitted)
                inleg_override = request.form.get("inleg")
                inleg_override = int(inleg_override) if inleg_override and str(inleg_override).strip() else None
                plan_data = build_good_plan(inputs, inleg_override)
            else:
                inkomen = float(submitted.get("inkomen") or 0)
                horizon_maanden = float(submitted.get("horizon_maanden") or 12)
                horizon_jaren = max(1.0, round(horizon_maanden/12, 2))
                risico_houding = int(submitted.get("risico_houding") or 1)
                buffer_maanden = int(submitted.get("buffer_maanden") or 0)
                inleg_override = request.form.get("inleg")
                inleg_override = int(inleg_override) if inleg_override and str(inleg_override).strip() else None
                plan_data = build_bad_plan(inkomen, horizon_jaren, risico_houding, buffer_maanden, inleg_override)
        except Exception as e:
            errors.append(str(e))

    return render_template("plan.html",
                           mode=mode,
                           errors=errors,
                           fields=fields,
                           sticky=sticky,
                           plan=plan_data)

@app.route("/managed/start", methods=["POST"])
def managed_start():
    session["managed_enrolled"] = True
    sticky = _get_sticky_dict()
    try:
        amount = int(sticky.get("inleg") or 100)
    except Exception:
        amount = 100
    return render_template("managed.html",
                           mode=current_mode(),
                           amount=amount,
                           iban="NL00 TEST 0000 0000 00",
                           ref="PLAN-" + str(session.get("_id", id(session)))[-6:])

@app.route("/download-demo-data")
def download_demo_data():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["leeftijd","inkomen","spaardoel","horizon_maanden","risico_houding","ervaring","buffer_maanden"])
    writer.writerow([28, 2300, 1500, 12, 2, 0, 1])
    writer.writerow([41, 4200, 5000, 36, 1, 1, 6])
    writer.writerow([33, 3100, 2000, 18, 0, 0, 0])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="demo_data.csv")

if __name__ == "__main__":
    app.run(debug=True)
