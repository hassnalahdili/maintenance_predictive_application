"""Initial schema

Revision ID: 20260424_01
Revises:
Create Date: 2026-04-24 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260424_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("node_type", sa.String(length=30), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["asset_nodes.id"]),
    )
    op.create_index(op.f("ix_asset_nodes_id"), "asset_nodes", ["id"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=True),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "machines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("machine_type", sa.String(length=60), nullable=False),
        sa.Column("site", sa.String(length=120), nullable=True),
        sa.Column("zone", sa.String(length=120), nullable=True),
        sa.Column("line", sa.String(length=120), nullable=True),
        sa.Column("component", sa.String(length=120), nullable=True),
        sa.Column("asset_node_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=True),
        sa.Column("installation_date", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["asset_node_id"], ["asset_nodes.id"]),
    )
    op.create_index(op.f("ix_machines_id"), "machines", ["id"], unique=False)

    op.create_table(
        "business_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("machine_type", sa.String(length=60), nullable=False),
        sa.Column("metric", sa.String(length=60), nullable=False),
        sa.Column("operator", sa.String(length=10), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(op.f("ix_business_rules_id"), "business_rules", ["id"], unique=False)

    op.create_table(
        "business_rule_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.Text(), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["rule_id"], ["business_rules.id"]),
    )
    op.create_index(op.f("ix_business_rule_versions_id"), "business_rule_versions", ["id"], unique=False)

    op.create_table(
        "sensor_data",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("vibration_x", sa.Float(), nullable=False),
        sa.Column("vibration_y", sa.Float(), nullable=False),
        sa.Column("vibration_z", sa.Float(), nullable=False),
        sa.Column("pressure", sa.Float(), nullable=False),
        sa.Column("rpm", sa.Float(), nullable=False),
        sa.Column("current", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
    )
    op.create_index(op.f("ix_sensor_data_id"), "sensor_data", ["id"], unique=False)
    op.create_index(op.f("ix_sensor_data_timestamp"), "sensor_data", ["timestamp"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=True),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), nullable=True),
        sa.Column("acknowledgment_comment", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=True),
        sa.Column("escalated", sa.Boolean(), nullable=True),
        sa.Column("escalated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["business_rules.id"]),
    )
    op.create_index(op.f("ix_alerts_id"), "alerts", ["id"], unique=False)

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("failure_probability", sa.Float(), nullable=False),
        sa.Column("remaining_useful_life_days", sa.Float(), nullable=False),
        sa.Column("expected_failure_date", sa.DateTime(), nullable=True),
        sa.Column("alert_level", sa.String(length=20), nullable=False),
        sa.Column("active_rules", sa.Text(), nullable=True),
        sa.Column("prediction_source", sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
    )
    op.create_index(op.f("ix_predictions_id"), "predictions", ["id"], unique=False)
    op.create_index(op.f("ix_predictions_timestamp"), "predictions", ["timestamp"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)

    op.create_table(
        "maintenance_interventions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=True),
        sa.Column("technician_id", sa.Integer(), nullable=True),
        sa.Column("work_order", sa.String(length=80), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column("outcome_label", sa.String(length=50), nullable=True),
        sa.Column("downtime_minutes", sa.Integer(), nullable=True),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
        sa.ForeignKeyConstraint(["technician_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_maintenance_interventions_id"), "maintenance_interventions", ["id"], unique=False)

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("mode", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=True),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("replay_steps", sa.Integer(), nullable=True),
        sa.Column("drift", sa.Boolean(), nullable=True),
        sa.Column("auto_restart", sa.Boolean(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
    )
    op.create_index(op.f("ix_ingestion_jobs_id"), "ingestion_jobs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ingestion_jobs_id"), table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
    op.drop_index(op.f("ix_maintenance_interventions_id"), table_name="maintenance_interventions")
    op.drop_table("maintenance_interventions")
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_predictions_timestamp"), table_name="predictions")
    op.drop_index(op.f("ix_predictions_id"), table_name="predictions")
    op.drop_table("predictions")
    op.drop_index(op.f("ix_alerts_id"), table_name="alerts")
    op.drop_table("alerts")
    op.drop_index(op.f("ix_sensor_data_timestamp"), table_name="sensor_data")
    op.drop_index(op.f("ix_sensor_data_id"), table_name="sensor_data")
    op.drop_table("sensor_data")
    op.drop_index(op.f("ix_business_rule_versions_id"), table_name="business_rule_versions")
    op.drop_table("business_rule_versions")
    op.drop_index(op.f("ix_business_rules_id"), table_name="business_rules")
    op.drop_table("business_rules")
    op.drop_index(op.f("ix_machines_id"), table_name="machines")
    op.drop_table("machines")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_asset_nodes_id"), table_name="asset_nodes")
    op.drop_table("asset_nodes")
