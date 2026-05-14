from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import Machine, Prediction, User
from app.schemas.common import PredictionOut
from app.ml.model_service import ModelUnavailableError
from app.services.audit import write_audit_log
from app.services.maintenance_service import process_sensor_reading, serialize_prediction
from app.services.simulator import generate_sensor_data

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("/", response_model=list[PredictionOut])
def list_predictions(
    machine_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Prediction).order_by(Prediction.timestamp.desc())
    if machine_id:
        query = query.filter(Prediction.machine_id == machine_id)
    return [serialize_prediction(prediction) for prediction in query.limit(300).all()]


@router.post("/simulate/{machine_id}")
def simulate_prediction(
    machine_id: int,
    request: Request,
    drift: bool = False,
    persist: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    machine = db.query(Machine).filter(Machine.id == machine_id, Machine.is_deleted.is_(False)).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    sensor = generate_sensor_data(machine, drift=drift)
    payload = {
        "machine_id": machine.id,
        "timestamp": sensor.timestamp,
        "temperature": sensor.temperature,
        "vibration_x": sensor.vibration_x,
        "vibration_y": sensor.vibration_y,
        "vibration_z": sensor.vibration_z,
        "pressure": sensor.pressure,
        "rpm": sensor.rpm,
        "current": sensor.current,
    }

    if persist:
        try:
            result = process_sensor_reading(db, machine, payload)
        except ModelUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        write_audit_log(
            db,
            "simulate_prediction",
            "machine",
            user=current_user,
            entity_id=machine.id,
            request=request,
            details=f"drift={drift}",
        )
        db.commit()
        db.refresh(result["prediction"])
        return {
            "sensor": payload,
            "prediction": serialize_prediction(result["prediction"]).model_dump(),
            "features": result["features"],
            "active_rules": [rule.name for rule in result["matched_rules"]],
        }

    return payload
