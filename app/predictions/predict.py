from __future__ import annotations

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import numpy as np
import threading

from . import models as mla  # your module
from __future__ import annotations
import os, json, pickle
import joblib

# Where artifacts live by default
# Directory where model artifacts (trained model, threshold, feature order) are stored
_ART_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

# Path to the trained model file (can be overridden by PHISH_MODEL_PATH environment variable)
_MODEL_PATH = os.getenv("PHISH_MODEL_PATH", os.path.join(_ART_DIR, "phish_rf.joblib"))

# Path to the threshold file (can be overridden by PHISH_THRESHOLD_PATH environment variable)
_THRESHOLD_PATH = os.getenv("PHISH_THRESHOLD_PATH", os.path.join(_ART_DIR, "threshold.json"))

# Path to the feature order file (can be overridden by PHISH_FEATURE_ORDER_PATH environment variable)
_FEATURE_ORDER_PATH = os.getenv("PHISH_FEATURE_ORDER_PATH", os.path.join(_ART_DIR, "feature_order.json"))

def _load_artifact(path: str):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".joblib", ".jl"):
        return joblib.load(path)
    # default to pickle (.pkl / .pickle)
    with open(path, "rb") as f:
        return pickle.load(f)

def load_model():
    """Return a fitted sklearn estimator or a dict bundle with 'model' and (optionally) 'feature_order'."""
    # SECURITY: only load from trusted paths!
    return _load_artifact(_MODEL_PATH)

def load_feature_order():
    """Return list[str] feature names in serving order, or None if bundled in the model."""
    try:
        if os.path.exists(_FEATURE_ORDER_PATH):
            with open(_FEATURE_ORDER_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and all(isinstance(x, str) for x in data):
                return data
    except Exception:
        pass
    return None

def get_threshold(default: float = 0.5) -> float:
    """Return F1-opt threshold if available; default 0.5 (env PHISH_THRESHOLD overrides)."""
    # JSON file (preferred)
    try:
        if os.path.exists(_THRESHOLD_PATH):
            with open(_THRESHOLD_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            t = float(data.get("f1_opt", default))
            if 0.0 <= t <= 1.0:
                return t
    except Exception:
        pass
    # ENV override
    try:
        t_env = float(os.getenv("PHISH_THRESHOLD", default))
        if 0.0 <= t_env <= 1.0:
            return t_env
    except Exception:
        pass
    return default


# -------------------------------------------------
# Flask setup
# -------------------------------------------------
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# -------------------------------------------------
# Global, lazy-loaded artifacts (no training here)
# -------------------------------------------------
# Global variables for lazy-loaded model artifacts
_model = None                # The trained model instance (loaded once)
_feature_order = None        # List of feature names in model order
_pos_idx = 1                 # Default positive class index; will be inferred from model
_label_map = {0: "legit", 1: "phish"}  # Maps model output to labels; adjust if using string labels
_lock = threading.Lock()     # Thread lock for safe lazy loading

def _try_getattr(obj, names):
    """
    Return the first existing attribute from a list of possible names, or None if not found.
    Used to flexibly access loader functions or properties in the MLA module.
    """
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return None

def _load_feature_order():
    """
    Try several conventional functions in your mla module to load feature order.
    Adjust the candidate names if your module differs.

    Returns:
        list[str] | None: The feature order as a list of strings, or None if not found.
    """
    # Try to get a loader function or property from the MLA module
    loader = _try_getattr(mla, [
        "load_feature_order",          # Preferred: explicit loader
        "get_feature_order",           # Alternative: getter
        "feature_order",               # Alternative: direct property
    ])
    if callable(loader):
        fo = loader()
        # Ensure the returned value is a list/tuple of strings
        if isinstance(fo, (list, tuple)) and all(isinstance(x, str) for x in fo):
            return list(fo)
    # Fallback: if your model bundle carries the order, leave None here; we’ll infer later.
    return None

def _load_model_bundle():
    """
    Loads the trained model and feature order from the Core_Machine_Learning_Algorithm module.
    Tries several conventional loader function names. Returns:
        (model, feature_order, pos_label)
    """
    # Try common loader names in Core_Machine_Learning_Algorithm
    load_fn = _try_getattr(mla, [
        "load_model",                  # ideal: returns fitted model (and maybe metadata)
        "load_rf",                     # if you saved a specific RF
        "restore_model",               # alternative loader name
        "get_trained_model",           # another possible loader name
    ])

    if callable(load_fn):
        bundle = load_fn()
        # Accept either raw estimator or dict bundle
        if isinstance(bundle, dict):
            # If loader returns a dict, extract model, feature order, and positive label
            model = bundle.get("model", None)
            fo = bundle.get("feature_order", None) or _load_feature_order()
            pos_label = bundle.get("pos_label", 1)
            return model, fo, pos_label
        else:
            # If loader returns just the model, infer feature order and use default pos_label
            return bundle, _load_feature_order(), 1

    # LAST RESORT: fallback to training if no loader is found
    # Only use this if train_rf() returns a fitted model without retraining
    train_fn = _try_getattr(mla, ["train_rf"])
    if callable(train_fn):
        logging.warning("No explicit load_model() found; using train_rf() as a fallback loader.")
        model = train_fn()
        return model, _load_feature_order(), 1

    # If no loader or trainer is found, raise an error
    raise RuntimeError("No model loader found in Core_Machine_Learning_Algorithm.")

def _infer_positive_index(model):
    """
    Determine which column of predict_proba corresponds to the phishing class.
    We assume '1' => phish as a convention; if your classes_ are strings, we look for 'phish'.
    Otherwise we fall back to the last column.
    """
    pos_idx = 1  # Default to index 1 (second column)
    classes = getattr(model, "classes_", None)  # Try to get model's class labels

    if classes is None:
        # If model does not have classes_, return default
        return pos_idx

    # numpy array or list
    try:
        if 1 in classes:
            # Standard case: classes are [0, 1], with 1 = phishing
            pos_idx = int(np.where(classes == 1)[0][0])
        elif "phish" in classes:
            # If classes are string labels, look for "phish"
            pos_idx = int(np.where(classes == "phish")[0][0])
        else:
            # Fallback: use last column
            pos_idx = len(classes) - 1
    except Exception:
        # If any error, fallback to index 1 if possible, else 0
        pos_idx = 1 if len(classes) > 1 else 0

    return pos_idx

def _label_from_score(score: float, threshold: float) -> str:
    """
    Returns the label ("phish" or "legit") based on the score and threshold.

    Args:
        score (float): The predicted probability for the positive class.
        threshold (float): The decision threshold.

    Returns:
        str: "phish" if score >= threshold, else "legit".
    """
    return "phish" if score >= threshold else "legit"

def _threshold():
    """
    Optional: pull an F1-optimal threshold from your module or env var.
    Defaults to 0.5 if not set.
    """
    # Try to get threshold from the MLA module (e.g., get_threshold or load_threshold)
    get_thr = _try_getattr(mla, ["get_threshold", "load_threshold"])
    if callable(get_thr):
        try:
            t = float(get_thr())
            if 0.0 <= t <= 1.0:
                return t  # Use threshold from MLA module if valid
        except Exception:
            pass  # Ignore errors and continue

    # Try to get threshold from environment variable PHISH_THRESHOLD
    t_env = os.getenv("PHISH_THRESHOLD", "")
    try:
        t = float(t_env)
        if 0.0 <= t <= 1.0:
            return t  # Use threshold from environment if valid
    except Exception:
        pass  # Ignore errors and continue

    # Default threshold if none found
    return 0.5

def _ensure_loaded():
    """
    Lazy-load model, feature order, and positive class index once, thread-safe.

    Ensures that the model and its metadata are loaded only once, even if multiple
    threads access the API simultaneously. Uses a thread lock for safety.
    """
    global _model, _feature_order, _pos_idx
    if _model is not None:
        # Already loaded, nothing to do
        return
    with _lock:
        if _model is not None:
            # Double-checked locking: another thread may have loaded it
            return
        # Load model, feature order, and positive label index from the MLA module
        model, fo, pos_label = _load_model_bundle()
        if model is None:
            # If loading failed, raise an error
            raise RuntimeError("Model failed to load.")
        _model = model
        _feature_order = fo
        # If pos_label is None, infer positive index from model; otherwise, use pos_label
        _pos_idx = _infer_positive_index(_model) if pos_label is None else _infer_positive_index(_model)

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def _vector_from_payload(features, feature_order):
    """
    Converts input features (dict or list) into a 2D numpy array for model prediction.

    Args:
        features (dict or list): Feature values, either as a dict {name: value} or a list [v1, v2, ...].
        feature_order (list[str]): List of feature names in model order (required for dict input).

    Returns:
        np.ndarray: Array of shape (1, n_features) suitable for model input.

    Raises:
        ValueError: If feature order is unknown for dict input, or list length mismatches feature order.
        TypeError: If features is not a dict or list.
    """
    if isinstance(features, dict):
        # Map dict values to model order; missing keys default to 0
        if not feature_order:
            raise ValueError("Feature order is unknown; cannot map dict to vector.")
        vec = [features.get(k, 0) for k in feature_order]
        return np.asarray(vec, dtype=float).reshape(1, -1)

    if isinstance(features, list):
        # If feature order is known, check length matches
        if feature_order and len(features) != len(feature_order):
            raise ValueError(f"Expected {len(feature_order)} features, got {len(features)}.")
        return np.asarray(features, dtype=float).reshape(1, -1)

    # Invalid input type
    raise TypeError("'features' must be a list or a dict of name->value.")

# -------------------------------------------------
# Routes
# -------------------------------------------------
# -------------------------------------------------
# Health check endpoint
# -------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    """
    GET /health

    Returns basic health and model status info.
    Checks if the model is loaded and returns metadata.

    Response:
    {
        "ok": True,
        "model_loaded": True,
        "n_features_in": <number of input features>,
        "classes": <model class labels>,
        "feature_order_known": True|False
    }
    """
    try:
        _ensure_loaded()  # Make sure model is loaded
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

# -------------------------------------------------
# Feature order endpoint
# -------------------------------------------------
@app.route("/feature_order", methods=["GET"])
def feature_order_endpoint():
    """
    GET /feature_order

    Returns the feature order used by the model.

    Response:
    {
        "ok": True,
        "feature_order": [list of feature names],
        "count": <number of features>
    }
    """
    try:
        _ensure_loaded()  # Make sure model is loaded
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
    POST /predict

    Request Body:
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
        _ensure_loaded()  # Ensure model and metadata are loaded

        # Parse JSON body from request
        data = request.get_json(force=True, silent=False)
        if not data or "features" not in data:
            # Missing features in request
            return jsonify({"ok": False, "error": "Missing 'features' in JSON body."}), 400

        # Convert input features to numpy array in model order
        X = _vector_from_payload(data["features"], _feature_order)
        if not hasattr(_model, "predict_proba"):
            # Model does not support probability prediction
            return jsonify({"ok": False, "error": "Model has no predict_proba()."}), 500

        # Get probability predictions from model
        proba = _model.predict_proba(X)
        if proba.shape[1] == 1:
            # Some models output a single probability column
            score = float(proba[0, 0])
        else:
            # Use the positive class index for phishing probability
            score = float(proba[0, _pos_idx])

        thr = _threshold()  # Get decision threshold
        label = _label_from_score(score, thr)  # Map score to label

        logging.info(f"Predicted label={label}, score={score:.4f}")
        # Return prediction result
        return jsonify({
            "ok": True,
            "label": label,
            "score": round(score, 6),
            "threshold": thr,
            "positive_class_index": _pos_idx,
            "features_checked": int(X.shape[1]),
        }), 200

    except Exception as e:
        # Log and return error details
        logging.exception("Prediction error")
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    # Never enable debug=True in production
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
