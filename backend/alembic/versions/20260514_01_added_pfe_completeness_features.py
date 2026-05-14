"""Added PFE completeness features

Revision ID: 20260514_01
Revises: 20260424_01
Create Date: 2026-05-14 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260514_01"
down_revision = "20260424_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_reset_required", sa.Boolean(), nullable=True, server_default=sa.text("false")))

    op.add_column("maintenance_interventions", sa.Column("priority", sa.String(length=20), nullable=True, server_default="medium"))
    op.add_column("maintenance_interventions", sa.Column("planned_at", sa.DateTime(), nullable=True))
    op.add_column("maintenance_interventions", sa.Column("parts_used", sa.Text(), nullable=True))
    op.add_column("maintenance_interventions", sa.Column("estimated_cost", sa.Float(), nullable=True, server_default="0"))

    op.create_table(
        "ingestion_job_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["ingestion_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_ingestion_job_logs_id"), "ingestion_job_logs", ["id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.String(length=80), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(op.f("ix_ingestion_job_logs_id"), table_name="ingestion_job_logs")
    op.drop_table("ingestion_job_logs")

    op.drop_column("maintenance_interventions", "estimated_cost")
    op.drop_column("maintenance_interventions", "parts_used")
    op.drop_column("maintenance_interventions", "planned_at")
    op.drop_column("maintenance_interventions", "priority")
    op.drop_column("users", "password_reset_required")
