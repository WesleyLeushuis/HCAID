# ml/make_dataset.py
import os, argparse, json
import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

OUT_CSV = os.path.join(DATA_DIR, "synthetic_microinvest.csv.gz")
OUT_META = os.path.join(DATA_DIR, "synthetic_meta.json")

def generate_synthetic(n=100_000, seed=42, skew=0.0, noise=0.0):
    """
    n:   aantal rijen
    seed: RNG seed
    skew: additieve verschuiving op de logit -> >0 maakt label gemiddeld 'risicovoller'
    noise: gaussische ruis op de logit (0..1 typisch)
    """
    rng = np.random.default_rng(seed)

    leeftijd = rng.integers(18, 75, n)
    inkomen = rng.normal(3200, 900, n).clip(800, 10000)
    spaardoel = rng.normal(3000, 2500, n).clip(0, 20000)
    horizon = rng.integers(3, 60, n)
    risico = rng.integers(0, 3, n)   # 0 laag, 1 middel, 2 hoog
    ervaring = rng.integers(0, 2, n) # 0/1
    buffer = rng.integers(0, 18, n)

    # Latente logit: combinatie van factoren
    z = (
        0.60*(risico/2) +
        -0.30*(buffer/18) +
        -0.20*(horizon/60) +
        -0.25*((inkomen-3200)/2000) +
        0.15*((spaardoel-3000)/5000) +
        -0.10*((leeftijd-40)/20) +
        -0.08*(ervaring)
    )

    if noise > 0:
        z = z + rng.normal(0, noise, n)

    z = z + skew  # schuif de balans

    p = 1/(1+np.exp(-z))
    y = (rng.random(n) < p).astype(int)

    df = pd.DataFrame({
        "leeftijd": leeftijd,
        "inkomen": np.round(inkomen, 2),
        "spaardoel": np.round(spaardoel, 2),
        "horizon_maanden": horizon,
        "risico_houding": risico,
        "ervaring": ervaring,
        "buffer_maanden": buffer,
        "y_risico": y
    })
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=100_000, help="Aantal rijen (default 100k)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skew", type=float, default=0.0, help="Logit shift: >0 meer 1'jes, <0 meer 0'en")
    ap.add_argument("--noise", type=float, default=0.0, help="Gauss-ruis op logit (typisch 0..0.5)")
    args = ap.parse_args()

    df = generate_synthetic(n=args.rows, seed=args.seed, skew=args.skew, noise=args.noise)
    df.to_csv(OUT_CSV, index=False, compression="gzip")

    meta = {
        "rows": int(args.rows),
        "seed": int(args.seed),
        "skew": float(args.skew),
        "noise": float(args.noise),
        "path": OUT_CSV
    }
    with open(OUT_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # Kleine samenvatting
    frac_1 = float(df["y_risico"].mean())
    print(f"✅ Dataset opgeslagen: {OUT_CSV}  |  rows={len(df)}  |  y_risico mean={frac_1:.3f}")
    print(f"ℹ️  Meta: {OUT_META}")

if __name__ == "__main__":
    main()
