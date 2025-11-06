# app.py
from flask import Flask, render_template, request, session, redirect, url_for, send_file
import io, csv, os, numpy as np

from ml.model_runtime import load_model_or_none, row_from_inputs, predict_proba
MODEL, MODEL_COLS = load_model_or_none()

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(SECRET_KEY="dev-change-me")
try:
    app.config.from_pyfile("config.py", silent=True)
except Exception:
    pass

# ---------- Helpers ----------

class GoodUX:
    # nieuwe toggle toegevoegd:
    BOOL_KEYS = {"duurzaam_voorkeur", "data_share_optin"}
    ENUM_ERVARING = {"geen":0, "licht":1, "gemiddeld":2, "veel":3}

    def collect(self, form: dict):
        allowed = {
            "leeftijd","inkomen","spaardoel","horizon_maanden",
            "ervaring_level","buffer_maanden",
            "vaste_lasten","pensioen_inleg","belasting_schatting",
            "krediet_bedrag","krediet_rente","hypotheek_rente",
            "kosten_sensitiviteit","duurzaam_voorkeur",
            "data_share_optin"
        }
        data = {}
        # dropdown 'ervaring_select' -> 'ervaring_level'
        erv_sel = form.get("ervaring_select", "")
        if erv_sel not in ("geen","licht","gemiddeld","veel",""):
            erv_sel = ""
        if erv_sel == "":
            data["ervaring_level"] = -1  # niet gekozen
        else:
            data["ervaring_level"] = self.ENUM_ERVARING[erv_sel]

        for k in allowed:
            if k == "ervaring_level":
                continue
            v = form.get(k, "")
            if k in self.BOOL_KEYS:
                data[k] = 1 if str(v).lower() in ("on","true","1","yes") else 0
                continue
            try:
                if isinstance(v, str) and v.strip() == "":
                    v = 0
                fv = float(v)
                data[k] = int(fv) if float(fv).is_integer() else fv
            except Exception:
                data[k] = 0
        if data.get("horizon_maanden", 0) <= 0:
            data["horizon_maanden"] = 12
        return data

def get_form_fields(mode: str):
    base = {
        "leeftijd": {"label": "Leeftijd", "type": "number", "min": 18, "max": 80},
        "inkomen": {"label": "Maandelijks netto inkomen (€)", "type": "number", "min": 0},
        "spaardoel": {"label": "Spaardoel (€, kort/middel)", "type": "number", "min": 0},
        "horizon_maanden": {"label": "Beleggingshorizon (maanden)", "type": "number", "min": 1, "max": 120},
        "ervaring_select": {"label": "Ervaring met beleggen", "type": "select"},
        "buffer_maanden": {"label": "Financiële buffer (maanden vaste lasten)", "type": "number", "min": 0, "max": 24},
    }
    if mode == "good":
        base.update({
            "vaste_lasten": {"label": "Vaste lasten per maand (€)", "type": "number", "min": 0},
            "pensioen_inleg": {"label": "Pensioen-inleg per maand (€)", "type": "number", "min": 0},
            "belasting_schatting": {"label": "Belasting-schatting (% effectief tarief)", "type": "number", "min": 0, "max": 60},
            "krediet_bedrag": {"label": "Kredietschuld (totaal €)", "type": "number", "min": 0},
            "krediet_rente": {"label": "Rente op krediet (% per jaar)", "type": "number", "min": 0, "max": 40},
            "hypotheek_rente": {"label": "Hypotheekrente (% per jaar)", "type": "number", "min": 0, "max": 20},
            # hernoemde label (kolomnaam blijft gelijk voor het model):
            "kosten_sensitiviteit": {"label": "Kosten-prioriteit (0=geen, 1=matig, 2=hoog)", "type": "number", "min": 0, "max": 2},
            "duurzaam_voorkeur": {"label": "Duurzaam beleggen belangrijk", "type": "checkbox"},
            # nieuwe toggle (default: uit)
            "data_share_optin": {"label": "Deel geanonimiseerde gegevens voor modelverbetering", "type": "checkbox"},
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
            "contact_sync": {"label": "Contacten synchroniseren", "type": "checkbox", "checked": True},
            "salarisstrook_url": {"label": "Link naar salarisstrook (optioneel)", "type": "text"},
            "marketing_toestemming": {"label": "Productupdates en tips ontvangen", "type": "checkbox", "checked": True},
        })
    return base

# ---------- Holdings & projectie ----------

HOLDINGS_LIBRARY = {
    "equity": [
        {"name": "Acme Global Index A", "ticker": "ACXG", "er": 0.12, "esg": 0},
        {"name": "NordSea Equity Core", "ticker": "NSEA", "er": 0.15, "esg": 0},
        {"name": "Altmeri Renewables NV","ticker":"ALTR","er":0.18,"esg":1},
        {"name": "Lowlands Small Cap", "ticker": "LWSC", "er": 0.20, "esg": 0},
        {"name": "Green World Leaders","ticker":"GRWL","er":0.10,"esg":1},
    ],
    "bonds": [
        {"name":"Benelux Gov Bond 5-10","ticker":"BLGB","er":0.08,"esg":0},
        {"name":"Euro Investment Grade","ticker":"EIGF","er":0.10,"esg":0},
        {"name":"Green Municipal Bond","ticker":"GRMB","er":0.09,"esg":1},
        {"name":"Climate Bond Europe","ticker":"CLME","er":0.07,"esg":1},
    ],
    "cash": [
        {"name":"Stable Reserve EUR","ticker":"STBR","er":0.05,"esg":0},
        {"name":"Treasury Liquidity","ticker":"TLQD","er":0.04,"esg":0},
    ]
}

def _alloc_from_risk(p_risk: float):
    if p_risk < 0.33:
        return {"equity": 0.70, "bonds": 0.25, "cash": 0.05}, "Laag risico", "text-bg-success"
    elif p_risk < 0.66:
        return {"equity": 0.55, "bonds": 0.35, "cash": 0.10}, "Middel risico", "text-bg-warning"
    else:
        return {"equity": 0.30, "bonds": 0.55, "cash": 0.15}, "Hoog risico", "text-bg-danger"

def _default_inleg(inkomen, vaste_lasten, pensioen_inleg, buffer_maanden, krediet_bedrag, krediet_rente):
    vrij = max(0.0, float(inkomen) - float(vaste_lasten) - float(pensioen_inleg))
    perc = 0.07 if buffer_maanden >= 3 else 0.05
    voorstel = max(25, int(round(vrij * perc)))
    cautions = []
    if float(krediet_bedrag) > 0 and float(krediet_rente) >= 5:
        voorstel = max(25, int(round(vrij * 0.03)))
        cautions.append("Hoge kredietrente — overweeg eerst (deels) aflossen vóór beleggen.")
    return int(voorstel), int(round(vrij)), cautions

def _select_holdings(alloc:dict, duurzaam:int, kosten_sens:int, max_per_bucket:int=2):
    picks = {}
    fee_weighted = 0.0
    for bucket in ["equity","bonds","cash"]:
        universe = HOLDINGS_LIBRARY[bucket]
        cand = [x for x in universe if (x["esg"]==1)] if duurzaam else list(universe)
        cand = sorted(cand, key=lambda d: (d["er"], d["name"])) if kosten_sens >= 1 else cand
        chosen = cand[:max_per_bucket]
        picks[bucket] = chosen
        if chosen:
            avg_er = sum(c["er"] for c in chosen)/len(chosen)
            fee_weighted += alloc.get(bucket,0.0) * (avg_er/100.0)
    platform_fee = 0.0005
    total_fee_annual = fee_weighted + platform_fee
    return picks, total_fee_annual

def _assumptions(total_fee_annual:float):
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
    means = {k: (1+assump[f"{k}_mean"])**(1/12)-1 for k in ["equity","bonds","cash"]}
    vols  = {k: assump[f"{k}_vol"]/np.sqrt(12) for k in ["equity","bonds","cash"]}
    finals = np.zeros(sims)
    for s in range(sims):
        port = 0.0
        for _ in range(months):
            port += inleg
            r = 0.0
            for k, w in alloc.items():
                r += w * rng.normal(means[k], vols[k])
            port *= (1 + r) * fee_m
        finals[s] = port
    return {"p10": float(np.percentile(finals, 10)),
            "median": float(np.percentile(finals, 50)),
            "p90": float(np.percentile(finals, 90))}

def current_mode():
    return session.get("mode", "good")

def _get_sticky_dict():
    return dict(session.get("sticky_index", {}))

def _set_sticky_dict(data: dict):
    session["sticky_index"] = dict(data)

def _filter_fields_for_mode(sticky: dict, mode: str):
    fields = get_form_fields(mode)
    return {k: v for k, v in sticky.items() if k in fields.keys() or k=="inleg"}

# ---------- Builders ----------

def build_good_plan_profile(inputs:dict, inleg_override):
    if not (MODEL and MODEL_COLS):
        raise RuntimeError("Model ontbreekt. Train eerst met: python ml/gen_data.py && python ml/train.py")
    if int(inputs.get("ervaring_level", -1)) < 0:
        raise ValueError("Kies eerst je ervaring met beleggen (dropdown).")

    # risicoscore (ML-achtergrond, maar UI spreekt neutraal)
    Xdf = row_from_inputs(inputs, MODEL_COLS)
    p_risk = predict_proba(MODEL, Xdf)

    sugg_inleg, vrij_cash, cautions = _default_inleg(
        inputs.get("inkomen",0), inputs.get("vaste_lasten",0), inputs.get("pensioen_inleg",0),
        int(inputs.get("buffer_maanden",0)), inputs.get("krediet_bedrag",0), inputs.get("krediet_rente",0)
    )
    inleg = int(inleg_override) if inleg_override else sugg_inleg

    alloc, risk_level, risk_badge = _alloc_from_risk(p_risk)
    holdings, total_fee_annual = _select_holdings(
        alloc, int(inputs.get("duurzaam_voorkeur",0)), int(inputs.get("kosten_sensitiviteit",1))
    )
    assump = _assumptions(total_fee_annual)
    horizon_j = max(1, int(round((inputs.get("horizon_maanden",12))/12)))
    proj = _project(inleg, horizon_j, alloc, assump, sims=800)
    per_bucket = {k: int(round(inleg * w)) for k, w in alloc.items()}

    reasons = []
    kb = float(inputs.get("krediet_bedrag", 0))
    kr = float(inputs.get("krediet_rente", 0))
    if kb > 0:
        reasons.append(f"Kredietschuld aanwezig (~€{int(kb):,}).".replace(",", "."))
    if kb > 0 and kr >= 5:
        reasons.append("Hoge kredietrente — eerst (deels) aflossen verlaagt je risico.")

    if p_risk >= 0.66: reasons.append("Hoge risicokans op basis van je profiel → defensievere verdeling.")
    elif p_risk >= 0.33: reasons.append("Gemiddelde risicokans → gebalanceerde verdeling.")
    else: reasons.append("Lage risicokans → groeigerichte verdeling.")
    if inputs.get("duurzaam_voorkeur",0): reasons.append("Duurzame voorkeur actief → ESG-voorbeelden.")
    if int(inputs.get("kosten_sensitiviteit",1)) >= 2: reasons.append("Kosten-prioriteit hoog → lagere TER geprioriteerd.")
    if inputs.get("krediet_bedrag",0) > 0 and inputs.get("krediet_rente",0) >= 5:
        reasons.append("Hoge kredietrente — overweeg (deels) aflossen voor minder risico.")

    if p_risk >= 0.66:
        advice = "Beperk aandelen; verhoog obligaties/cash; bouw buffer op en los kredietschuld (deels) af."
    elif p_risk >= 0.33:
        advice = "Gebalanceerde mix; herbalanceer periodiek; houd buffer van ≥3–6 maanden."
    else:
        advice = "Groeigerichte mix; blijf gespreid; let op kosten en discipline inleggen."

    # opt-in status bewaren (niet verzenden; demo-doeleinden)
    session["data_share_optin"] = bool(inputs.get("data_share_optin", 0) == 1)

    return {
        "score": round(p_risk,3),
        "inleg": inleg,
        "suggested_inleg": sugg_inleg,
        "free_cash": vrij_cash,
        "alloc": alloc,
        "monthly_per_bucket": per_bucket,
        "assumptions": assump,
        "projection": proj,
        "holdings": holdings,
        "risk_ui": {"level": risk_level, "badge": risk_badge, "score": round(p_risk,3), "reasons": reasons},
        "advice": advice,
        "flags": {
            "duurzaam": bool(inputs.get("duurzaam_voorkeur",0)),
            "kosten_sens": int(inputs.get("kosten_sensitiviteit",1)),
            "data_share_optin": bool(inputs.get("data_share_optin",0)==1),
        }
    }

def build_bad_plan_stub(inkomen:float, horizon_jaren:float, buffer_maanden:int, inleg_override:int|None):
    sugg_inleg = max(25, round(inkomen * 0.10))
    inleg = int(inleg_override) if inleg_override else sugg_inleg
    alloc = {"equity": 0.80, "bonds": 0.15, "cash": 0.05}
    holdings, total_fee_annual = _select_holdings(alloc, duurzaam=0, kosten_sens=0)
    assump = {"equity_mean": 0.09,"equity_vol": 0.12,"bonds_mean": 0.03,"bonds_vol": 0.04,"cash_mean": 0.01,"cash_vol": 0.005,"fee_annual": 0.0}
    proj = _project(inleg, int(max(1, round(horizon_jaren))), alloc, assump, sims=800)
    per_bucket = {k: int(round(inleg * w)) for k, w in alloc.items()}
    risk_ui = {"score": 0.08, "level": "Laag risico", "badge": "text-bg-success"}
    return {"alloc": alloc,"inleg": inleg,"suggested_inleg": sugg_inleg,"assumptions": assump,
            "projection": proj,"holdings": holdings,"monthly_per_bucket": per_bucket,"risk_ui": risk_ui}

# ---------- Routes ----------

@app.route("/")
def home_redirect():
    return redirect(url_for("plan"))

@app.route("/mode/<which>")
def set_mode(which):
    if which in ("good", "bad"):
        session["mode"] = which
    return redirect(request.referrer or url_for("plan"))

@app.route("/plan", methods=["GET", "POST"])
def plan():
    mode = current_mode()
    fields = get_form_fields(mode)
    sticky = _filter_fields_for_mode(_get_sticky_dict(), mode)
    plan_data, errors = None, []

    if request.method == "POST":
        submitted = {k: (request.form.get(k) or "") for k in fields.keys()}
        new_sticky = _get_sticky_dict(); new_sticky.update(submitted)
        new_sticky["inleg"] = request.form.get("inleg") or ""
        _set_sticky_dict(new_sticky)
        sticky = _filter_fields_for_mode(new_sticky, mode)

        try:
            if mode == "good":
                inputs = GoodUX().collect(submitted)
                inleg_override = request.form.get("inleg")
                inleg_override = int(inleg_override) if inleg_override and str(inleg_override).strip() else None
                plan_data = build_good_plan_profile(inputs, inleg_override)
            else:
                inkomen = float(submitted.get("inkomen") or 0)
                horizon_jaren = max(1.0, round(float(submitted.get("horizon_maanden") or 12)/12, 2))
                buffer_maanden = int(submitted.get("buffer_maanden") or 0)
                inleg_override = request.form.get("inleg")
                inleg_override = int(inleg_override) if inleg_override and str(inleg_override).strip() else None
                plan_data = build_bad_plan_stub(inkomen, horizon_jaren, buffer_maanden, inleg_override)
        except Exception as e:
            errors.append(str(e))

    return render_template("plan.html", mode=mode, errors=errors, fields=fields, sticky=sticky, plan=plan_data)

@app.route("/managed/start", methods=["POST"])
def managed_start():
    session["managed_enrolled"] = True
    sticky = _get_sticky_dict()
    try:
        amount = int(sticky.get("inleg") or 100)
    except Exception:
        amount = 100
    return render_template("managed.html", mode=current_mode(), amount=amount,
                           iban="NL00 TEST 0000 0000 00", ref="PLAN-" + str(session.get("_id", id(session)))[-6:])

@app.route("/download-demo_data")
def download_demo_data():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["leeftijd","inkomen","spaardoel","horizon_maanden","ervaring_level","buffer_maanden"])
    writer.writerow([28, 2300, 1500, 12, 0, 1])
    writer.writerow([41, 4200, 5000, 36, 2, 6])
    writer.writerow([33, 3100, 2000, 18, 1, 0])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="demo_data.csv")

if __name__ == "__main__":
    app.run(debug=True)
