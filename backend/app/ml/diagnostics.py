from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.inspection import permutation_importance
from sklearn.metrics import brier_score_loss, f1_score, precision_score, recall_score, roc_auc_score


MODEL_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_METADATA_PATH = MODEL_DIR / "maintenance_model_metadata.json"


def expected_calibration_error(y_true, probabilities, bins: int = 10) -> float:
    y_array = np.asarray(y_true, dtype=float)
    prob_array = np.asarray(probabilities, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(prob_array)
    if total == 0:
        return 0.0

    ece = 0.0
    for index in range(bins):
        lower = edges[index]
        upper = edges[index + 1]
        if index == bins - 1:
            mask = (prob_array >= lower) & (prob_array <= upper)
        else:
            mask = (prob_array >= lower) & (prob_array < upper)
        if not np.any(mask):
            continue
        avg_confidence = float(prob_array[mask].mean())
        avg_accuracy = float(y_array[mask].mean())
        ece += abs(avg_accuracy - avg_confidence) * (np.count_nonzero(mask) / total)
    return float(ece)


def build_calibration_bins(y_true, probabilities, bins: int = 10) -> list[dict]:
    y_array = np.asarray(y_true, dtype=float)
    prob_array = np.asarray(probabilities, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows: list[dict] = []
    for index in range(bins):
        lower = edges[index]
        upper = edges[index + 1]
        if index == bins - 1:
            mask = (prob_array >= lower) & (prob_array <= upper)
        else:
            mask = (prob_array >= lower) & (prob_array < upper)
        count = int(np.count_nonzero(mask))
        if count == 0:
            rows.append(
                {
                    "bin_label": f"{lower:.1f}-{upper:.1f}",
                    "count": 0,
                    "average_confidence": 0.0,
                    "observed_frequency": 0.0,
                }
            )
            continue
        rows.append(
            {
                "bin_label": f"{lower:.1f}-{upper:.1f}",
                "count": count,
                "average_confidence": round(float(prob_array[mask].mean()), 4),
                "observed_frequency": round(float(y_array[mask].mean()), 4),
            }
        )
    return rows


def compute_probability_metrics(y_true, probabilities, *, threshold: float = 0.5) -> dict[str, float]:
    y_array = np.asarray(y_true, dtype=int)
    prob_array = np.asarray(probabilities, dtype=float)
    predictions = (prob_array >= threshold).astype(int)
    roc_auc = 0.5
    if len(np.unique(y_array)) > 1:
        roc_auc = float(roc_auc_score(y_array, prob_array))
    return {
        "precision": round(float(precision_score(y_array, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_array, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(y_array, predictions, zero_division=0)), 4),
        "roc_auc": round(roc_auc, 4),
        "brier": round(float(brier_score_loss(y_array, prob_array)), 4),
        "ece": round(float(expected_calibration_error(y_array, prob_array)), 4),
    }


def extract_feature_importance(model, feature_names: list[str], X_eval, y_eval) -> list[dict]:
    scores = None
    if hasattr(model, "feature_importances_"):
        scores = np.asarray(model.feature_importances_, dtype=float)
    elif hasattr(model, "coef_"):
        coefficients = np.asarray(model.coef_, dtype=float)
        if coefficients.ndim == 2:
            coefficients = coefficients[0]
        scores = np.abs(coefficients)

    if scores is None:
        importance = permutation_importance(
            model,
            X_eval,
            y_eval,
            scoring="roc_auc",
            n_repeats=8,
            random_state=42,
        )
        scores = np.asarray(importance.importances_mean, dtype=float)

    scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)
    total = float(np.abs(scores).sum()) or 1.0
    rows = [
        {
            "feature": feature_name,
            "importance": round(float(score), 6),
            "normalized_importance": round(float(abs(score) / total), 4),
        }
        for feature_name, score in zip(feature_names, scores)
    ]
    rows.sort(key=lambda item: item["normalized_importance"], reverse=True)
    return rows


def save_model_metadata(
    *,
    model_name: str,
    feature_names: list[str],
    feature_means: dict[str, float],
    feature_stds: dict[str, float],
    calibration_method: str,
    calibration_before: dict[str, float],
    calibration_after: dict[str, float],
    calibration_bins: list[dict],
    global_importance: list[dict],
) -> dict:
    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "model_name": model_name,
        "feature_names": feature_names,
        "feature_means": {feature: round(float(value), 6) for feature, value in feature_means.items()},
        "feature_stds": {feature: round(float(value), 6) for feature, value in feature_stds.items()},
        "calibration_method": calibration_method,
        "calibration_before": calibration_before,
        "calibration_after": calibration_after,
        "calibration_bins": calibration_bins,
        "global_importance": global_importance,
    }
    MODEL_METADATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_model_metadata() -> dict:
    if not MODEL_METADATA_PATH.exists():
        return {}
    return json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))
