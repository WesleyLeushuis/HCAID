# ml/train.py
import os, json, warnings, math
import numpy as np
import pandas as pd
from joblib import dump
from sklearn.model_selection import RandomizedSearchCV, RepeatedStratifiedKFold
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score
from sklearn.utils import check_random_state

warnings.filterwarnings("ignore", category=UserWarning)

# ===========================
# ✦ ROBUSTNESS CONTROLS ✦
# Pas gerust aan je machine aan
# ===========================
CV_FOLDS   = 10        # meer folds → robuuster (8–10 is prima)
CV_REPEATS = 2         # herhaal CV voor stabiliteit (1–3)
N_ITER     = 60        # meer kandidaten in RandomizedSearch (20–200)
N_JOBS     = -1        # -1 = alle cores; zet op 1 als je macOS-multiprocessing-meldingen wilt vermijden
RANDOM_SEED = 17       # vast zaad voor reproduceerbaarheid
VERBOSE_SEARCH = 1

# Optioneel: zet op True om joblib 'threading' te forceren (soms stiller op macOS)
USE_THREADING_BACKEND = False

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "..", "data")
MODEL_OUT = os.path.join(DATA_DIR, "model.joblib")
COLS_OUT  = os.path.join(DATA_DIR, "columns.json")

train_csv = os.path.join(DATA_DIR, "synth_train.csv")
valid_csv = os.path.join(DATA_DIR, "synth_valid.csv")
assert os.path.exists(train_csv), "Run eerst: python ml/gen_data.py"

train = pd.read_csv(train_csv)
if os.path.exists(valid_csv):
    valid = pd.read_csv(valid_csv)
else:
    # fallback: simpele split (mocht valid er niet zijn)
    valid = train.sample(frac=0.15, random_state=RANDOM_SEED)
    train = train.drop(valid.index)

y_train = train["label"].astype(int).values
y_valid = valid["label"].astype(int).values

features = [c for c in train.columns if c != "label"]
X_train = train[features].copy()
X_valid = valid[features].copy()

# ====== Preprocessing: alle features numeriek, licht schalen ======
pre = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(with_mean=True, with_std=True), features)
    ],
    remainder="drop"
)

# ====== Basismodel ======
base = HistGradientBoostingClassifier(
    max_depth=None,
    learning_rate=0.05,
    max_bins=255,
    l2_regularization=0.0,
    early_stopping=True,
    validation_fraction=0.1,   # gebruikt tijdens fit voor internal early_stopping
    random_state=RANDOM_SEED
)

pipe = Pipeline([
    ("pre", pre),
    ("clf", base)
])

# ====== Hyperparam-ruimte (bewust breed) ======
# Let op: max_leaf_nodes mag geen None zijn bij HGB
param_space = {
    "clf__learning_rate":  [0.02, 0.03, 0.05, 0.08, 0.10],
    "clf__max_leaf_nodes": [31, 63, 127, 255],
    "clf__min_samples_leaf": [20, 50, 100, 200, 400],
    "clf__l2_regularization": [0.0, 1e-4, 1e-3, 1e-2],
    "clf__max_bins": [63, 127, 255]
}

# ====== RepeatedStratifiedKFold voor stabielere schattingen ======
cv = RepeatedStratifiedKFold(
    n_splits=CV_FOLDS,
    n_repeats=CV_REPEATS,
    random_state=RANDOM_SEED
)

search = RandomizedSearchCV(
    estimator=pipe,
    param_distributions=param_space,
    n_iter=N_ITER,
    cv=cv,
    scoring="roc_auc",
    n_jobs=N_JOBS,
    verbose=VERBOSE_SEARCH,
    random_state=RANDOM_SEED,
    refit=True,
)

def run_search():
    if USE_THREADING_BACKEND:
        from joblib import parallel_backend
        with parallel_backend("threading"):
            search.fit(X_train, y_train)
    else:
        search.fit(X_train, y_train)

# ====== Train ======
run_search()
best = search.best_estimator_
print("\n[Best params]", search.best_params_)
print(f"[CV best score] AUC={search.best_score_:.4f} (RepeatedStratifiedKFold {CV_FOLDS}x{CV_REPEATS}; n_iter={N_ITER})")

# ====== Calibratie voor betrouwbare predict_proba ======
calib = CalibratedClassifierCV(best, method="isotonic", cv=3)
calib.fit(X_train, y_train)

# ====== Evaluatie ======
p_tr = calib.predict_proba(X_train)[:, 1]
p_va = calib.predict_proba(X_valid)[:, 1]

print(f"[Train] AUC={roc_auc_score(y_train,p_tr):.3f} | AP={average_precision_score(y_train,p_tr):.3f} | F1={f1_score(y_train,(p_tr>0.5).astype(int)):.3f}")
print(f"[Valid] AUC={roc_auc_score(y_valid,p_va):.3f} | AP={average_precision_score(y_valid,p_va):.3f} | F1={f1_score(y_valid,(p_va>0.5).astype(int)):.3f}")

# ====== Opslaan ======
dump(calib, MODEL_OUT)
with open(COLS_OUT, "w", encoding="utf-8") as f:
    json.dump({"columns": features}, f, ensure_ascii=False, indent=2)

print(f"[OK] Model -> {MODEL_OUT}")
print(f"[OK] Columns -> {COLS_OUT}")

print("\nTip: wil je nóg robuuster?")
print("- Verhoog N_ITER (bijv. 120 of 200).")
print("- Verhoog CV_REPEATS naar 3 (kost tijd).")
print("- Voeg meer variatie in synthetische data toe (ml/gen_data.py).")
