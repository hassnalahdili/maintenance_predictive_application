from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.models import AuditLog, User


def get_request_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


def write_audit_log(
    db: Session,
    action: str,
    entity_type: str,
    *,
    user: User | None = None,
    entity_id: Any | None = None,
    request: Request | None = None,
    details: str | None = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        ip_address=get_request_ip(request),
        details=details,
    )
    db.add(log)
    return log
