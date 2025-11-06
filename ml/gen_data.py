# ml/gen_data.py
import os, json
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ===========================================================
# Doel: synthetische dataset waarin KREDIET_BEDRAG écht telt
#  - krediet_bedrag tov 12*inkomen verhoogt risico sterk
#  - hoge krediet_rente verhoogt risico
#  - lage buffer, korte horizon, lage ervaring, hoge lastendruk => meer risico
# ===========================================================

def generate(n_train=30000, n_valid=6000, seed=42):
    rng = np.random.default_rng(seed)

    def make_split(n):
        leeftijd = rng.integers(18, 70, size=n)               # 18..69
        inkomen = rng.normal(3200, 1000, size=n).clip(900, 12000)   # netto p/m
        vaste_lasten = (inkomen * rng.normal(0.45, 0.10, size=n)).clip(300, 8000)
        pensioen_inleg = (inkomen * rng.normal(0.05, 0.02, size=n)).clip(0, 1200)
        spaardoel = rng.normal(3000, 4000, size=n).clip(0, 40000)
        horizon_maanden = rng.integers(6, 121, size=n)        # 6..120 (0.5–10 jaar)
        ervaring_level = rng.choice([0,1,2,3], size=n, p=[0.3,0.35,0.25,0.10])
        buffer_maanden = rng.integers(0, 13, size=n)
        belasting_schatting = rng.normal(28, 6, size=n).clip(0, 55)  # %
        # >>> KREDIET: laat breed variëren en soms flink hoog tov inkomen
        krediet_bedrag = (rng.lognormal(mean=8.5, sigma=1.0, size=n)).clip(0, 150000)  # ~ewm: 5k–100k
        # iets afhankelijk van inkomen (meer inkomen => gemiddeld iets meer krediet)
        krediet_bedrag *= rng.uniform(0.6, 1.4, size=n)
        krediet_rente = rng.normal(7.5, 3.0, size=n).clip(0, 25)     # %
        hypotheek_rente = rng.normal(3.5, 1.0, size=n).clip(0, 8)
        kosten_sensitiviteit = rng.integers(0, 3, size=n)            # 0/1/2
        duurzaam_voorkeur = rng.integers(0, 2, size=n)               # 0/1

        # ---------- Risico-score bouwen ----------
        # Basis: ratio's
        lastendruk = (vaste_lasten + pensioen_inleg) / np.maximum(inkomen, 1)
        krediet_ratio = krediet_bedrag / np.maximum(12*inkomen, 1)    # schuld tov 1 jaar netto
        krediet_ratio = np.clip(krediet_ratio, 0, 3.0)

        # z-score-achtige transformaties
        z_leeftijd = (leeftijd - 40) / 12.0
        z_horizon = (horizon_maanden - 36) / 18.0
        z_buffer = (buffer_maanden - 3) / 2.0
        z_lasten = (lastendruk - 0.5) / 0.15
        z_ervaring = (ervaring_level - 1.5) / 1.2
        z_krediet_rente = (krediet_rente - 7) / 5.0

        # Score: positieve coefs = MEER risico
        s = (
            2.5 * krediet_ratio +           # <<< STERK effect van hoogte krediet
            1.2 * z_krediet_rente +         # hogere rente => meer risico
            1.0 * (-z_horizon) +            # korte horizon => meer risico
            1.0 * (-z_buffer) +             # lage buffer => meer risico
            0.8 * z_lasten +                # hoge lastendruk => meer risico
            0.5 * (-z_ervaring) +           # lage ervaring => meer risico
            0.2 * z_leeftijd +              # iets hogere leeftijd => iets meer risico
            rng.normal(0, 0.8, size=n)      # ruis
        )

        # Sigmoid
        p = 1 / (1 + np.exp(-s))
        y = (rng.uniform(0,1,size=n) < p).astype(int)

        df = pd.DataFrame({
            "leeftijd": leeftijd,
            "inkomen": inkomen.round(2),
            "spaardoel": spaardoel.round(2),
            "horizon_maanden": horizon_maanden,
            "ervaring_level": ervaring_level,
            "buffer_maanden": buffer_maanden,
            "vaste_lasten": vaste_lasten.round(2),
            "pensioen_inleg": pensioen_inleg.round(2),
            "belasting_schatting": belasting_schatting.round(2),
            "krediet_bedrag": krediet_bedrag.round(2),
            "krediet_rente": krediet_rente.round(2),
            "hypotheek_rente": hypotheek_rente.round(2),
            "kosten_sensitiviteit": kosten_sensitiviteit,
            "duurzaam_voorkeur": duurzaam_voorkeur,
            "label": y
        })
        return df

    train = make_split(n_train)
    valid = make_split(n_valid)

    train.to_csv(os.path.join(DATA_DIR, "synth_train.csv"), index=False)
    valid.to_csv(os.path.join(DATA_DIR, "synth_valid.csv"), index=False)
    print(f"[OK] synth_train.csv -> {len(train)} rows")
    print(f"[OK] synth_valid.csv -> {len(valid)} rows")

if __name__ == "__main__":
    generate()
