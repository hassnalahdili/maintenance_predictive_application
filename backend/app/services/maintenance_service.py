from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Alert, BusinessRule, Machine, Prediction, SensorData
from app.schemas.common import AlertOut, PredictionOut
from app.services.live_updates import publish_event
from app.services.notifications import create_notification
from app.services.rules_engine import build_rule_features, evaluate_rules
from app.ml.model_service import predict_from_features


def serialize_prediction(prediction: Prediction) -> PredictionOut:
    return PredictionOut(
        id=prediction.id,
        machine_id=prediction.machine_id,
        machine_name=prediction.machine.name if prediction.machine else None,
        timestamp=prediction.timestamp,
        failure_probability=prediction.failure_probability,
        remaining_useful_life_days=prediction.remaining_useful_life_days,
        expected_failure_date=prediction.expected_failure_date,
        alert_level=prediction.alert_level,
        active_rules=prediction.active_rules,
        prediction_source=prediction.prediction_source,
    )


def serialize_alert(alert: Alert) -> AlertOut:
    return AlertOut(
        id=alert.id,
        machine_id=alert.machine_id,
        machine_name=alert.machine.name if alert.machine else None,
        level=alert.level,
        message=alert.message,
        probability=alert.probability,
        acknowledged=alert.acknowledged,
        acknowledgment_comment=alert.acknowledgment_comment,
        status=alert.status,
        escalated=alert.escalated,
        escalated_at=alert.escalated_at,
        created_at=alert.created_at,
    )


def escalate_pending_alerts(db: Session, *, now: datetime | None = None) -> int:
    reference = now or datetime.utcnow()
    escalated_count = 0
    deadline = reference - timedelta(hours=settings.alert_escalation_hours)
    pending_alerts = (
        db.query(Alert)
        .filter(Alert.acknowledged.is_(False), Alert.created_at <= deadline, Alert.escalated.is_(False))
        .all()
    )
    for alert in pending_alerts:
        alert.escalated = True
        alert.status = "escalated"
        alert.escalated_at = reference
        create_notification(
            db,
            title="Alerte escaladee",
            message=f"L'alerte #{alert.id} sur {alert.machine.name if alert.machine else 'machine'} n'a pas ete traitee a temps.",
            severity="critical",
            entity_type="alert",
            entity_id=alert.id,
        )
        escalated_count += 1
    return escalated_count


def _build_alert_message(machine: Machine, level: str, active_rules: list[str]) -> str:
    if active_rules:
        joined_rules = ", ".join(active_rules)
        return f"Risque {level} detecte sur {machine.name} ({joined_rules})"
    return f"Risque {level} detecte sur {machine.name}"


def process_sensor_reading(
    db: Session,
    machine: Machine,
    sensor_payload: dict,
) -> dict:
    sensor_data = {key: value for key, value in sensor_payload.items() if key != "machine_id"}
    sensor = SensorData(machine_id=machine.id, **sensor_data)
    db.add(sensor)
    db.flush()

    rules = (
        db.query(BusinessRule)
        .filter(BusinessRule.machine_type == machine.machine_type, BusinessRule.is_active.is_(True))
        .order_by(BusinessRule.id.asc())
        .all()
    )
    matched_rules = evaluate_rules(sensor, rules)
    features = build_rule_features(sensor, matched_rules)
    ml_prediction = predict_from_features(features)
    final_probability = ml_prediction["failure_probability"]
    final_level = ml_prediction["alert_level"]
    active_rules = [rule.name for rule in matched_rules]

    prediction = Prediction(
        machine_id=machine.id,
        failure_probability=final_probability,
        remaining_useful_life_days=ml_prediction["remaining_useful_life_days"],
        expected_failure_date=ml_prediction["expected_failure_date"],
        alert_level=final_level,
        active_rules=json.dumps(active_rules, ensure_ascii=False),
        prediction_source=ml_prediction["prediction_source"],
    )
    db.add(prediction)

    created_alert = None
    if final_probability >= settings.alert_probability_threshold:
        created_alert = Alert(
            machine_id=machine.id,
            level=final_level,
            message=_build_alert_message(machine, final_level, active_rules),
            probability=round(final_probability, 4),
            status="active",
        )
        db.add(created_alert)
        db.flush()
        create_notification(
            db,
            title=f"Alerte {final_level}",
            message=created_alert.message,
            severity=final_level,
            entity_type="alert",
            entity_id=created_alert.id,
        )

    machine.status = final_level if final_level != "normal" else "healthy"
    machine.updated_at = datetime.utcnow()
    db.flush()

    publish_event(
        "machine_signal_processed",
        machine_id=machine.id,
        machine_name=machine.name,
        machine_type=machine.machine_type,
        alert_level=final_level,
        failure_probability=round(final_probability, 4),
        prediction_id=prediction.id,
        alert_id=created_alert.id if created_alert else None,
    )

    return {
        "sensor": sensor,
        "prediction": prediction,
        "alert": created_alert,
        "features": features,
        "matched_rules": matched_rules,
        "final_probability": round(final_probability, 4),
    }
