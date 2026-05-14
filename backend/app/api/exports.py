from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import Alert, Machine, MaintenanceIntervention, User
from app.services.export_utils import csv_response, pdf_response

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.get("/machines.csv")
def export_machines_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    machines = db.query(Machine).filter(Machine.is_deleted.is_(False)).order_by(Machine.id.asc()).all()
    return csv_response(
        "machines.csv",
        ["id", "nom", "type", "site", "zone", "ligne", "composant", "statut", "notes"],
        [
            [
                machine.id,
                machine.name,
                machine.machine_type,
                machine.site,
                machine.zone,
                machine.line,
                machine.component,
                machine.status,
                machine.notes,
            ]
            for machine in machines
        ],
    )


@router.get("/alerts.csv")
def export_alerts_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alerts = db.query(Alert).options(joinedload(Alert.machine)).order_by(Alert.created_at.desc()).limit(1000).all()
    return csv_response(
        "alertes.csv",
        ["id", "machine", "niveau", "probabilite", "statut", "accusee", "escaladee", "date", "message"],
        [
            [
                alert.id,
                alert.machine.name if alert.machine else alert.machine_id,
                alert.level,
                alert.probability,
                alert.status,
                alert.acknowledged,
                alert.escalated,
                alert.created_at,
                alert.message,
            ]
            for alert in alerts
        ],
    )


@router.get("/interventions.csv")
def export_interventions_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interventions = (
        db.query(MaintenanceIntervention)
        .options(joinedload(MaintenanceIntervention.machine), joinedload(MaintenanceIntervention.technician))
        .order_by(MaintenanceIntervention.opened_at.desc())
        .limit(1000)
        .all()
    )
    return csv_response(
        "interventions.csv",
        [
            "id",
            "machine",
            "technicien",
            "work_order",
            "priorite",
            "statut",
            "label",
            "downtime",
            "cout_estime",
            "date_prevue",
            "ouverture",
            "pieces",
        ],
        [
            [
                item.id,
                item.machine.name if item.machine else item.machine_id,
                item.technician.full_name if item.technician else item.technician_id,
                item.work_order,
                item.priority,
                item.status,
                item.outcome_label,
                item.downtime_minutes,
                item.estimated_cost,
                item.planned_at,
                item.opened_at,
                item.parts_used,
            ]
            for item in interventions
        ],
    )


@router.get("/machines/{machine_id}.pdf")
def export_machine_pdf(
    machine_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    machine = (
        db.query(Machine)
        .options(joinedload(Machine.predictions), joinedload(Machine.alerts), joinedload(Machine.interventions))
        .filter(Machine.id == machine_id, Machine.is_deleted.is_(False))
        .first()
    )
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    latest_prediction = sorted(machine.predictions, key=lambda item: item.timestamp, reverse=True)[:1]
    recent_alerts = sorted(machine.alerts, key=lambda item: item.created_at, reverse=True)[:5]
    recent_interventions = sorted(machine.interventions, key=lambda item: item.opened_at, reverse=True)[:5]
    lines = [
        f"Machine: {machine.name}",
        f"Type: {machine.machine_type}",
        f"Localisation: {machine.site or '-'} / {machine.zone or '-'} / {machine.line or '-'} / {machine.component or '-'}",
        f"Statut actuel: {machine.status}",
        f"Notes: {machine.notes or '-'}",
        "",
        "Derniere prediction:",
    ]
    if latest_prediction:
        prediction = latest_prediction[0]
        lines.extend(
            [
                f"- Date: {prediction.timestamp}",
                f"- Niveau: {prediction.alert_level}",
                f"- Probabilite: {round(prediction.failure_probability * 100)}%",
                f"- RUL: {prediction.remaining_useful_life_days} jours",
            ]
        )
    else:
        lines.append("- Aucune prediction disponible")
    lines.append("")
    lines.append("Alertes recentes:")
    lines.extend([f"- {alert.created_at}: {alert.level} / {alert.status} / {alert.message}" for alert in recent_alerts] or ["- Aucune alerte recente"])
    lines.append("")
    lines.append("Interventions recentes:")
    lines.extend(
        [
            f"- {item.opened_at}: {item.status} / {item.priority} / {item.work_order or '-'} / {item.outcome_label}"
            for item in recent_interventions
        ]
        or ["- Aucune intervention recente"]
    )
    return pdf_response(f"machine_{machine.id}.pdf", f"Rapport machine {machine.name}", lines)


@router.get("/alerts/{alert_id}.pdf")
def export_alert_pdf(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = db.query(Alert).options(joinedload(Alert.machine), joinedload(Alert.interventions)).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    lines = [
        f"Alerte #{alert.id}",
        f"Machine: {alert.machine.name if alert.machine else alert.machine_id}",
        f"Niveau: {alert.level}",
        f"Probabilite: {round((alert.probability or 0) * 100)}%",
        f"Statut: {alert.status}",
        f"Accusee: {'oui' if alert.acknowledged else 'non'}",
        f"Escaladee: {'oui' if alert.escalated else 'non'}",
        f"Date: {alert.created_at}",
        f"Message: {alert.message}",
        f"Commentaire: {alert.acknowledgment_comment or '-'}",
        "",
        "Interventions liees:",
    ]
    lines.extend(
        [
            f"- {item.opened_at}: {item.status} / {item.priority} / {item.action_taken or item.outcome_label}"
            for item in sorted(alert.interventions, key=lambda item: item.opened_at, reverse=True)
        ]
        or ["- Aucune intervention liee"]
    )
    return pdf_response(f"alerte_{alert.id}.pdf", f"Rapport alerte #{alert.id}", lines)
