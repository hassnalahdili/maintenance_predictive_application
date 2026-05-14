from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.api.deps import get_current_user, require_roles
from app.core.domain import normalize_machine_type
from app.db.session import get_db
from app.models.models import Machine, MaintenanceIntervention, SensorData
from app.schemas.common import MachineCreate, MachineDetailOut, MachineOut, MachineUpdate, SensorDataOut
from app.services.audit import write_audit_log
from app.services.assets import apply_asset_node_to_machine, resolve_machine_asset_node, serialize_machine
from app.services.interventions import serialize_intervention
from app.services.maintenance_service import serialize_alert, serialize_prediction

router = APIRouter(prefix="/api/machines", tags=["machines"])


def _active_machines_query(db: Session):
    return db.query(Machine).filter(Machine.is_deleted.is_(False))


@router.get("/", response_model=list[MachineOut])
def list_machines(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    machine_type: str | None = None,
    site: str | None = None,
    search: str | None = None,
):
    query = _active_machines_query(db).options(joinedload(Machine.asset_node)).order_by(Machine.updated_at.desc(), Machine.id.desc())
    if machine_type:
        query = query.filter(Machine.machine_type == normalize_machine_type(machine_type))
    if site:
        query = query.filter(Machine.site == site)
    if search:
        query = query.filter(Machine.name.ilike(f"%{search.strip()}%"))
    return [serialize_machine(machine) for machine in query.all()]


@router.get("/{machine_id}", response_model=MachineDetailOut)
def get_machine_detail(
    machine_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    machine = (
        _active_machines_query(db)
        .options(joinedload(Machine.asset_node), joinedload(Machine.interventions).joinedload(MaintenanceIntervention.technician))
        .filter(Machine.id == machine_id)
        .first()
    )
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    sensors = (
        db.query(SensorData)
        .filter(SensorData.machine_id == machine_id)
        .order_by(SensorData.timestamp.desc())
        .limit(30)
        .all()
    )
    predictions = sorted(machine.predictions, key=lambda item: item.timestamp, reverse=True)[:20]
    alerts = sorted(machine.alerts, key=lambda item: item.created_at, reverse=True)[:20]

    return MachineDetailOut(
        **serialize_machine(machine).model_dump(),
        sensor_history=[SensorDataOut.model_validate(sensor) for sensor in sensors],
        prediction_history=[serialize_prediction(prediction) for prediction in predictions],
        alert_history=[serialize_alert(alert) for alert in alerts],
        interventions=[serialize_intervention(intervention) for intervention in sorted(machine.interventions, key=lambda item: item.opened_at, reverse=True)[:20]],
    )


@router.post("/", response_model=MachineOut)
def create_machine(
    payload: MachineCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "technicien", "expert")),
):
    asset_node = resolve_machine_asset_node(
        db,
        asset_node_id=payload.asset_node_id,
        site=payload.site,
        zone=payload.zone,
        line=payload.line,
        component=payload.component,
    )
    if payload.asset_node_id and asset_node is None:
        raise HTTPException(status_code=404, detail="Hierarchy node not found")
    machine = Machine(**payload.model_dump(), asset_node=asset_node)
    if asset_node is not None:
        apply_asset_node_to_machine(machine, asset_node)
    db.add(machine)
    db.flush()
    write_audit_log(
        db,
        "create_machine",
        "machine",
        user=current_user,
        entity_id=machine.id,
        request=request,
        details=machine.name,
    )
    db.commit()
    db.refresh(machine)
    db.refresh(machine)
    return serialize_machine(machine)


@router.put("/{machine_id}", response_model=MachineOut)
def update_machine(
    machine_id: int,
    payload: MachineUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "technicien", "expert")),
):
    machine = _active_machines_query(db).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    asset_node = resolve_machine_asset_node(
        db,
        asset_node_id=payload.asset_node_id,
        site=payload.site,
        zone=payload.zone,
        line=payload.line,
        component=payload.component,
    )
    if payload.asset_node_id and asset_node is None:
        raise HTTPException(status_code=404, detail="Hierarchy node not found")
    for key, value in payload.model_dump().items():
        setattr(machine, key, value)
    if asset_node is not None:
        apply_asset_node_to_machine(machine, asset_node)
    else:
        machine.asset_node = None
    write_audit_log(
        db,
        "update_machine",
        "machine",
        user=current_user,
        entity_id=machine.id,
        request=request,
        details=machine.name,
    )
    db.commit()
    db.refresh(machine)
    db.refresh(machine)
    return serialize_machine(machine)


@router.delete("/{machine_id}")
def delete_machine(
    machine_id: int,
    request: Request,
    hard_delete: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    if hard_delete:
        db.delete(machine)
    else:
        machine.is_deleted = True
        machine.updated_at = datetime.utcnow()
    write_audit_log(
        db,
        "delete_machine_hard" if hard_delete else "delete_machine_soft",
        "machine",
        user=current_user,
        entity_id=machine_id,
        request=request,
        details=machine.name,
    )
    db.commit()
    return {"message": "Machine deleted"}
