# ml/train.py
import os, json, joblib, warnings
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, RobustScaler
from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_hist_gradient_boosting  # noqa: F401
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, RandomizedSearchCV
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, precision_recall_fscore_support

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
IN_CSV = os.path.join(DATA_DIR, "synth_train.csv")
MODEL_OUT = os.path.join(DATA_DIR, "model.joblib")
COLS_OUT = os.path.join(DATA_DIR, "columns.json")

warnings.filterwarnings("ignore", category=UserWarning)

# ——— Feature selectie ———
# Gebruik veilige kolommen (core + extended). Géén gevoelige velden uit “slechte” kant.
SAFE_NUMERIC = [
    "leeftijd","inkomen","spaardoel","horizon_maanden","risico_houding","ervaring","buffer_maanden",
    "vaste_lasten","pensioen_inleg","belasting_schatting","schuld_bedrag","schuld_rente",
    "hypotheek_rente","kosten_sensitiviteit","duurzaam_voorkeur"
]
SAFE_CATEG = []  # als je later categoricals wil toevoegen, zet ze hier (met str type)

TARGET = "label"

def load_data(path=IN_CSV):
    df = pd.read_csv(path)
    # Zorg dat categoricals ook echt str zijn
    for c in SAFE_CATEG:
        if c in df.columns:
            df[c] = df[c].astype(str)
    return df

def make_pipeline(num_cols, cat_cols):
    pre = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("scaler", RobustScaler(with_centering=True))]), num_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols),
        ],
        remainder="drop",
        verbose_feature_names_out=False
    )

    base = HistGradientBoostingClassifier(
        loss="log_loss",
        learning_rate=0.08,
        max_depth=None,
        max_iter=300,
        l2_regularization=0.0,
        early_stopping=True,
        random_state=17
    )

    pipe = Pipeline([
        ("pre", pre),
        ("clf", base)
    ])
    return pipe

def fit_model():
    df = load_data()
    X = df[SAFE_NUMERIC + SAFE_CATEG].copy()
    y = df[TARGET].astype(int).values

    # Sample weights: balanceer klassen
    pos_rate = y.mean()
    w_pos = 0.5 / (pos_rate + 1e-9)
    w_neg = 0.5 / (1 - pos_rate + 1e-9)
    sample_weight = np.where(y == 1, w_pos, w_neg)

    pipe = make_pipeline(SAFE_NUMERIC, SAFE_CATEG)

    # Hyperparam-zoekruimte (compact maar effectief)
    param_dist = {
        "clf__learning_rate": [0.03, 0.05, 0.08, 0.12],
        "clf__max_leaf_nodes": [15, 31, 63, 127],
        "clf__min_samples_leaf": [20, 50, 100, 200],
        "clf__l2_regularization": [0.0, 0.0005, 0.001, 0.005],
        "clf__max_bins": [255],
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=13)

    search = RandomizedSearchCV(
        pipe,
        param_distributions=param_dist,
        n_iter=20,
        scoring="average_precision",
        n_jobs=-1,
        cv=cv,
        verbose=1,
        refit=True,
        random_state=29
    )
    search.fit(X, y, clf__sample_weight=sample_weight)

    best_pipe = search.best_estimator_

    # Calibratie met sigmoid (platt scaling), 3-fold op train
    calib = CalibratedClassifierCV(best_pipe, method="sigmoid", cv=3)
    calib.fit(X, y, sample_weight=sample_weight)

    # Evaluatie (out-of-sample benadering via CV van calibrator is beperkt; quick global check op train)
    prob = calib.predict_proba(X)[:, 1]
    pred = (prob >= 0.5).astype(int)
    roc = roc_auc_score(y, prob)
    ap = average_precision_score(y, prob)
    p, r, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)

    print(f"[Best params] {search.best_params_}")
    print(f"[Train-ish eval] ROC-AUC={roc:.3f} | AP={ap:.3f} | F1={f1:.3f} (P={p:.3f}, R={r:.3f})")

    # Bewaar model + kolommen
    joblib.dump(calib, MODEL_OUT)
    with open(COLS_OUT, "w") as f:
        json.dump({
            "numeric": SAFE_NUMERIC,
            "categorical": SAFE_CATEG,
            "target": TARGET
        }, f, indent=2)

    print(f"[OK] Model -> {MODEL_OUT}")
    print(f"[OK] Columns -> {COLS_OUT}")

if __name__ == "__main__":
    fit_model()
