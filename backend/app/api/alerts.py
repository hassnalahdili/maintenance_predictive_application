from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.models import Alert, User
from app.schemas.common import AlertAcknowledge, AlertOut
from app.services.audit import write_audit_log
from app.services.live_updates import publish_event
from app.services.maintenance_service import escalate_pending_alerts, serialize_alert
from app.services.notifications import create_notification

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/", response_model=list[AlertOut])
def list_alerts(
    status: str | None = None,
    level: str | None = None,
    machine_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    escalate_pending_alerts(db)
    db.commit()

    query = db.query(Alert).order_by(Alert.created_at.desc())
    if status:
        if status == "active":
            query = query.filter(Alert.acknowledged.is_(False), Alert.escalated.is_(False))
        elif status == "acknowledged":
            query = query.filter(Alert.acknowledged.is_(True))
        elif status == "escalated":
            query = query.filter(Alert.escalated.is_(True))
    if level:
        query = query.filter(Alert.level == level)
    if machine_id:
        query = query.filter(Alert.machine_id == machine_id)
    return [serialize_alert(alert) for alert in query.limit(300).all()]


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(
    alert_id: int,
    payload: AlertAcknowledge,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "technicien")),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    alert.acknowledgment_comment = payload.comment
    alert.status = "acknowledged"
    create_notification(
        db,
        title="Alerte prise en charge",
        message=f"L'alerte #{alert.id} a ete accusee par {current_user.full_name}.",
        severity="success",
        entity_type="alert",
        entity_id=alert.id,
    )
    write_audit_log(
        db,
        "acknowledge_alert",
        "alert",
        user=current_user,
        entity_id=alert.id,
        request=request,
        details=payload.comment,
    )
    db.commit()
    db.refresh(alert)
    publish_event("alert_acknowledged", alert_id=alert.id, machine_id=alert.machine_id, status=alert.status)
    return serialize_alert(alert)
