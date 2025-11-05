# ml/model.py
import os, json, joblib
import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MODEL_PATH = os.path.join(DATA_DIR, "model.joblib")
COLS_PATH = os.path.join(DATA_DIR, "columns.json")

def load_model():
    if not os.path.exists(MODEL_PATH):
        raise RuntimeError("Modelbestand ontbreekt. Voer eerst: python ml/train.py")
    return joblib.load(MODEL_PATH)

def _load_columns():
    with open(COLS_PATH, "r") as f:
        cols = json.load(f)
    return cols["numeric"], cols["categorical"]

def _align_columns(df: pd.DataFrame, num_cols, cat_cols):
    # Voeg missende kolommen toe
    for c in num_cols:
        if c not in df.columns:
            df[c] = 0.0
    for c in cat_cols:
        if c not in df.columns:
            df[c] = ""
    # Hou alleen bekende kolommen in juiste volgorde
    return df[num_cols + cat_cols].copy()

def predict_with_explain(model, X: pd.DataFrame):
    num_cols, cat_cols = _load_columns()
    X2 = _align_columns(X.copy(), num_cols, cat_cols)

    proba = float(model.predict_proba(X2)[:, 1][0])
    pred = int(proba >= 0.5)

    # Snelle, lichte pseudo-uitleg:
    # Schat top-variabele numerieke kolommen via z-score (hoe “extreem” tov trainings-mean=0 na RobustScaler)
    # NB: Omdat we scaler in pipeline hebben, kunnen we input approx z-scored inschatten door een ad-hoc schaal:
    # Hier simpelweg absolute waarde vs robust schaal (fallback = 1.0). Dit is indicatief.
    contrib = []
    row = X2.iloc[0]
    for c in num_cols:
        val = row[c]
        # ruwe “impact score” ~ |val| geschaald
        score = float(abs(val))  # we hebben geen directe scaler stats; indicatief
        contrib.append({"feature": c, "value": float(val), "contribution": score})

    # sorteer top 8
    contrib = sorted(contrib, key=lambda d: d["contribution"], reverse=True)[:8]
    return proba, pred, contrib
