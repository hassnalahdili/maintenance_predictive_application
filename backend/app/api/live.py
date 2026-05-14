from __future__ import annotations

from jose import JWTError, jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import User
from app.services.live_updates import manager


router = APIRouter(tags=["live"])


def _authenticate_websocket(token: str | None) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(user_id), User.is_active.is_(True)).first()
        if user is None:
            return None
        db.expunge(user)
        return user
    finally:
        db.close()


@router.websocket("/ws/live")
async def live_socket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    user = _authenticate_websocket(token)
    if user is None:
        await websocket.close(code=4401)
        return

    await manager.connect(websocket)
    await websocket.send_json(
        {
            "type": "live_connected",
            "user_id": user.id,
            "user_name": user.full_name,
        }
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
