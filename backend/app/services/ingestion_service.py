from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy.orm import joinedload

from app.db.session import SessionLocal
from app.ml.model_service import ModelUnavailableError
from app.models.models import IngestionJob, IngestionJobLog
from app.schemas.common import IngestionJobOut
from app.services.live_updates import publish_event
from app.services.maintenance_service import process_sensor_reading, serialize_prediction
from app.services.replay_service import replay_step, reset_replay_state
from app.services.simulator import generate_sensor_data


_loop: asyncio.AbstractEventLoop | None = None
_tasks: dict[int, asyncio.Task] = {}


def configure_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def serialize_job(job: IngestionJob) -> IngestionJobOut:
    machine = job.machine
    return IngestionJobOut(
        id=job.id,
        machine_id=job.machine_id,
        machine_name=machine.name if machine else None,
        machine_type=machine.machine_type if machine else None,
        mode=job.mode,
        source_id=job.source_id,
        interval_seconds=job.interval_seconds,
        replay_steps=job.replay_steps,
        drift=job.drift,
        auto_restart=job.auto_restart,
        is_active=job.is_active,
        last_run_at=job.last_run_at,
        last_error=job.last_error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def log_job_event(db, job_id: int, event_type: str, message: str, level: str = "info") -> IngestionJobLog:
    log = IngestionJobLog(job_id=job_id, event_type=event_type, message=message, level=level)
    db.add(log)
    return log


async def _stop_job_task(job_id: int) -> None:
    task = _tasks.get(job_id)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    _tasks.pop(job_id, None)


async def _ensure_job_task(job_id: int) -> None:
    task = _tasks.get(job_id)
    if task and not task.done():
        return
    _tasks[job_id] = asyncio.create_task(_job_loop(job_id))


def ensure_job_state(job_id: int, should_run: bool) -> None:
    if _loop is None:
        return
    if should_run:
        asyncio.run_coroutine_threadsafe(_ensure_job_task(job_id), _loop)
    else:
        asyncio.run_coroutine_threadsafe(_stop_job_task(job_id), _loop)


def resume_active_jobs() -> None:
    db = SessionLocal()
    try:
        active_job_ids = [job_id for (job_id,) in db.query(IngestionJob.id).filter(IngestionJob.is_active.is_(True)).all()]
    finally:
        db.close()
    for job_id in active_job_ids:
        ensure_job_state(job_id, True)


def _run_job_cycle(job_id: int) -> tuple[bool, int]:
    db = SessionLocal()
    try:
        job = (
            db.query(IngestionJob)
            .options(joinedload(IngestionJob.machine))
            .filter(IngestionJob.id == job_id)
            .first()
        )
        if not job or not job.is_active:
            return False, 0

        machine = job.machine
        if machine is None or machine.is_deleted:
            job.is_active = False
            job.last_error = "Machine introuvable ou supprimee."
            log_job_event(db, job.id, "error", job.last_error, "error")
            db.commit()
            publish_event("ingestion_job_error", job_id=job_id, error=job.last_error)
            return False, 0

        latest_prediction = None
        if job.mode == "replay":
            if not job.source_id:
                raise ValueError("Aucune source de rejeu n'est configuree.")
            result = replay_step(db, machine, source_id=job.source_id, steps=job.replay_steps)
            if result["injected_rows"] == 0:
                if job.auto_restart:
                    reset_replay_state(job.source_id)
                    result = replay_step(db, machine, source_id=job.source_id, steps=job.replay_steps)
                else:
                    job.is_active = False
                    job.last_run_at = datetime.utcnow()
                    job.last_error = None
                    log_job_event(db, job.id, "completed", "Source de rejeu terminee.", "info")
                    db.commit()
                    publish_event("ingestion_job_completed", job_id=job.id, machine_id=machine.id, machine_name=machine.name)
                    return False, 0
            latest_prediction = result["latest_prediction"]
        else:
            sensor = generate_sensor_data(machine, drift=job.drift)
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
            result = process_sensor_reading(db, machine, payload)
            latest_prediction = serialize_prediction(result["prediction"]).model_dump()

        job.last_run_at = datetime.utcnow()
        job.last_error = None
        log_job_event(
            db,
            job.id,
            "tick",
            f"{job.mode} execute sur {machine.name}.",
            "info",
        )
        db.commit()
        publish_event(
            "ingestion_job_tick",
            job_id=job.id,
            machine_id=machine.id,
            machine_name=machine.name,
            mode=job.mode,
            latest_prediction=latest_prediction,
        )
        return True, max(job.interval_seconds, 1)
    except ModelUnavailableError as exc:
        if "job" in locals() and job is not None:
            job.is_active = False
            job.last_error = str(exc)
            log_job_event(db, job.id, "error", str(exc), "error")
            db.commit()
        publish_event("ingestion_job_error", job_id=job_id, error=str(exc))
        return False, 0
    except Exception as exc:
        if "job" in locals() and job is not None:
            job.is_active = False
            job.last_error = str(exc)
            log_job_event(db, job.id, "error", str(exc), "error")
            db.commit()
        publish_event("ingestion_job_error", job_id=job_id, error=str(exc))
        return False, 0
    finally:
        db.close()


async def _job_loop(job_id: int) -> None:
    try:
        while True:
            keep_running, interval_seconds = await asyncio.to_thread(_run_job_cycle, job_id)
            if not keep_running:
                break
            await asyncio.sleep(interval_seconds)
    finally:
        _tasks.pop(job_id, None)
