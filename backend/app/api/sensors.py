from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import Machine, SensorData, User
from app.schemas.common import SensorDataCreate, SensorDataOut
from app.services.audit import write_audit_log
from app.services.maintenance_service import process_sensor_reading
from app.ml.model_service import ModelUnavailableError

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.get("/", response_model=list[SensorDataOut])
def list_sensor_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    machine_id: int | None = None,
):
    query = db.query(SensorData)
    if machine_id:
        query = query.filter(SensorData.machine_id == machine_id)
    return query.order_by(SensorData.timestamp.desc()).limit(300).all()


@router.post("/ingest", response_model=SensorDataOut)
def ingest_sensor_data(
    payload: SensorDataCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    machine = db.query(Machine).filter(Machine.id == payload.machine_id, Machine.is_deleted.is_(False)).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    try:
        result = process_sensor_reading(db, machine, payload.model_dump())
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    write_audit_log(
        db,
        "ingest_sensor_data",
        "machine",
        user=current_user,
        entity_id=machine.id,
        request=request,
        details=f"probability={result['final_probability']}",
    )
    db.commit()
    db.refresh(result["sensor"])
    return result["sensor"]
