from __future__ import annotations

from app.models.models import MaintenanceIntervention
from app.schemas.common import MaintenanceInterventionOut


def serialize_intervention(intervention: MaintenanceIntervention) -> MaintenanceInterventionOut:
    technician = intervention.technician
    machine = intervention.machine
    return MaintenanceInterventionOut(
        id=intervention.id,
        machine_id=intervention.machine_id,
        machine_name=machine.name if machine else None,
        alert_id=intervention.alert_id,
        technician_id=intervention.technician_id,
        technician_name=technician.full_name if technician else None,
        work_order=intervention.work_order,
        category=intervention.category,
        priority=intervention.priority,
        status=intervention.status,
        root_cause=intervention.root_cause,
        action_taken=intervention.action_taken,
        parts_used=intervention.parts_used,
        estimated_cost=intervention.estimated_cost or 0,
        outcome_label=intervention.outcome_label,
        downtime_minutes=intervention.downtime_minutes,
        planned_at=intervention.planned_at,
        opened_at=intervention.opened_at,
        closed_at=intervention.closed_at,
        created_at=intervention.created_at,
        updated_at=intervention.updated_at,
    )
