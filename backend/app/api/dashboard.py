from datetime import datetime
from math import sqrt

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.domain import MACHINE_TYPES, RISK_LEVELS, normalize_machine_type
from app.db.session import get_db
from app.models.models import Alert, Machine, Prediction, SensorData, User
from app.schemas.common import (
    DashboardMachineHealth,
    DashboardProbabilityPoint,
    DashboardSensorSnapshot,
    DashboardSummaryOut,
    DashboardTrendPoint,
)
from app.services.maintenance_service import escalate_pending_alerts

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryOut)
def summary(
    machine_type: str | None = None,
    risk_level: str | None = None,
    site: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    escalate_pending_alerts(db)
    db.commit()

    machine_query = db.query(Machine).filter(Machine.is_deleted.is_(False))
    if machine_type:
        machine_query = machine_query.filter(Machine.machine_type == normalize_machine_type(machine_type))
    if site:
        machine_query = machine_query.filter(Machine.site == site)

    machines = machine_query.order_by(Machine.name.asc()).all()
    machine_ids = [machine.id for machine in machines]

    predictions = []
    sensors = []
    if machine_ids:
        prediction_limit = max(len(machine_ids) * 24, 240)
        predictions = (
            db.query(Prediction)
            .filter(Prediction.machine_id.in_(machine_ids))
            .order_by(Prediction.timestamp.desc())
            .limit(prediction_limit)
            .all()
        )
        sensor_limit = max(len(machine_ids) * 24, 240)
        sensors = (
            db.query(SensorData)
            .filter(SensorData.machine_id.in_(machine_ids))
            .order_by(SensorData.timestamp.desc())
            .limit(sensor_limit)
            .all()
        )

    latest_by_machine: dict[int, Prediction] = {}
    prediction_history_by_machine: dict[int, list[Prediction]] = {}
    for prediction in predictions:
        latest_by_machine.setdefault(prediction.machine_id, prediction)
        history = prediction_history_by_machine.setdefault(prediction.machine_id, [])
        if len(history) < 12:
            history.append(prediction)

    latest_sensor_by_machine: dict[int, SensorData] = {}
    sensor_history_by_machine: dict[int, list[SensorData]] = {}
    for sensor in sensors:
        latest_sensor_by_machine.setdefault(sensor.machine_id, sensor)
        history = sensor_history_by_machine.setdefault(sensor.machine_id, [])
        if len(history) < 12:
            history.append(sensor)

    machine_health = []
    for machine in machines:
        latest_prediction = latest_by_machine.get(machine.id)
        latest_sensor = latest_sensor_by_machine.get(machine.id)
        alert_level = latest_prediction.alert_level if latest_prediction else "normal"
        probability = latest_prediction.failure_probability if latest_prediction else 0.0
        if risk_level and alert_level != risk_level:
            continue

        current_sensor_values = None
        if latest_sensor:
            vibration_total = sqrt(
                (latest_sensor.vibration_x or 0.0) ** 2
                + (latest_sensor.vibration_y or 0.0) ** 2
                + (latest_sensor.vibration_z or 0.0) ** 2
            )
            current_sensor_values = DashboardSensorSnapshot(
                timestamp=latest_sensor.timestamp,
                temperature=round(latest_sensor.temperature, 2),
                vibration_total=round(vibration_total, 2),
                pressure=round(latest_sensor.pressure, 2),
                rpm=round(latest_sensor.rpm, 2),
                current=round(latest_sensor.current, 2),
            )

        sensor_trend = []
        for sensor in reversed(sensor_history_by_machine.get(machine.id, [])):
            vibration_total = sqrt(
                (sensor.vibration_x or 0.0) ** 2
                + (sensor.vibration_y or 0.0) ** 2
                + (sensor.vibration_z or 0.0) ** 2
            )
            sensor_trend.append(
                DashboardSensorSnapshot(
                    timestamp=sensor.timestamp,
                    temperature=round(sensor.temperature, 2),
                    vibration_total=round(vibration_total, 2),
                    pressure=round(sensor.pressure, 2),
                    rpm=round(sensor.rpm, 2),
                    current=round(sensor.current, 2),
                )
            )

        probability_trend = [
            DashboardProbabilityPoint(timestamp=item.timestamp, value=round(item.failure_probability, 4))
            for item in reversed(prediction_history_by_machine.get(machine.id, []))
        ]

        machine_health.append(
            DashboardMachineHealth(
                machine_id=machine.id,
                machine_name=machine.name,
                machine_type=machine.machine_type,
                site=machine.site,
                status=machine.status,
                alert_level=alert_level,
                failure_probability=round(probability, 4),
                remaining_useful_life_days=(
                    round(latest_prediction.remaining_useful_life_days, 2) if latest_prediction else None
                ),
                current_sensor_values=current_sensor_values,
                sensor_trend=sensor_trend,
                probability_trend=probability_trend,
                timestamp=latest_prediction.timestamp if latest_prediction else None,
            )
        )

    machine_health.sort(key=lambda item: (item.failure_probability, item.machine_name.lower()), reverse=True)

    filtered_machine_ids = [item.machine_id for item in machine_health]

    recent_predictions = [prediction for prediction in predictions if prediction.machine_id in filtered_machine_ids][:120]
    trend_buckets = {}
    for prediction in reversed(recent_predictions):
        label = prediction.timestamp.replace(second=0, microsecond=0)
        trend_buckets.setdefault(label, []).append(prediction.failure_probability)

    prediction_trend = [
        DashboardTrendPoint(
            timestamp=timestamp,
            average_probability=round(sum(values) / len(values), 4),
            max_probability=round(max(values), 4),
        )
        for timestamp, values in sorted(trend_buckets.items())[-12:]
    ]

    status_distribution = {}
    risk_distribution = {level: 0 for level in RISK_LEVELS}
    for item in machine_health:
        status_distribution[item.status] = status_distribution.get(item.status, 0) + 1
        risk_distribution[item.alert_level] = risk_distribution.get(item.alert_level, 0) + 1

    active_alerts_query = db.query(Alert).filter(Alert.acknowledged.is_(False))
    if filtered_machine_ids:
        active_alerts_query = active_alerts_query.filter(Alert.machine_id.in_(filtered_machine_ids))
    active_alerts = active_alerts_query.count() if filtered_machine_ids else 0

    available_sites = sorted({machine.site for machine in db.query(Machine).filter(Machine.is_deleted.is_(False)).all() if machine.site})
    available_types = [machine_type for machine_type in MACHINE_TYPES]

    return DashboardSummaryOut(
        total_machines=len(machine_health),
        active_alerts=active_alerts,
        machines_at_risk=sum(1 for item in machine_health if item.alert_level in {"low", "medium", "high", "critical"}),
        status_distribution=status_distribution,
        risk_distribution=risk_distribution,
        prediction_trend=prediction_trend,
        machine_health=machine_health,
        available_types=available_types,
        available_sites=available_sites,
        last_updated_at=datetime.utcnow(),
    )
