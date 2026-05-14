from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.domain import normalize_machine_type
from app.db.session import get_db
from app.ml.benchmark_hub import get_ml_overview
from app.models.models import BusinessRule, Machine, SensorData, User
from app.schemas.common import (
    BusinessMetricsOut,
    DriftReportOut,
    ModelDiagnosticsOut,
    PredictionExplanationOut,
    ReplaySourceOut,
    ReplayStepOut,
    ReplayStepRequest,
    RetrainReportOut,
    RetrainRequest,
)
from app.services.audit import write_audit_log
from app.services.live_updates import publish_event
from app.services.ml_ops_service import compute_business_metrics, generate_drift_report, get_feedback_summary, get_model_diagnostics, get_model_registry, retrain_from_feedback
from app.services.rules_engine import build_rule_features, evaluate_rules
from app.ml.model_service import explain_from_features, predict_from_features
from app.services.replay_service import list_replay_sources, replay_step, reset_replay_state

router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.get("/overview")
def ml_overview(
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
):
    return get_ml_overview(refresh=refresh)


@router.get("/replay/sources", response_model=list[ReplaySourceOut])
def replay_sources(
    current_user: User = Depends(get_current_user),
):
    return list_replay_sources()


@router.post("/replay/step", response_model=ReplayStepOut)
def replay_realtime_step(
    payload: ReplayStepRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "technicien", "expert")),
):
    machine = db.query(Machine).filter(Machine.id == payload.machine_id, Machine.is_deleted.is_(False)).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    try:
        result = replay_step(db, machine, source_id=payload.source_id, steps=payload.steps, reset=payload.reset)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Replay source not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    write_audit_log(
        db,
        "replay_dataset_step",
        "machine",
        user=current_user,
        entity_id=machine.id,
        request=request,
        details=f"source={payload.source_id},steps={payload.steps},rows={result['injected_rows']}",
    )
    db.commit()
    return result


@router.post("/replay/reset/{source_id}")
def replay_reset(
    source_id: str,
    current_user: User = Depends(require_roles("admin", "technicien", "expert")),
):
    reset_replay_state(source_id)
    return {"message": "Replay reset", "source_id": source_id}


@router.get("/feedback-summary")
def feedback_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_feedback_summary(db)


@router.get("/drift-report", response_model=DriftReportOut)
def drift_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return generate_drift_report(db)


@router.get("/business-metrics", response_model=BusinessMetricsOut)
def business_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return compute_business_metrics(db)


@router.get("/model-diagnostics", response_model=ModelDiagnosticsOut)
def model_diagnostics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_model_diagnostics(db)


@router.get("/model-registry")
def model_registry(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_model_registry(db)


@router.get("/explain/machines/{machine_id}", response_model=PredictionExplanationOut)
def explain_machine(
    machine_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    machine = db.query(Machine).filter(Machine.id == machine_id, Machine.is_deleted.is_(False)).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    latest_sensor = (
        db.query(SensorData)
        .filter(SensorData.machine_id == machine_id)
        .order_by(SensorData.timestamp.desc())
        .first()
    )
    if not latest_sensor:
        raise HTTPException(status_code=404, detail="No sensor history available for this machine")

    rules = (
        db.query(BusinessRule)
        .filter(BusinessRule.machine_type == normalize_machine_type(machine.machine_type), BusinessRule.is_active.is_(True))
        .order_by(BusinessRule.id.asc())
        .all()
    )
    matched_rules = evaluate_rules(latest_sensor, rules)
    features = build_rule_features(latest_sensor, matched_rules)
    prediction = predict_from_features(features)
    explanation = explain_from_features(features)
    return {
        "machine_id": machine.id,
        "machine_name": machine.name,
        "machine_type": machine.machine_type,
        "timestamp": latest_sensor.timestamp,
        "failure_probability": prediction["failure_probability"],
        "alert_level": prediction["alert_level"],
        "active_rules": [rule.name for rule in matched_rules],
        "calibration_method": explanation.get("calibration_method"),
        "top_positive": explanation.get("top_positive", []),
        "top_negative": explanation.get("top_negative", []),
        "ranked_features": explanation.get("ranked_features", []),
        "global_importance": explanation.get("global_importance", []),
    }


@router.post("/retrain-from-feedback", response_model=RetrainReportOut)
def retrain_feedback_model(
    payload: RetrainRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "expert")),
):
    try:
        report = retrain_from_feedback(db, horizon_hours=payload.horizon_hours, minimum_samples=payload.minimum_samples)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    write_audit_log(
        db,
        "retrain_feedback_model",
        "ml_model",
        user=current_user,
        entity_id="maintenance_model",
        request=request,
        details=f"samples={report['dataset_size']},model={report['best_model']}",
    )
    db.commit()
    publish_event(
        "ml_model_retrained",
        best_model=report["best_model"],
        dataset_size=report["dataset_size"],
        primary_metric=report["metrics"].get(report["primary_metric"], 0),
    )
    return report
