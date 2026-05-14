import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.assets import router as assets_router
from app.api import users
from app.api.alerts import router as alerts_router
from app.api.audit_logs import router as audit_logs_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.exports import router as exports_router
from app.api.ingestion_jobs import router as ingestion_jobs_router
from app.api.interventions import router as interventions_router
from app.api.live import router as live_router
from app.api.machines import router as machines_router
from app.api.ml import router as ml_router
from app.api.notifications import router as notifications_router
from app.api.predictions import router as predictions_router
from app.api.rules import router as rules_router
from app.api.sensors import router as sensors_router
from app.core.config import settings
from app.core.domain import normalize_machine_type, normalize_role
from app.core.security import get_password_hash
from app.db.session import Base, SessionLocal, engine
from app.models.models import BusinessRule, Machine, User
from app.services.assets import ensure_asset_path
from app.services.ingestion_service import configure_loop as configure_ingestion_loop, resume_active_jobs
from app.services.live_updates import configure_loop as configure_live_loop

app = FastAPI(title="Predictive Maintenance API", version="1.3.0")

request_counters: dict[str, deque] = defaultdict(deque)

if settings.proxy_headers:
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts or ["*"])

if settings.enforce_https:
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

if settings.auto_create_schema:
    Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(assets_router)
app.include_router(machines_router)
app.include_router(rules_router)
app.include_router(sensors_router)
app.include_router(alerts_router)
app.include_router(predictions_router)
app.include_router(dashboard_router)
app.include_router(interventions_router)
app.include_router(ingestion_jobs_router)
app.include_router(ml_router)
app.include_router(notifications_router)
app.include_router(exports_router)
app.include_router(users.router)
app.include_router(audit_logs_router)
app.include_router(live_router)


@app.middleware("http")
async def apply_rate_limit(request: Request, call_next):
    ip_address = request.client.host if request.client else "unknown"
    now = datetime.utcnow()
    bucket = request_counters[ip_address]
    window_start = now - timedelta(minutes=1)
    while bucket and bucket[0] < window_start:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_per_minute:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    bucket.append(now)
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_minute)
    return response


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    connect_sources = {"'self'"}
    for origin in settings.allowed_origins:
        connect_sources.add(origin)
        parsed = urlparse(origin)
        if parsed.scheme in {"http", "https"}:
            ws_scheme = "wss" if parsed.scheme == "https" else "ws"
            connect_sources.add(f"{ws_scheme}://{parsed.netloc}")
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        f"connect-src {' '.join(sorted(connect_sources))}; "
        "frame-ancestors 'none';"
    )
    if settings.enforce_https:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def ensure_schema_updates() -> None:
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_required BOOLEAN DEFAULT FALSE",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS zone VARCHAR(120) NULL",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS line VARCHAR(120) NULL",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS component VARCHAR(120) NULL",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS asset_node_id INTEGER NULL",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NULL",
        "ALTER TABLE business_rules ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1",
        "ALTER TABLE business_rules ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NULL",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS probability DOUBLE PRECISION NULL",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'active'",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS escalated BOOLEAN DEFAULT FALSE",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMP NULL",
        "ALTER TABLE maintenance_interventions ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'medium'",
        "ALTER TABLE maintenance_interventions ADD COLUMN IF NOT EXISTS planned_at TIMESTAMP NULL",
        "ALTER TABLE maintenance_interventions ADD COLUMN IF NOT EXISTS parts_used TEXT NULL",
        "ALTER TABLE maintenance_interventions ADD COLUMN IF NOT EXISTS estimated_cost DOUBLE PRECISION DEFAULT 0",
        """
        CREATE TABLE IF NOT EXISTS ingestion_job_logs (
            id SERIAL PRIMARY KEY,
            job_id INTEGER NOT NULL REFERENCES ingestion_jobs(id) ON DELETE CASCADE,
            event_type VARCHAR(60) NOT NULL,
            level VARCHAR(20) DEFAULT 'info',
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            title VARCHAR(140) NOT NULL,
            message TEXT NOT NULL,
            severity VARCHAR(20) DEFAULT 'info',
            entity_type VARCHAR(80) NULL,
            entity_id VARCHAR(80) NULL,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        connection.execute(text("UPDATE users SET role = 'technicien' WHERE role = 'technician'"))
        connection.execute(text("UPDATE machines SET machine_type = 'generateur' WHERE machine_type IN ('générateur', 'generator')"))
        connection.execute(text("UPDATE business_rules SET machine_type = 'generateur' WHERE machine_type IN ('générateur', 'generator')"))
        connection.execute(text("UPDATE machines SET machine_type = 'four' WHERE machine_type = 'furnace'"))
        connection.execute(text("UPDATE business_rules SET machine_type = 'four' WHERE machine_type = 'furnace'"))


@app.on_event("startup")
async def startup_runtime_services() -> None:
    loop = asyncio.get_running_loop()
    configure_live_loop(loop)
    configure_ingestion_loop(loop)
    resume_active_jobs()


@app.get("/")
def root():
    return {"message": "Predictive Maintenance API is running"}


@app.on_event("startup")
def seed_data():
    if settings.auto_create_schema:
        ensure_schema_updates()
    if not settings.auto_seed_data:
        return
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "admin@example.com").first():
            db.add(
                User(
                    full_name="Admin User",
                    email="admin@example.com",
                    hashed_password=get_password_hash("Admin123!"),
                    role=normalize_role("admin"),
                    password_changed_at=datetime.utcnow(),
                )
            )

        seeded_machines = [
            ("Moteur A1", "moteur", "Site 1", "Zone Assemblage", "Ligne A", "Roulement principal"),
            ("Pompe B2", "pompe", "Site 1", "Zone Utilites", "Ligne Eau", "Hydraulique"),
            ("Convoyeur C1", "convoyeur", "Site 1", "Zone Logistique", "Ligne C", "Bande"),
            ("Compresseur C3", "compresseur", "Site 2", "Zone Utilites", "Ligne Air", "Bloc compression"),
            ("Ventilateur V4", "ventilateur", "Site 2", "Zone Froid", "Ligne Ventilation", "Turbine"),
            ("Generateur G5", "generateur", "Site 3", "Zone Energie", "Ligne G", "Alternateur"),
            ("Broyeur D4", "broyeur", "Site 2", "Zone Broyage", "Ligne D", "Rotor"),
            ("Four F6", "four", "Site 3", "Zone Thermique", "Ligne Fusion", "Chambre"),
        ]
        for machine_name, machine_type, site, zone, line, component in seeded_machines:
            exists = (
                db.query(Machine)
                .filter(Machine.name == machine_name, Machine.machine_type == normalize_machine_type(machine_type))
                .first()
            )
            if not exists:
                db.add(
                    Machine(
                        name=machine_name,
                        machine_type=normalize_machine_type(machine_type),
                        site=site,
                        zone=zone,
                        line=line,
                        component=component,
                        asset_node=ensure_asset_path(db, site=site, zone=zone, line=line, component=component),
                    )
                )
            else:
                if not exists.asset_node_id:
                    exists.site = exists.site or site
                    exists.zone = exists.zone or zone
                    exists.line = exists.line or line
                    exists.component = exists.component or component
                    exists.asset_node = ensure_asset_path(
                        db,
                        site=exists.site,
                        zone=exists.zone,
                        line=exists.line,
                        component=exists.component,
                    )

        seeded_rules = [
            ("Surchauffe moteur", "moteur", "temperature", ">", 85, "high", 0.85),
            ("Vibration moteur", "moteur", "vibration_x", ">", 4.5, "high", 0.90),
            ("Surpression pompe", "pompe", "pressure", ">", 7.8, "medium", 0.80),
            ("Derapage convoyeur", "convoyeur", "rpm", "<", 1320, "medium", 0.76),
            ("Surchauffe compresseur", "compresseur", "temperature", ">", 88, "critical", 0.92),
            ("Surchauffe ventilateur", "ventilateur", "temperature", ">", 80, "medium", 0.82),
            ("Instabilite generateur", "generateur", "current", ">", 64, "high", 0.87),
            ("Surcharge broyeur", "broyeur", "current", ">", 68, "critical", 0.95),
            ("Surchauffe four", "four", "temperature", ">", 900, "critical", 0.96),
        ]
        for rule_name, machine_type, metric, operator, threshold, severity, confidence in seeded_rules:
            exists = db.query(BusinessRule).filter(BusinessRule.name == rule_name, BusinessRule.machine_type == machine_type).first()
            if not exists:
                db.add(
                    BusinessRule(
                        name=rule_name,
                        machine_type=machine_type,
                        metric=metric,
                        operator=operator,
                        threshold=threshold,
                        severity=severity,
                        confidence=confidence,
                    )
                )

        for machine in db.query(Machine).filter(Machine.asset_node_id.is_(None), Machine.site.isnot(None)).all():
            machine.asset_node = ensure_asset_path(
                db,
                site=machine.site,
                zone=machine.zone,
                line=machine.line,
                component=machine.component,
            )

        db.commit()
    finally:
        db.close()
