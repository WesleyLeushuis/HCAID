# ml/model_runtime.py
import os, json
import pandas as pd
from joblib import load

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "..", "data")

def load_model_or_none():
    model_path = os.path.join(DATA_DIR, "model.joblib")
    cols_path  = os.path.join(DATA_DIR, "columns.json")
    if not (os.path.exists(model_path) and os.path.exists(cols_path)):
        return None, None
    try:
        model = load(model_path)
        with open(cols_path, "r", encoding="utf-8") as f:
            cols_obj = json.load(f)
        cols = cols_obj.get("columns") or cols_obj.get("feature_names") or []
        if not isinstance(cols, list) or len(cols) == 0:
            return None, None
        return model, cols
    except Exception:
        return None, None

# Zorg dat ALLE verwachte kolommen aanwezig zijn en op de goede VOLGORDE staan
def row_from_inputs(inputs: dict, model_cols: list[str]) -> pd.DataFrame:
    row = {}
    for c in model_cols:
        v = inputs.get(c, 0)
        # normaliseer booleans
        if isinstance(v, str):
            vl = v.strip().lower()
            if vl in ("true","on","1","yes"): v = 1
            elif vl == "": v = 0
        row[c] = v
    return pd.DataFrame([row], columns=model_cols)

def predict_proba(model, Xdf: pd.DataFrame) -> float:
    # model is Pipeline met scaler + HGB + calibratie → direct proba
    proba = model.predict_proba(Xdf)[:, 1]
    return float(proba[0])
