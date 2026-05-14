from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.models import Alert, Machine, MaintenanceIntervention, User
from app.schemas.common import MaintenanceInterventionCreate, MaintenanceInterventionOut, MaintenanceInterventionUpdate
from app.services.audit import write_audit_log
from app.services.interventions import serialize_intervention
from app.services.live_updates import publish_event

router = APIRouter(prefix="/api/interventions", tags=["interventions"])


@router.get("/", response_model=list[MaintenanceInterventionOut])
def list_interventions(
    machine_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(MaintenanceIntervention)
        .options(joinedload(MaintenanceIntervention.machine), joinedload(MaintenanceIntervention.technician))
        .order_by(MaintenanceIntervention.opened_at.desc())
    )
    if machine_id:
        query = query.filter(MaintenanceIntervention.machine_id == machine_id)
    if status:
        query = query.filter(MaintenanceIntervention.status == status)
    return [serialize_intervention(item) for item in query.limit(300).all()]


@router.post("/", response_model=MaintenanceInterventionOut)
def create_intervention(
    payload: MaintenanceInterventionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "technicien", "expert")),
):
    machine = db.query(Machine).filter(Machine.id == payload.machine_id, Machine.is_deleted.is_(False)).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    if payload.alert_id is not None and not db.query(Alert).filter(Alert.id == payload.alert_id).first():
        raise HTTPException(status_code=404, detail="Alert not found")

    intervention = MaintenanceIntervention(
        **payload.model_dump(exclude={"opened_at"}),
        opened_at=payload.opened_at or datetime.utcnow(),
    )
    if intervention.status == "resolved" and intervention.closed_at is None:
        intervention.closed_at = datetime.utcnow()
    db.add(intervention)
    db.flush()
    write_audit_log(
        db,
        "create_intervention",
        "maintenance_intervention",
        user=current_user,
        entity_id=intervention.id,
        request=request,
        details=intervention.outcome_label,
    )
    db.commit()
    db.refresh(intervention)
    publish_event(
        "intervention_updated",
        intervention_id=intervention.id,
        machine_id=intervention.machine_id,
        status=intervention.status,
        outcome_label=intervention.outcome_label,
    )
    return serialize_intervention(intervention)


@router.put("/{intervention_id}", response_model=MaintenanceInterventionOut)
def update_intervention(
    intervention_id: int,
    payload: MaintenanceInterventionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "technicien", "expert")),
):
    intervention = (
        db.query(MaintenanceIntervention)
        .options(joinedload(MaintenanceIntervention.machine), joinedload(MaintenanceIntervention.technician))
        .filter(MaintenanceIntervention.id == intervention_id)
        .first()
    )
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("machine_id") is not None:
        machine = db.query(Machine).filter(Machine.id == updates["machine_id"], Machine.is_deleted.is_(False)).first()
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")
    for key, value in updates.items():
        setattr(intervention, key, value)
    if intervention.status == "resolved" and intervention.closed_at is None:
        intervention.closed_at = datetime.utcnow()
    db.flush()
    write_audit_log(
        db,
        "update_intervention",
        "maintenance_intervention",
        user=current_user,
        entity_id=intervention.id,
        request=request,
        details=intervention.status,
    )
    db.commit()
    db.refresh(intervention)
    publish_event(
        "intervention_updated",
        intervention_id=intervention.id,
        machine_id=intervention.machine_id,
        status=intervention.status,
        outcome_label=intervention.outcome_label,
    )
    return serialize_intervention(intervention)
