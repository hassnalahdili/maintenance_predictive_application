import json
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
import joblib

from app.ml.diagnostics import (
    compute_probability_metrics,
    build_calibration_bins,
    extract_feature_importance,
    save_model_metadata,
)

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
BASELINE_PATH = ARTIFACT_DIR / "training_baseline.json"

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


def build_dataset(n: int = 3000) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    for _ in range(n):
        temperature = rng.normal(75, 8)
        pressure = rng.normal(6.8, 0.8)
        rpm = rng.normal(1480, 80)
        current = rng.normal(50, 6)
        total_vibration = abs(rng.normal(8, 3))

        rule_count = 0
        severity_score = 0
        max_rule_confidence = 0.0

        if temperature > 85:
            rule_count += 1
            severity_score += 3
            max_rule_confidence = max(max_rule_confidence, 0.85)
        if total_vibration > 12:
            rule_count += 1
            severity_score += 3
            max_rule_confidence = max(max_rule_confidence, 0.9)
        if pressure > 7.5:
            rule_count += 1
            severity_score += 2
            max_rule_confidence = max(max_rule_confidence, 0.8)
        if rpm < 1400:
            rule_count += 1
            severity_score += 2
            max_rule_confidence = max(max_rule_confidence, 0.75)

        temperature_margin_85 = temperature - 85
        pressure_margin_7 = pressure - 7
        rpm_drop_margin = 1450 - rpm

        risk_score = (
            0.25 * max(temperature_margin_85, 0)
            + 0.18 * max(total_vibration - 10, 0)
            + 0.12 * max(pressure_margin_7, 0)
            + 0.08 * max(rpm_drop_margin, 0)
            + 0.3 * rule_count
        )
        failure = 1 if risk_score > 1.5 else 0

        rows.append({
            "temperature": temperature,
            "pressure": pressure,
            "rpm": rpm,
            "current": current,
            "total_vibration": total_vibration,
            "rule_count": rule_count,
            "max_rule_confidence": max_rule_confidence,
            "severity_score": severity_score,
            "temperature_margin_85": temperature_margin_85,
            "pressure_margin_7": pressure_margin_7,
            "rpm_drop_margin": rpm_drop_margin,
            "failure": failure,
        })

    return pd.DataFrame(rows)


def main():
    df = build_dataset()
    X = df[FEATURE_ORDER]
    y = df["failure"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    base_model = RandomForestClassifier(n_estimators=250, random_state=42, class_weight="balanced", n_jobs=1)
    base_model.fit(X_train_scaled, y_train)
    uncalibrated_probabilities = base_model.predict_proba(X_test_scaled)[:, 1]

    calibrated_model = CalibratedClassifierCV(
        estimator=clone(base_model),
        method="sigmoid",
        cv=3,
    )
    calibrated_model.fit(X_train_scaled, y_train)
    calibrated_probabilities = calibrated_model.predict_proba(X_test_scaled)[:, 1]
    preds = calibrated_model.predict(X_test_scaled)

    print(classification_report(y_test, preds))

    calibration_before = compute_probability_metrics(y_test, uncalibrated_probabilities)
    calibration_after = compute_probability_metrics(y_test, calibrated_probabilities)
    feature_importance = extract_feature_importance(base_model, FEATURE_ORDER, X_test_scaled, y_test)
    BASELINE_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.utcnow().isoformat(),
                "sample_size": len(X_train),
                "feature_means": {feature: round(float(X_train[feature].mean()), 6) for feature in FEATURE_ORDER},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    save_model_metadata(
        model_name="RandomForest + CalibratedClassifierCV",
        feature_names=FEATURE_ORDER,
        feature_means={feature: float(X_train[feature].mean()) for feature in FEATURE_ORDER},
        feature_stds={feature: float(X_train[feature].std()) or 1.0 for feature in FEATURE_ORDER},
        calibration_method="sigmoid_cv3",
        calibration_before=calibration_before,
        calibration_after=calibration_after,
        calibration_bins=build_calibration_bins(y_test, calibrated_probabilities),
        global_importance=feature_importance,
    )

    joblib.dump(calibrated_model, ARTIFACT_DIR / "maintenance_model.joblib")
    joblib.dump(scaler, ARTIFACT_DIR / "maintenance_scaler.joblib")
    print("Artifacts saved in", ARTIFACT_DIR)


if __name__ == "__main__":
    main()
