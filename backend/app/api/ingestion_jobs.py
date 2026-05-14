from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.models import IngestionJob, IngestionJobLog, Machine, User
from app.schemas.common import IngestionJobCreate, IngestionJobLogOut, IngestionJobOut, IngestionJobUpdate
from app.services.audit import write_audit_log
from app.services.ingestion_service import ensure_job_state, log_job_event, serialize_job
from app.services.live_updates import publish_event
from app.services.replay_service import list_replay_sources

router = APIRouter(prefix="/api/ingestion-jobs", tags=["ingestion-jobs"])


@router.get("/", response_model=list[IngestionJobOut])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    jobs = (
        db.query(IngestionJob)
        .options(joinedload(IngestionJob.machine))
        .order_by(IngestionJob.created_at.desc())
        .all()
    )
    return [serialize_job(job) for job in jobs]


@router.post("/", response_model=IngestionJobOut)
def create_job(
    payload: IngestionJobCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "technicien", "expert")),
):
    machine = db.query(Machine).filter(Machine.id == payload.machine_id, Machine.is_deleted.is_(False)).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    if payload.mode == "replay":
        source_map = {item["source_id"]: item for item in list_replay_sources()}
        source = source_map.get(payload.source_id or "")
        if source is None:
            raise HTTPException(status_code=400, detail="Replay source not found")
        if source["machine_type"] != machine.machine_type:
            raise HTTPException(status_code=400, detail="Replay source incompatible with selected machine")

    job = IngestionJob(**payload.model_dump(), created_by_user_id=current_user.id)
    db.add(job)
    db.flush()
    log_job_event(db, job.id, "created", f"Job cree en mode {job.mode}.")
    write_audit_log(
        db,
        "create_ingestion_job",
        "ingestion_job",
        user=current_user,
        entity_id=job.id,
        request=request,
        details=f"{job.mode}:{job.source_id or 'simulator'}",
    )
    db.commit()
    db.refresh(job)
    return serialize_job(job)


@router.put("/{job_id}", response_model=IngestionJobOut)
def update_job(
    job_id: int,
    payload: IngestionJobUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "technicien", "expert")),
):
    job = (
        db.query(IngestionJob)
        .options(joinedload(IngestionJob.machine))
        .filter(IngestionJob.id == job_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, key, value)
    log_job_event(db, job.id, "updated", "Parametres du job mis a jour.")
    write_audit_log(
        db,
        "update_ingestion_job",
        "ingestion_job",
        user=current_user,
        entity_id=job.id,
        request=request,
        details=f"active={job.is_active}",
    )
    db.commit()
    db.refresh(job)
    ensure_job_state(job.id, job.is_active)
    publish_event("ingestion_job_status", job_id=job.id, is_active=job.is_active)
    return serialize_job(job)


@router.post("/{job_id}/start", response_model=IngestionJobOut)
def start_job(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "technicien", "expert")),
):
    job = (
        db.query(IngestionJob)
        .options(joinedload(IngestionJob.machine))
        .filter(IngestionJob.id == job_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    job.is_active = True
    job.last_error = None
    log_job_event(db, job.id, "started", "Job demarre manuellement.")
    write_audit_log(db, "start_ingestion_job", "ingestion_job", user=current_user, entity_id=job.id, request=request)
    db.commit()
    db.refresh(job)
    ensure_job_state(job.id, True)
    publish_event("ingestion_job_status", job_id=job.id, is_active=True)
    return serialize_job(job)


@router.post("/{job_id}/stop", response_model=IngestionJobOut)
def stop_job(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "technicien", "expert")),
):
    job = (
        db.query(IngestionJob)
        .options(joinedload(IngestionJob.machine))
        .filter(IngestionJob.id == job_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    job.is_active = False
    log_job_event(db, job.id, "stopped", "Job arrete manuellement.")
    write_audit_log(db, "stop_ingestion_job", "ingestion_job", user=current_user, entity_id=job.id, request=request)
    db.commit()
    db.refresh(job)
    ensure_job_state(job.id, False)
    publish_event("ingestion_job_status", job_id=job.id, is_active=False)
    return serialize_job(job)


@router.get("/{job_id}/logs", response_model=list[IngestionJobLogOut])
def list_job_logs(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not db.query(IngestionJob).filter(IngestionJob.id == job_id).first():
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return (
        db.query(IngestionJobLog)
        .filter(IngestionJobLog.job_id == job_id)
        .order_by(IngestionJobLog.created_at.desc())
        .limit(100)
        .all()
    )
