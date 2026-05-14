import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.models import BusinessRule, BusinessRuleVersion, Machine, SensorData
from app.schemas.common import RuleCreate, RuleOut, RuleSimulationMatch, RuleSimulationOut, RuleUpdate, RuleVersionOut
from app.services.audit import write_audit_log
from app.services.rules_engine import compare

router = APIRouter(prefix="/api/rules", tags=["rules"])


def _create_rule_snapshot(db: Session, rule: BusinessRule) -> None:
    snapshot = BusinessRuleVersion(
        rule_id=rule.id,
        version=rule.version,
        snapshot=json.dumps(
            {
                "name": rule.name,
                "machine_type": rule.machine_type,
                "metric": rule.metric,
                "operator": rule.operator,
                "threshold": rule.threshold,
                "duration_seconds": rule.duration_seconds,
                "severity": rule.severity,
                "confidence": rule.confidence,
                "is_active": rule.is_active,
            },
            ensure_ascii=False,
        ),
    )
    db.add(snapshot)


@router.get("/", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(BusinessRule).order_by(BusinessRule.updated_at.desc(), BusinessRule.id.desc()).all()


@router.post("/", response_model=RuleOut)
def create_rule(
    payload: RuleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "expert")),
):
    rule = BusinessRule(**payload.model_dump())
    db.add(rule)
    db.flush()
    _create_rule_snapshot(db, rule)
    write_audit_log(
        db,
        "create_rule",
        "business_rule",
        user=current_user,
        entity_id=rule.id,
        request=request,
        details=rule.name,
    )
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=RuleOut)
def update_rule(
    rule_id: int,
    payload: RuleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "expert")),
):
    rule = db.query(BusinessRule).filter(BusinessRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    for key, value in payload.model_dump().items():
        setattr(rule, key, value)
    rule.version += 1
    _create_rule_snapshot(db, rule)
    write_audit_log(
        db,
        "update_rule",
        "business_rule",
        user=current_user,
        entity_id=rule.id,
        request=request,
        details=rule.name,
    )
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/{rule_id}/toggle", response_model=RuleOut)
def toggle_rule(
    rule_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "expert")),
):
    rule = db.query(BusinessRule).filter(BusinessRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.is_active = not rule.is_active
    rule.version += 1
    _create_rule_snapshot(db, rule)
    write_audit_log(
        db,
        "toggle_rule",
        "business_rule",
        user=current_user,
        entity_id=rule.id,
        request=request,
        details=f"is_active={rule.is_active}",
    )
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/{rule_id}/versions", response_model=list[RuleVersionOut])
def list_rule_versions(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rule = db.query(BusinessRule).filter(BusinessRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return (
        db.query(BusinessRuleVersion)
        .filter(BusinessRuleVersion.rule_id == rule_id)
        .order_by(BusinessRuleVersion.version.desc())
        .all()
    )


@router.get("/{rule_id}/simulate", response_model=RuleSimulationOut)
def simulate_rule(
    rule_id: int,
    machine_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rule = db.query(BusinessRule).filter(BusinessRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    query = (
        db.query(SensorData)
        .join(Machine, Machine.id == SensorData.machine_id)
        .filter(Machine.machine_type == rule.machine_type, Machine.is_deleted.is_(False))
        .order_by(SensorData.timestamp.desc())
    )
    if machine_id:
        query = query.filter(SensorData.machine_id == machine_id)

    rows = query.limit(300).all()
    matches = []
    for row in rows:
        metric_value = getattr(row, rule.metric, None)
        if metric_value is None:
            continue
        if compare(float(metric_value), rule.operator, rule.threshold):
            matches.append(
                RuleSimulationMatch(
                    sensor_id=row.id,
                    machine_id=row.machine_id,
                    timestamp=row.timestamp,
                    metric_value=float(metric_value),
                )
            )

    total_records = len(rows)
    matched_records = len(matches)
    return RuleSimulationOut(
        rule_id=rule.id,
        total_records=total_records,
        matched_records=matched_records,
        match_rate=round(matched_records / total_records, 4) if total_records else 0,
        latest_matches=matches[:10],
    )
