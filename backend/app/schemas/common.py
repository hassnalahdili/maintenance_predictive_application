from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.domain import MACHINE_TYPES, RISK_LEVELS, USER_ROLES, normalize_machine_type, normalize_role


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caracteres")
    if not any(char.isupper() for char in password):
        raise ValueError("Le mot de passe doit contenir une majuscule")
    if not any(char.islower() for char in password):
        raise ValueError("Le mot de passe doit contenir une minuscule")
    if not any(char.isdigit() for char in password):
        raise ValueError("Le mot de passe doit contenir un chiffre")
    return password


class UserSummary(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    password_reset_required: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


class PasswordResetRequest(BaseModel):
    new_password: str
    require_change_on_login: bool = True

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str
    role: str = "viewer"

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        normalized = normalize_role(value)
        if normalized not in USER_ROLES:
            raise ValueError("Role invalide")
        return normalized


class UserUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str | None = None
    role: str
    is_active: bool = True

    @field_validator("password")
    @classmethod
    def validate_optional_password(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return validate_password_strength(value)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        normalized = normalize_role(value)
        if normalized not in USER_ROLES:
            raise ValueError("Role invalide")
        return normalized


class UserOut(UserSummary):
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    password_reset_required: bool = False


class MachineBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    machine_type: str
    asset_node_id: int | None = None
    site: str | None = Field(default=None, max_length=120)
    zone: str | None = Field(default=None, max_length=120)
    line: str | None = Field(default=None, max_length=120)
    component: str | None = Field(default=None, max_length=120)
    status: str = "healthy"
    notes: str | None = None

    @field_validator("machine_type")
    @classmethod
    def validate_machine_type(cls, value: str) -> str:
        normalized = normalize_machine_type(value)
        if normalized not in MACHINE_TYPES:
            raise ValueError("Type de machine invalide")
        return normalized


class MachineCreate(MachineBase):
    pass


class MachineUpdate(MachineBase):
    pass


class MachineOut(BaseModel):
    id: int
    name: str
    machine_type: str
    asset_node_id: int | None = None
    site: str | None
    zone: str | None = None
    line: str | None = None
    component: str | None = None
    asset_path: str | None = None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RuleBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    machine_type: str
    metric: str
    operator: str
    threshold: float
    duration_seconds: int = 0
    severity: str = "medium"
    confidence: float = 0.8

    @field_validator("machine_type")
    @classmethod
    def validate_machine_type(cls, value: str) -> str:
        normalized = normalize_machine_type(value)
        if normalized not in MACHINE_TYPES:
            raise ValueError("Type de machine invalide")
        return normalized

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, value: str) -> str:
        if value not in {">", ">=", "<", "<=", "=="}:
            raise ValueError("Operateur invalide")
        return value

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        if value not in {"low", "medium", "high", "critical"}:
            raise ValueError("Severite invalide")
        return value

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("La confiance doit etre comprise entre 0 et 1")
        return value

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, value: str) -> str:
        if value not in {"temperature", "vibration_x", "vibration_y", "vibration_z", "pressure", "rpm", "current"}:
            raise ValueError("Metrique invalide")
        return value


class RuleCreate(RuleBase):
    pass


class RuleUpdate(RuleBase):
    is_active: bool = True


class RuleOut(BaseModel):
    id: int
    name: str
    machine_type: str
    metric: str
    operator: str
    threshold: float
    duration_seconds: int
    severity: str
    confidence: float
    is_active: bool
    version: int
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RuleVersionOut(BaseModel):
    id: int
    version: int
    snapshot: str
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuleSimulationMatch(BaseModel):
    sensor_id: int
    machine_id: int
    timestamp: datetime
    metric_value: float


class RuleSimulationOut(BaseModel):
    rule_id: int
    total_records: int
    matched_records: int
    match_rate: float
    latest_matches: list[RuleSimulationMatch]


class SensorDataCreate(BaseModel):
    machine_id: int
    timestamp: datetime | None = None
    temperature: float
    vibration_x: float
    vibration_y: float
    vibration_z: float
    pressure: float
    rpm: float
    current: float


class SensorDataOut(BaseModel):
    id: int
    machine_id: int
    timestamp: datetime
    temperature: float
    vibration_x: float
    vibration_y: float
    vibration_z: float
    pressure: float
    rpm: float
    current: float

    model_config = ConfigDict(from_attributes=True)


class AlertAcknowledge(BaseModel):
    comment: str | None = None


class AlertOut(BaseModel):
    id: int
    machine_id: int
    machine_name: str | None = None
    level: str
    message: str
    probability: float | None = None
    acknowledged: bool
    acknowledgment_comment: str | None
    status: str
    escalated: bool = False
    escalated_at: datetime | None = None
    created_at: datetime


class PredictionOut(BaseModel):
    id: int
    machine_id: int
    machine_name: str | None = None
    timestamp: datetime
    failure_probability: float
    remaining_useful_life_days: float
    expected_failure_date: datetime | None
    alert_level: str
    active_rules: str | None
    prediction_source: str


class MachineDetailOut(MachineOut):
    sensor_history: list[SensorDataOut]
    prediction_history: list[PredictionOut]
    alert_history: list[AlertOut]
    interventions: list["MaintenanceInterventionOut"]


class DashboardTrendPoint(BaseModel):
    timestamp: datetime
    average_probability: float
    max_probability: float


class DashboardSensorSnapshot(BaseModel):
    timestamp: datetime
    temperature: float
    vibration_total: float
    pressure: float
    rpm: float
    current: float


class DashboardProbabilityPoint(BaseModel):
    timestamp: datetime
    value: float


class DashboardMachineHealth(BaseModel):
    machine_id: int
    machine_name: str
    machine_type: str
    site: str | None
    status: str
    alert_level: str
    failure_probability: float
    remaining_useful_life_days: float | None = None
    current_sensor_values: DashboardSensorSnapshot | None = None
    sensor_trend: list[DashboardSensorSnapshot] = Field(default_factory=list)
    probability_trend: list[DashboardProbabilityPoint] = Field(default_factory=list)
    timestamp: datetime | None = None


class DashboardSummaryOut(BaseModel):
    total_machines: int
    active_alerts: int
    machines_at_risk: int
    status_distribution: dict[str, int]
    risk_distribution: dict[str, int]
    prediction_trend: list[DashboardTrendPoint]
    machine_health: list[DashboardMachineHealth]
    available_types: list[str]
    available_sites: list[str]
    last_updated_at: datetime


class AuditLogOut(BaseModel):
    id: int
    user_id: int | None = None
    user_name: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    ip_address: str | None = None
    details: str | None = None
    created_at: datetime


class DashboardFilters(BaseModel):
    machine_type: str | None = None
    risk_level: str | None = None
    site: str | None = None

    @field_validator("machine_type")
    @classmethod
    def validate_machine_type(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        normalized = normalize_machine_type(value)
        if normalized not in MACHINE_TYPES:
            raise ValueError("Type de machine invalide")
        return normalized

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        value = value.strip().lower()
        if value not in RISK_LEVELS:
            raise ValueError("Niveau de risque invalide")
        return value


class ReplaySourceOut(BaseModel):
    source_id: str
    display_name: str
    machine_type: str
    description: str
    row_count: int
    cursor: int
    completed: bool


class ReplayStepRequest(BaseModel):
    source_id: str
    machine_id: int
    steps: int = Field(default=1, ge=1, le=50)
    reset: bool = False


class ReplayStepOut(BaseModel):
    source_id: str
    machine_id: int
    machine_name: str | None = None
    machine_type: str
    injected_rows: int
    cursor: int
    completed: bool
    latest_timestamp: datetime | None = None
    latest_prediction: PredictionOut | None = None


class AssetNodeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    node_type: str
    parent_id: int | None = None

    @field_validator("node_type")
    @classmethod
    def validate_node_type(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if len(normalized) < 2 or len(normalized) > 30:
            raise ValueError("Type de noeud invalide")
        return normalized


class AssetNodeUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    node_type: str
    parent_id: int | None = None

    @field_validator("node_type")
    @classmethod
    def validate_node_type(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if len(normalized) < 2 or len(normalized) > 30:
            raise ValueError("Type de noeud invalide")
        return normalized


class AssetNodeOut(BaseModel):
    id: int
    name: str
    node_type: str
    parent_id: int | None = None
    path: str | None = None
    machine_count: int = 0
    child_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AssetTreeNode(BaseModel):
    id: int
    name: str
    node_type: str
    children: list["AssetTreeNode"] = Field(default_factory=list)


class MaintenanceInterventionBase(BaseModel):
    machine_id: int
    alert_id: int | None = None
    technician_id: int | None = None
    work_order: str | None = Field(default=None, max_length=80)
    category: str = "inspection"
    priority: str = "medium"
    status: str = "open"
    root_cause: str | None = None
    action_taken: str | None = None
    parts_used: str | None = None
    estimated_cost: float = Field(default=0, ge=0)
    outcome_label: str = "under_analysis"
    downtime_minutes: int = Field(default=0, ge=0)
    planned_at: datetime | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None

    @field_validator("status")
    @classmethod
    def validate_intervention_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"open", "in_progress", "resolved", "cancelled"}:
            raise ValueError("Statut d'intervention invalide")
        return normalized

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"low", "medium", "high", "critical"}:
            raise ValueError("Priorite invalide")
        return normalized

    @field_validator("outcome_label")
    @classmethod
    def validate_outcome_label(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"under_analysis", "confirmed_failure", "false_alarm", "preventive_maintenance", "sensor_fault"}:
            raise ValueError("Label terrain invalide")
        return normalized


class MaintenanceInterventionCreate(MaintenanceInterventionBase):
    pass


class MaintenanceInterventionUpdate(MaintenanceInterventionBase):
    machine_id: int | None = None


class MaintenanceInterventionOut(BaseModel):
    id: int
    machine_id: int
    machine_name: str | None = None
    alert_id: int | None = None
    technician_id: int | None = None
    technician_name: str | None = None
    work_order: str | None = None
    category: str
    priority: str = "medium"
    status: str
    root_cause: str | None = None
    action_taken: str | None = None
    parts_used: str | None = None
    estimated_cost: float = 0
    outcome_label: str
    downtime_minutes: int
    planned_at: datetime | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class IngestionJobCreate(BaseModel):
    machine_id: int
    mode: str = "simulator"
    source_id: str | None = None
    interval_seconds: int = Field(default=5, ge=1, le=300)
    replay_steps: int = Field(default=1, ge=1, le=50)
    drift: bool = False
    auto_restart: bool = True

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"simulator", "replay"}:
            raise ValueError("Mode d'ingestion invalide")
        return normalized


class IngestionJobUpdate(BaseModel):
    interval_seconds: int | None = Field(default=None, ge=1, le=300)
    replay_steps: int | None = Field(default=None, ge=1, le=50)
    drift: bool | None = None
    auto_restart: bool | None = None
    is_active: bool | None = None


class IngestionJobOut(BaseModel):
    id: int
    machine_id: int
    machine_name: str | None = None
    machine_type: str | None = None
    mode: str
    source_id: str | None = None
    interval_seconds: int
    replay_steps: int
    drift: bool
    auto_restart: bool
    is_active: bool
    last_run_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class IngestionJobLogOut(BaseModel):
    id: int
    job_id: int
    event_type: str
    level: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    severity: str
    entity_type: str | None = None
    entity_id: str | None = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DriftMetricOut(BaseModel):
    feature: str
    baseline_mean: float
    recent_mean: float
    delta: float
    drift_ratio: float
    status: str


class DriftReportOut(BaseModel):
    generated_at: datetime
    sample_size: int
    baseline_size: int
    status: str
    metrics: list[DriftMetricOut]


class RetrainRequest(BaseModel):
    horizon_hours: int = Field(default=72, ge=1, le=720)
    minimum_samples: int = Field(default=30, ge=10, le=5000)


class RetrainReportOut(BaseModel):
    generated_at: datetime
    dataset_size: int
    positive_labels: int
    negative_labels: int
    best_model: str
    primary_metric: str
    metrics: dict[str, float]
    labels_breakdown: dict[str, int]
    report_path: str


class CalibrationBinOut(BaseModel):
    bin_label: str
    count: int
    average_confidence: float
    observed_frequency: float


class FeatureImportanceOut(BaseModel):
    feature: str
    importance: float
    normalized_importance: float


class BusinessMetricsOut(BaseModel):
    generated_at: datetime
    total_alerts: int
    active_alerts: int
    acknowledged_rate: float
    escalation_rate: float
    resolved_intervention_rate: float
    false_alert_rate: float
    confirmed_failure_rate: float
    mean_downtime_minutes: float
    mean_resolution_hours: float
    mean_lead_time_hours: float
    failure_coverage_rate: float


class ModelDiagnosticsOut(BaseModel):
    generated_at: datetime
    model_name: str
    calibration_method: str | None = None
    calibration_before: dict[str, float]
    calibration_after: dict[str, float]
    calibration_bins: list[CalibrationBinOut]
    global_importance: list[FeatureImportanceOut]
    business_metrics: BusinessMetricsOut

    model_config = ConfigDict(protected_namespaces=())


class PredictionContributionOut(BaseModel):
    feature: str
    value: float
    baseline: float
    contribution: float


class PredictionExplanationOut(BaseModel):
    machine_id: int
    machine_name: str | None = None
    machine_type: str
    timestamp: datetime
    failure_probability: float
    alert_level: str
    active_rules: list[str]
    calibration_method: str | None = None
    top_positive: list[PredictionContributionOut]
    top_negative: list[PredictionContributionOut]
    ranked_features: list[PredictionContributionOut]
    global_importance: list[FeatureImportanceOut]


AssetTreeNode.model_rebuild()
MachineDetailOut.model_rebuild()
