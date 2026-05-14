from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.ml.diagnostics import (
    build_calibration_bins,
    compute_probability_metrics,
    extract_feature_importance,
    load_model_metadata,
    save_model_metadata,
)
from app.ml.model_service import FEATURE_ORDER, MODEL_DIR, MODEL_PATH, SCALER_PATH, clear_model_cache
from app.models.models import Alert, BusinessRule, MaintenanceIntervention, Prediction, SensorData
from app.services.rules_engine import build_rule_features, evaluate_rules


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
BASELINE_PATH = MODEL_DIR / "training_baseline.json"
RETRAIN_REPORT_PATH = REPORTS_DIR / "ml_feedback_report.json"


def _build_feature_frame(db: Session) -> pd.DataFrame:
    rules_by_type: dict[str, list[BusinessRule]] = {}
    for rule in db.query(BusinessRule).filter(BusinessRule.is_active.is_(True)).order_by(BusinessRule.id.asc()).all():
        rules_by_type.setdefault(rule.machine_type, []).append(rule)

    sensors = (
        db.query(SensorData)
        .options(joinedload(SensorData.machine))
        .order_by(SensorData.timestamp.asc())
        .all()
    )
    rows: list[dict] = []
    for sensor in sensors:
        if sensor.machine is None or sensor.machine.is_deleted:
            continue
        matched_rules = evaluate_rules(sensor, rules_by_type.get(sensor.machine.machine_type, []))
        features = build_rule_features(sensor, matched_rules)
        rows.append(
            {
                "sensor_id": sensor.id,
                "machine_id": sensor.machine_id,
                "machine_type": sensor.machine.machine_type,
                "timestamp": sensor.timestamp,
                **features,
            }
        )
    return pd.DataFrame(rows)


def _collect_feedback_labels(
    db: Session,
    features_df: pd.DataFrame,
    *,
    horizon_hours: int,
) -> pd.DataFrame:
    interventions = (
        db.query(MaintenanceIntervention)
        .filter(MaintenanceIntervention.outcome_label != "under_analysis")
        .order_by(MaintenanceIntervention.opened_at.asc())
        .all()
    )
    by_machine: dict[int, list[MaintenanceIntervention]] = {}
    for intervention in interventions:
        by_machine.setdefault(intervention.machine_id, []).append(intervention)

    now = datetime.utcnow()
    horizon = timedelta(hours=horizon_hours)
    labeled_rows: list[dict] = []

    for row in features_df.to_dict(orient="records"):
        timestamp = row["timestamp"]
        machine_interventions = by_machine.get(row["machine_id"], [])
        label = None
        label_source = None
        for intervention in machine_interventions:
            if intervention.opened_at is None or intervention.opened_at < timestamp:
                continue
            if intervention.opened_at - timestamp > horizon:
                continue
            if intervention.outcome_label == "confirmed_failure":
                label = 1
                label_source = intervention.outcome_label
                break
            if intervention.outcome_label in {"false_alarm", "preventive_maintenance", "sensor_fault"}:
                label = 0
                label_source = intervention.outcome_label
                break
        if label is None and timestamp <= now - horizon:
            label = 0
            label_source = "no_event_window"
        if label is None:
            continue
        labeled_rows.append({**row, "label": label, "label_source": label_source})

    return pd.DataFrame(labeled_rows)


def build_feedback_training_set(db: Session, *, horizon_hours: int = 72) -> pd.DataFrame:
    features_df = _build_feature_frame(db)
    if features_df.empty:
        return pd.DataFrame()
    return _collect_feedback_labels(db, features_df, horizon_hours=horizon_hours)


def generate_drift_report(db: Session) -> dict:
    feature_df = _build_feature_frame(db)
    if feature_df.empty:
        return {
            "generated_at": datetime.utcnow(),
            "sample_size": 0,
            "baseline_size": 0,
            "status": "insufficient_data",
            "metrics": [],
        }

    recent = feature_df.tail(min(len(feature_df), 200))
    if BASELINE_PATH.exists():
        baseline_payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        baseline_means = baseline_payload.get("feature_means", {})
        baseline_size = int(baseline_payload.get("sample_size", 0))
    else:
        bootstrap = feature_df.head(min(len(feature_df), 200))
        baseline_means = {feature: float(bootstrap[feature].mean()) for feature in FEATURE_ORDER}
        baseline_size = len(bootstrap)

    metrics = []
    drift_flags = 0
    for feature in FEATURE_ORDER:
        recent_mean = float(recent[feature].mean())
        baseline_mean = float(baseline_means.get(feature, recent_mean))
        delta = recent_mean - baseline_mean
        drift_ratio = abs(delta) / (abs(baseline_mean) + 1e-6)
        status = "drift" if drift_ratio >= 0.25 else "stable"
        if status == "drift":
            drift_flags += 1
        metrics.append(
            {
                "feature": feature,
                "baseline_mean": round(baseline_mean, 4),
                "recent_mean": round(recent_mean, 4),
                "delta": round(delta, 4),
                "drift_ratio": round(drift_ratio, 4),
                "status": status,
            }
        )

    overall_status = "drift_detected" if drift_flags >= 3 else "stable"
    if not BASELINE_PATH.exists():
        overall_status = "bootstrap_baseline"

    return {
        "generated_at": datetime.utcnow(),
        "sample_size": len(recent),
        "baseline_size": baseline_size,
        "status": overall_status,
        "metrics": metrics,
    }


def get_feedback_summary(db: Session) -> dict:
    interventions = db.query(MaintenanceIntervention).all()
    breakdown: dict[str, int] = {}
    for intervention in interventions:
        breakdown[intervention.outcome_label] = breakdown.get(intervention.outcome_label, 0) + 1
    latest_report = None
    if RETRAIN_REPORT_PATH.exists():
        latest_report = json.loads(RETRAIN_REPORT_PATH.read_text(encoding="utf-8"))
    return {
        "total_interventions": len(interventions),
        "labels_breakdown": breakdown,
        "latest_report": latest_report,
    }


def compute_business_metrics(db: Session, *, horizon_days: int = 7) -> dict:
    alerts = db.query(Alert).all()
    interventions = db.query(MaintenanceIntervention).all()
    labeled_interventions = [item for item in interventions if item.outcome_label != "under_analysis"]
    confirmed_failures = [item for item in labeled_interventions if item.outcome_label == "confirmed_failure"]
    false_alarms = [item for item in labeled_interventions if item.outcome_label == "false_alarm"]
    resolved_interventions = [item for item in interventions if item.status == "resolved"]
    active_alerts = [item for item in alerts if item.status == "active" and not item.acknowledged]

    lead_times: list[float] = []
    covered_failures = 0
    horizon = timedelta(days=horizon_days)
    for intervention in confirmed_failures:
        if intervention.opened_at is None:
            continue
        predictions = (
            db.query(Prediction)
            .filter(
                Prediction.machine_id == intervention.machine_id,
                Prediction.timestamp <= intervention.opened_at,
                Prediction.timestamp >= intervention.opened_at - horizon,
                Prediction.failure_probability >= settings.alert_probability_threshold,
            )
            .order_by(Prediction.timestamp.asc())
            .all()
        )
        if predictions:
            covered_failures += 1
            lead_times.append((intervention.opened_at - predictions[0].timestamp).total_seconds() / 3600)

    total_alerts = len(alerts)
    total_labeled = len(confirmed_failures) + len(false_alarms)
    resolution_durations = [
        (item.closed_at - item.opened_at).total_seconds() / 3600
        for item in resolved_interventions
        if item.closed_at is not None and item.opened_at is not None and item.closed_at >= item.opened_at
    ]
    downtime_values = [item.downtime_minutes for item in resolved_interventions if item.downtime_minutes is not None]

    return {
        "generated_at": datetime.utcnow(),
        "total_alerts": total_alerts,
        "active_alerts": len(active_alerts),
        "acknowledged_rate": round(sum(1 for item in alerts if item.acknowledged) / total_alerts, 4) if total_alerts else 0.0,
        "escalation_rate": round(sum(1 for item in alerts if item.escalated) / total_alerts, 4) if total_alerts else 0.0,
        "resolved_intervention_rate": round(len(resolved_interventions) / len(interventions), 4) if interventions else 0.0,
        "false_alert_rate": round(len(false_alarms) / total_labeled, 4) if total_labeled else 0.0,
        "confirmed_failure_rate": round(len(confirmed_failures) / total_labeled, 4) if total_labeled else 0.0,
        "mean_downtime_minutes": round(sum(downtime_values) / len(downtime_values), 2) if downtime_values else 0.0,
        "mean_resolution_hours": round(sum(resolution_durations) / len(resolution_durations), 2) if resolution_durations else 0.0,
        "mean_lead_time_hours": round(sum(lead_times) / len(lead_times), 2) if lead_times else 0.0,
        "failure_coverage_rate": round(covered_failures / len(confirmed_failures), 4) if confirmed_failures else 0.0,
    }


def get_model_diagnostics(db: Session) -> dict:
    metadata = load_model_metadata()
    return {
        "generated_at": datetime.utcnow(),
        "model_name": metadata.get("model_name", "unknown"),
        "calibration_method": metadata.get("calibration_method"),
        "calibration_before": metadata.get("calibration_before", {}),
        "calibration_after": metadata.get("calibration_after", {}),
        "calibration_bins": metadata.get("calibration_bins", []),
        "global_importance": metadata.get("global_importance", []),
        "business_metrics": compute_business_metrics(db),
    }


def get_model_registry(db: Session) -> dict:
    metadata = load_model_metadata()
    latest_feedback_report = None
    if RETRAIN_REPORT_PATH.exists():
        latest_feedback_report = json.loads(RETRAIN_REPORT_PATH.read_text(encoding="utf-8"))
    current_model = {
        "name": metadata.get("model_name", "unknown"),
        "calibration_method": metadata.get("calibration_method"),
        "metrics": metadata.get("calibration_after", {}),
        "artifact_path": str(MODEL_PATH),
        "scaler_path": str(SCALER_PATH),
    }
    candidates = []
    if latest_feedback_report:
        candidates = latest_feedback_report.get("evaluated_models", [])
    return {
        "generated_at": datetime.utcnow(),
        "current_model": current_model,
        "latest_feedback_report": latest_feedback_report,
        "evaluated_models": candidates,
        "business_metrics": compute_business_metrics(db),
    }


def retrain_from_feedback(db: Session, *, horizon_hours: int = 72, minimum_samples: int = 30) -> dict:
    dataset = build_feedback_training_set(db, horizon_hours=horizon_hours)
    if dataset.empty or len(dataset) < minimum_samples:
        raise ValueError("Pas assez de donnees terrain labellisees pour lancer un retraining fiable.")
    if dataset["label"].nunique() < 2:
        raise ValueError("Le dataset terrain doit contenir au moins une classe positive et une classe negative.")

    dataset = dataset.sort_values("timestamp").reset_index(drop=True)
    split_index = max(int(len(dataset) * 0.8), 1)
    if split_index >= len(dataset):
        split_index = len(dataset) - 1

    train_df = dataset.iloc[:split_index].copy()
    test_df = dataset.iloc[split_index:].copy()
    if test_df.empty or train_df["label"].nunique() < 2 or test_df["label"].nunique() < 2:
        raise ValueError("Les donnees terrain sont encore trop faibles pour un split temporel exploitable.")

    scaler = StandardScaler()
    X_train = scaler.fit_transform(train_df[FEATURE_ORDER])
    X_test = scaler.transform(test_df[FEATURE_ORDER])
    y_train = train_df["label"].astype(int)
    y_test = test_df["label"].astype(int)

    candidates = {
        "LogisticRegression": LogisticRegression(max_iter=1200, class_weight="balanced", random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=250, random_state=42, class_weight="balanced", n_jobs=1),
        "HistGradientBoosting": HistGradientBoostingClassifier(random_state=42),
    }

    scored_models: list[tuple[str, dict, object, object, np.ndarray]] = []
    for model_name, model in candidates.items():
        base_model = clone(model)
        base_model.fit(X_train, y_train)
        if hasattr(base_model, "predict_proba"):
            uncalibrated_probabilities = base_model.predict_proba(X_test)[:, 1]
        else:
            uncalibrated_probabilities = base_model.predict(X_test)
        calibrated_model = CalibratedClassifierCV(estimator=clone(model), method="sigmoid", cv=3)
        calibrated_model.fit(X_train, y_train)
        probabilities = calibrated_model.predict_proba(X_test)[:, 1]
        metrics = compute_probability_metrics(y_test, probabilities)
        metrics["uncalibrated_brier"] = round(compute_probability_metrics(y_test, uncalibrated_probabilities)["brier"], 4)
        metrics["uncalibrated_ece"] = round(compute_probability_metrics(y_test, uncalibrated_probabilities)["ece"], 4)
        scored_models.append((model_name, metrics, calibrated_model, base_model, probabilities))

    scored_models.sort(key=lambda item: (item[1]["f1"], item[1]["recall"], item[1]["roc_auc"]), reverse=True)
    best_name, best_metrics, best_model, best_base_model, best_probabilities = scored_models[0]

    joblib.dump(best_model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    clear_model_cache()

    baseline_payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "sample_size": len(train_df),
        "feature_means": {feature: round(float(train_df[feature].mean()), 6) for feature in FEATURE_ORDER},
    }
    BASELINE_PATH.write_text(json.dumps(baseline_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    save_model_metadata(
        model_name=f"{best_name} + CalibratedClassifierCV",
        feature_names=FEATURE_ORDER,
        feature_means={feature: float(train_df[feature].mean()) for feature in FEATURE_ORDER},
        feature_stds={feature: float(train_df[feature].std()) or 1.0 for feature in FEATURE_ORDER},
        calibration_method="sigmoid_cv3",
        calibration_before={
            "brier": best_metrics["uncalibrated_brier"],
            "ece": best_metrics["uncalibrated_ece"],
        },
        calibration_after={key: value for key, value in best_metrics.items() if key not in {"uncalibrated_brier", "uncalibrated_ece"}},
        calibration_bins=build_calibration_bins(y_test, best_probabilities),
        global_importance=extract_feature_importance(best_base_model, FEATURE_ORDER, X_test, y_test),
    )

    labels_breakdown: dict[str, int] = {}
    for value in dataset["label_source"]:
        labels_breakdown[str(value)] = labels_breakdown.get(str(value), 0) + 1

    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "dataset_size": int(len(dataset)),
        "positive_labels": int(dataset["label"].sum()),
        "negative_labels": int(len(dataset) - dataset["label"].sum()),
        "best_model": best_name,
        "primary_metric": "f1",
        "metrics": best_metrics,
        "calibration_method": "sigmoid_cv3",
        "labels_breakdown": labels_breakdown,
        "report_path": str(RETRAIN_REPORT_PATH),
        "evaluated_models": [
            {
                "name": model_name,
                "metrics": metrics,
            }
            for model_name, metrics, _model, _base_model, _probabilities in scored_models
        ],
    }
    RETRAIN_REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
