from __future__ import annotations

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import numpy as np
import threading

import Core_Machine_Learning_Algorithm as mla  # your module

# -------------------------------------------------
# Flask setup
# -------------------------------------------------
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# -------------------------------------------------
# Global, lazy-loaded artifacts (no training here)
# -------------------------------------------------
_model = None
_feature_order = None
_pos_idx = 1             # default positive class index; will be inferred
_label_map = {0: "legit", 1: "phish"}  # adjust if you used strings during training
_lock = threading.Lock()

def _try_getattr(obj, names):
    """Return first existing attribute by name list, else None."""
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return None

def _load_feature_order():
    """
    Try several conventional functions in your mla module to load feature order.
    Adjust the candidate names if your module differs.
    """
    loader = _try_getattr(mla, [
        "load_feature_order",          # you mentioned this
        "get_feature_order",
        "feature_order",
    ])
    if callable(loader):
        fo = loader()
        if isinstance(fo, (list, tuple)) and all(isinstance(x, str) for x in fo):
            return list(fo)
    # Fallback: if your model bundle carries the order, leave None here; we’ll infer later.
    return None

def _load_model_bundle():
    """
    Prefer a load function that returns a fitted model (and optionally feature_order).
    Do NOT call any training function here.
    """
    # Try common loader names in Core_Machine_Learning_Algorithm
    load_fn = _try_getattr(mla, [
        "load_model",                  # ideal: returns fitted model (and maybe metadata)
        "load_rf",                     # if you saved a specific RF
        "restore_model",
        "get_trained_model",
    ])

    if callable(load_fn):
        bundle = load_fn()
        # Accept either raw estimator or dict bundle
        if isinstance(bundle, dict):
            model = bundle.get("model", None)
            fo = bundle.get("feature_order", None) or _load_feature_order()
            pos_label = bundle.get("pos_label", 1)
            return model, fo, pos_label
        else:
            return bundle, _load_feature_order(), 1

    # LAST RESORT (only if you absolutely have no saved model loader):
    # If your train_rf() *returns a fitted model* without retraining expensively, you can keep it.
    # Otherwise, comment this out to avoid training inside API.
    train_fn = _try_getattr(mla, ["train_rf"])
    if callable(train_fn):
        logging.warning("No explicit load_model() found; using train_rf() as a fallback loader.")
        model = train_fn()
        return model, _load_feature_order(), 1

    raise RuntimeError("No model loader found in Core_Machine_Learning_Algorithm.")

def _infer_positive_index(model):
    """
    Determine which column of predict_proba corresponds to the phishing class.
    We assume '1' => phish as a convention; if your classes_ are strings, we look for 'phish'.
    Otherwise we fall back to the last column.
    """
    pos_idx = 1
    classes = getattr(model, "classes_", None)
    if classes is None:
        return pos_idx

    # numpy array or list
    try:
        if 1 in classes:
            # standard case: {0,1} with 1 = phishing
            pos_idx = int(np.where(classes == 1)[0][0])
        elif "phish" in classes:
            pos_idx = int(np.where(classes == "phish")[0][0])
        else:
            pos_idx = len(classes) - 1
    except Exception:
        pos_idx = 1 if len(classes) > 1 else 0

    return pos_idx

def _label_from_score(score: float, threshold: float) -> str:
    return "phish" if score >= threshold else "legit"

def _threshold():
    """
    Optional: pull an F1-optimal threshold from your module or env var.
    Defaults to 0.5 if not set.
    """
    # Try mla accessor
    get_thr = _try_getattr(mla, ["get_threshold", "load_threshold"])
    if callable(get_thr):
        try:
            t = float(get_thr())
            if 0.0 <= t <= 1.0:
                return t
        except Exception:
            pass

    # Environment override
    t_env = os.getenv("PHISH_THRESHOLD", "")
    try:
        t = float(t_env)
        if 0.0 <= t <= 1.0:
            return t
    except Exception:
        pass

    return 0.5

def _ensure_loaded():
    """
    Lazy-load model, feature order, and positive class index once, thread-safe.
    """
    global _model, _feature_order, _pos_idx
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        model, fo, pos_label = _load_model_bundle()
        if model is None:
            raise RuntimeError("Model failed to load.")
        _model = model
        _feature_order = fo
        _pos_idx = _infer_positive_index(_model) if pos_label is None else _infer_positive_index(_model)

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def _vector_from_payload(features, feature_order):
    """
    Accepts dict (preferred) or list. Returns 2D array shape (1, n_features).
    """
    if isinstance(features, dict):
        if not feature_order:
            raise ValueError("Feature order is unknown; cannot map dict to vector.")
        vec = [features.get(k, 0) for k in feature_order]
        return np.asarray(vec, dtype=float).reshape(1, -1)

    if isinstance(features, list):
        if feature_order and len(features) != len(feature_order):
            raise ValueError(f"Expected {len(feature_order)} features, got {len(features)}.")
        return np.asarray(features, dtype=float).reshape(1, -1)

    raise TypeError("'features' must be a list or a dict of name->value.")

# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    try:
        _ensure_loaded()
        classes = getattr(_model, "classes_", None)
        return jsonify({
            "ok": True,
            "model_loaded": True,
            "n_features_in": getattr(_model, "n_features_in_", None),
            "classes": classes.tolist() if hasattr(classes, "tolist") else classes,
            "feature_order_known": _feature_order is not None,
        }), 200
    except Exception as e:
        logging.exception("Health check failed")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/feature_order", methods=["GET"])
def feature_order_endpoint():
    try:
        _ensure_loaded()
        return jsonify({
            "ok": True,
            "feature_order": _feature_order or [],
            "count": len(_feature_order) if _feature_order else 0
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/predict", methods=["POST"])
def predict():
    """
    Body:
    {
      "features": {name: value, ...}   # preferred (dict)
      # or
      "features": [v1, v2, ...]        # list in model order
    }
    Response:
    {
      "ok": true,
      "label": "phish"|"legit",
      "score": 0.8734,                 # P(phish)
      "threshold": 0.57,
      "positive_class_index": 1,
      "features_checked": 24
    }
    """
    try:
        _ensure_loaded()

        data = request.get_json(force=True, silent=False)
        if not data or "features" not in data:
            return jsonify({"ok": False, "error": "Missing 'features' in JSON body."}), 400

        X = _vector_from_payload(data["features"], _feature_order)
        if not hasattr(_model, "predict_proba"):
            return jsonify({"ok": False, "error": "Model has no predict_proba()."}), 500

        proba = _model.predict_proba(X)
        if proba.shape[1] == 1:
            # Some models output a single-column proba for the positive class
            score = float(proba[0, 0])
        else:
            score = float(proba[0, _pos_idx])

        thr = _threshold()
        label = _label_from_score(score, thr)

        logging.info(f"Predicted label={label}, score={score:.4f}")
        return jsonify({
            "ok": True,
            "label": label,
            "score": round(score, 6),
            "threshold": thr,
            "positive_class_index": _pos_idx,
            "features_checked": int(X.shape[1]),
        }), 200

    except Exception as e:
        logging.exception("Prediction error")
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    # Never enable debug=True in production
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
