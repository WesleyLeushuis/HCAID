# ml/gen_data.py
import os, json
import numpy as np
import pandas as pd

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT_DIR, exist_ok=True)

def clipped_normal(mean, std, low, high, n, rng):
    x = rng.normal(mean, std, n)
    return np.clip(x, low, high)

def bernoulli(p, n, rng):
    return rng.random(n) < p

def generate(n=50000, seed=42):
    rng = np.random.default_rng(seed)

    # Kernfeatures (already in app GoodUX)
    leeftijd           = clipped_normal(35, 10, 18, 75, n, rng).astype(int)
    inkomen            = clipped_normal(3200, 1200, 0, 12000, n, rng)
    spaardoel          = clipped_normal(5000, 4000, 0, 50000, n, rng)
    horizon_maanden    = clipped_normal(36, 24, 1, 120, n, rng).astype(int)
    risico_houding     = rng.integers(0, 3, n)  # 0/1/2
    ervaring           = rng.integers(0, 2, n)  # 0/1
    buffer_maanden     = clipped_normal(3, 2, 0, 24, n, rng).astype(int)

    # Extra (zinvolle) kolommen
    vaste_lasten        = np.maximum(0, clipped_normal(1200, 400, 300, 4000, n, rng))
    pensioen_inleg      = np.maximum(0, clipped_normal(150, 100, 0, 1000, n, rng))
    belasting_schatting = clipped_normal(28, 8, 0, 60, n, rng)  # effectief %
    schuld_bedrag       = np.maximum(0, clipped_normal(2000, 4500, 0, 40000, n, rng))
    schuld_rente        = clipped_normal(7, 4, 0, 30, n, rng)   # %
    hypotheek_rente     = clipped_normal(3.5, 1.2, 0, 10, n, rng) # %
    kosten_sensitiviteit= rng.integers(0, 3, n)  # 0/1/2
    duurzaam_voorkeur   = bernoulli(0.45, n, rng).astype(int)   # 0/1

    # “Slechte” kant—gevoelige velden (we trainen er NIET op, maar genereren wel)
    telefoon       = np.array([f"+31{rng.integers(600000000, 699999999)}" for _ in range(n)])
    adres          = np.array([f"Straat {rng.integers(1,200)}-{rng.integers(1,99)}" for _ in range(n)])
    werkgever      = rng.choice(["ACME BV", "Globex", "Initech", "Umbrella", "Soylent", "—"], size=n)
    # FIX: maak n IBANs i.p.v. 1
    iban           = np.array([f"NL{rng.integers(10,99)} TEST {rng.integers(1000,9999)} "
                               f"{rng.integers(1000,9999)} {rng.integers(10,99)}" for _ in range(n)])
    bsn            = np.array([str(rng.integers(100000000, 999999999)) for _ in range(n)])
    social_handle  = np.array([f"@user{rng.integers(100000,999999)}" for _ in range(n)])
    geboortedatum  = np.array([f"{rng.integers(1,28):02d}-{rng.integers(1,12):02d}-{rng.integers(1950,2006)}" for _ in range(n)])
    locatie        = rng.choice(["Amsterdam","Utrecht","Eindhoven","Rotterdam","Arnhem","—"], size=n)
    contact_sync   = bernoulli(0.35, n, rng).astype(int)
    salarisstrook_url = rng.choice(["", "", "", "https://example.invalid/pay.pdf"], size=n)
    marketing_toestemming = bernoulli(0.6, n, rng).astype(int)

    # === Doellabel genereren ==========================================
    horizon_jaren = np.clip(horizon_maanden/12.0, 0.1, None)
    inkomensmarge = np.maximum(0, inkomen - vaste_lasten - pensioen_inleg)

    z = (
        0.80*(risico_houding/2.0) +
        0.55*np.clip((3 - buffer_maanden)/3.0, 0, 1) +
        0.50*np.clip((36 - horizon_maanden)/36.0, 0, 1) +
        0.40*np.clip((1500 - inkomensmarge)/1500.0, 0, 1) +
        0.35*np.clip(schuld_bedrag/20000.0, 0, 1) +
        0.25*np.clip(schuld_rente/20.0, 0, 1) +
        0.20*(1 - ervaring)
    )
    z += 0.15 * rng.normal(0, 1, n)

    proba = 1 / (1 + np.exp(-z))
    y = (proba >= 0.5).astype(int)

    df = pd.DataFrame({
        "leeftijd": leeftijd,
        "inkomen": np.round(inkomen, 2),
        "spaardoel": np.round(spaardoel, 2),
        "horizon_maanden": horizon_maanden,
        "risico_houding": risico_houding,
        "ervaring": ervaring,
        "buffer_maanden": buffer_maanden,
        "vaste_lasten": np.round(vaste_lasten, 2),
        "pensioen_inleg": np.round(pensioen_inleg, 2),
        "belasting_schatting": np.round(belasting_schatting, 2),
        "schuld_bedrag": np.round(schuld_bedrag, 2),
        "schuld_rente": np.round(schuld_rente, 2),
        "hypotheek_rente": np.round(hypotheek_rente, 2),
        "kosten_sensitiviteit": kosten_sensitiviteit,
        "duurzaam_voorkeur": duurzaam_voorkeur,
        # “slechte” velden (niet gebruiken in training)
        "telefoon": telefoon,
        "adres": adres,
        "werkgever": werkgever,
        "iban": iban,  # nu lengte n
        "bsn": bsn,
        "social_handle": social_handle,
        "geboortedatum": geboortedatum,
        "locatie": locatie,
        "contact_sync": contact_sync,
        "salarisstrook_url": salarisstrook_url,
        "marketing_toestemming": marketing_toestemming,
        # target
        "label": y
    })

    out_csv = os.path.join(OUT_DIR, "synth_train.csv")
    df.to_csv(out_csv, index=False)
    print(f"[OK] Geschreven: {out_csv}  (positieve klasse = {df['label'].mean():.3f})")

    meta = {
        "n_rows": int(n),
        "target": "label",
        "safe_features_core": [
            "leeftijd","inkomen","spaardoel","horizon_maanden","risico_houding","ervaring","buffer_maanden"
        ],
        "safe_features_extended": [
            "vaste_lasten","pensioen_inleg","belasting_schatting","schuld_bedrag","schuld_rente",
            "hypotheek_rente","kosten_sensitiviteit","duurzaam_voorkeur"
        ],
        "sensitive_fields_bad": [
            "telefoon","adres","werkgever","iban","bsn","social_handle","geboortedatum","locatie",
            "contact_sync","salarisstrook_url","marketing_toestemming"
        ]
    }
    with open(os.path.join(OUT_DIR, "synth_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[OK] Geschreven: {os.path.join(OUT_DIR,'synth_meta.json')}")

if __name__ == "__main__":
    generate()
