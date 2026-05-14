from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.models import Notification


def create_notification(
    db: Session,
    *,
    title: str,
    message: str,
    severity: str = "info",
    entity_type: str | None = None,
    entity_id: int | str | None = None,
) -> Notification:
    notification = Notification(
        title=title[:140],
        message=message,
        severity=severity,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
    )
    db.add(notification)
    return notification
