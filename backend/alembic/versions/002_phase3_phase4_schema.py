"""phase 3 and 4 multi-agent, memory, workflows, schedules, documents

Revision ID: 002_phase3_phase4_schema
Revises: 001_initial_schema
Create Date: 2026-10-23 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_phase3_phase4_schema"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update tasks table with user_id, workspace_id, current_stage
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=64), server_default="sandip_sah", nullable=False))
        batch_op.add_column(sa.Column("workspace_id", sa.String(length=64), server_default="default_workspace", nullable=False))
        batch_op.add_column(sa.Column("current_stage", sa.String(length=32), server_default="planner", nullable=False))

    # 2. Update subtasks table with stage, dependencies, retry_count
    with op.batch_alter_table("subtasks") as batch_op:
        batch_op.add_column(sa.Column("stage", sa.String(length=32), server_default="pending", nullable=True))
        batch_op.add_column(sa.Column("dependencies", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False))

    # 3. Create execution_events table
    op.create_table(
        "execution_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("agent_name", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="SUCCESS"),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_execution_events_task_id", "execution_events", ["task_id"])
    op.create_index("ix_execution_events_event_type", "execution_events", ["event_type"])

    # 4. Create agent_memories table
    op.create_table(
        "agent_memories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("mission_id", sa.String(length=36), nullable=True),
        sa.Column("memory_type", sa.String(length=32), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_memories_user_id", "agent_memories", ["user_id"])
    op.create_index("ix_agent_memories_key", "agent_memories", ["key"])

    # 5. Create agents table
    op.create_table(
        "agents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("permitted_tools", sa.JSON(), nullable=True),
        sa.Column("model_provider", sa.String(length=32), server_default="ollama", nullable=False),
        sa.Column("model_name", sa.String(length=64), server_default="llama3", nullable=False),
        sa.Column("temperature", sa.Float(), server_default="0.2", nullable=False),
        sa.Column("max_steps", sa.Integer(), server_default="10", nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("review_policy", sa.String(length=32), server_default="standard", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("total_runs", sa.Integer(), server_default="0", nullable=False),
        sa.Column("successful_runs", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agents_slug", "agents", ["slug"])
    op.create_index("ix_agents_user_id", "agents", ["user_id"])

    # 6. Create workflows, workflow_versions, workflow_runs
    op.create_table(
        "workflows",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("version_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("active_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("total_runs", sa.Integer(), server_default="0", nullable=False),
        sa.Column("successful_runs", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workflows_slug", "workflows", ["slug"])

    op.create_table(
        "workflow_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workflow_id", sa.String(length=36), sa.ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workflow_versions_wf_ver", "workflow_versions", ["workflow_id", "version_number"], unique=True)

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workflow_id", sa.String(length=36), sa.ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("current_node_id", sa.String(length=64), nullable=True),
        sa.Column("node_states", sa.JSON(), nullable=True),
        sa.Column("inputs", sa.JSON(), nullable=True),
        sa.Column("outputs", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_workflow_runs_workflow_id", "workflow_runs", ["workflow_id"])

    # 7. Create workflow_schedules, schedule_executions
    op.create_table(
        "workflow_schedules",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=36), sa.ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("schedule_type", sa.String(length=32), nullable=False),
        sa.Column("cron_expression", sa.String(length=64), nullable=True),
        sa.Column("timezone_str", sa.String(length=64), server_default="UTC", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("allow_overlap", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "schedule_executions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("schedule_id", sa.String(length=36), sa.ForeignKey("workflow_schedules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), unique=True, nullable=False),
        sa.Column("status", sa.String(length=32), server_default="RUNNING", nullable=False),
        sa.Column("scheduled_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    # 8. Create documents, document_chunks
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=16), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PROCESSED", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 9. Create notifications table
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=16), server_default="INFO", nullable=False),
        sa.Column("category", sa.String(length=32), server_default="MISSION", nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("action_url", sa.String(length=255), nullable=True),
        sa.Column("dedup_key", sa.String(length=128), unique=True, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 10. Create templates table
    op.create_table(
        "templates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=64), unique=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=64), server_default="MESH System", nullable=False),
        sa.Column("version", sa.String(length=16), server_default="1.0.0", nullable=False),
        sa.Column("is_built_in", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("workflow_definition", sa.JSON(), nullable=False),
        sa.Column("default_inputs", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("downloads_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("templates")
    op.drop_table("notifications")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("schedule_executions")
    op.drop_table("workflow_schedules")
    op.drop_table("workflow_runs")
    op.drop_table("workflow_versions")
    op.drop_table("workflows")
    op.drop_table("agents")
    op.drop_table("agent_memories")
    op.drop_table("execution_events")
    with op.batch_alter_table("subtasks") as batch_op:
        batch_op.drop_column("retry_count")
        batch_op.drop_column("dependencies")
        batch_op.drop_column("stage")
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("current_stage")
        batch_op.drop_column("workspace_id")
        batch_op.drop_column("user_id")
