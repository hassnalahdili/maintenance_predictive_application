from __future__ import annotations
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from app.ml.diagnostics import load_model_metadata
from app.services.rules_engine import risk_level

MODEL_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = MODEL_DIR / "maintenance_model.joblib"
SCALER_PATH = MODEL_DIR / "maintenance_scaler.joblib"
BASELINE_PATH = MODEL_DIR / "training_baseline.json"
FEATURE_ORDER = [
    "temperature",
    "pressure",
    "rpm",
    "current",
    "total_vibration",
    "rule_count",
    "max_rule_confidence",
    "severity_score",
    "temperature_margin_85",
    "pressure_margin_7",
    "rpm_drop_margin",
]


class ModelUnavailableError(RuntimeError):
    pass


def model_exists() -> bool:
    return MODEL_PATH.exists() and SCALER_PATH.exists()


@lru_cache(maxsize=1)
def load_model():
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    return model, scaler


def clear_model_cache() -> None:
    load_model.cache_clear()


def _load_feature_baselines() -> dict[str, float]:
    metadata = load_model_metadata()
    if metadata.get("feature_means"):
        return {feature: float(metadata["feature_means"].get(feature, 0.0)) for feature in FEATURE_ORDER}
    if BASELINE_PATH.exists():
        payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        means = payload.get("feature_means", {})
        if means:
            return {feature: float(means.get(feature, 0.0)) for feature in FEATURE_ORDER}
    return {feature: 0.0 for feature in FEATURE_ORDER}


def _predict_probability(features: dict[str, float]) -> float:
    model, scaler = load_model()
    frame = pd.DataFrame([{col: float(features.get(col, 0.0)) for col in FEATURE_ORDER}], columns=FEATURE_ORDER)
    vector = scaler.transform(frame)
    return float(model.predict_proba(vector)[0][1])


def predict_from_features(features: dict) -> dict:
    if not model_exists():
        raise ModelUnavailableError(
            "Aucun modele IA entraine n'est disponible. Lancez l'entrainement avant de demander une prediction."
        )

    probability = _predict_probability(features)
    source = "ml"

    remaining_days = max(1.0, round((1 - probability) * 14, 2))
    expected_failure = datetime.utcnow() + timedelta(days=remaining_days)
    return {
        "failure_probability": round(probability, 4),
        "remaining_useful_life_days": remaining_days,
        "expected_failure_date": expected_failure,
        "alert_level": risk_level(probability),
        "prediction_source": source,
    }


def explain_from_features(features: dict, *, top_k: int = 5) -> dict:
    if not model_exists():
        raise ModelUnavailableError(
            "Aucun modele IA entraine n'est disponible. Lancez l'entrainement avant de demander une prediction."
        )

    metadata = load_model_metadata()
    baselines = _load_feature_baselines()
    probability = _predict_probability(features)
    contributions = []
    for feature in FEATURE_ORDER:
        baseline_value = baselines.get(feature, 0.0)
        modified = {**features, feature: baseline_value}
        adjusted_probability = _predict_probability(modified)
        contribution = probability - adjusted_probability
        contributions.append(
            {
                "feature": feature,
                "value": round(float(features.get(feature, 0.0)), 4),
                "baseline": round(float(baseline_value), 4),
                "contribution": round(float(contribution), 4),
            }
        )

    ranked = sorted(contributions, key=lambda item: abs(item["contribution"]), reverse=True)
    top_positive = [item for item in ranked if item["contribution"] > 0][:top_k]
    top_negative = [item for item in ranked if item["contribution"] < 0][:top_k]

    return {
        "failure_probability": round(probability, 4),
        "alert_level": risk_level(probability),
        "top_positive": top_positive,
        "top_negative": top_negative,
        "ranked_features": ranked[:top_k],
        "global_importance": metadata.get("global_importance", [])[:top_k],
        "calibration_method": metadata.get("calibration_method"),
    }
