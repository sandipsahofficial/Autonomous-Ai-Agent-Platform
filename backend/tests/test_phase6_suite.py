import time
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app as fastapi_app
from app.database import Base, get_db
import app.models  # Ensure all model tables are registered in Base.metadata
from app.models.user import User, UserRole, ApiKey
from app.models.task import Task, Subtask, ExecutionEvent, TaskStatus, SubtaskStatus
from app.models.workflow import Workflow, WorkflowRun
from app.models.document import Document
from app.models.audit import AuditLog
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    hash_api_key,
    generate_raw_api_key,
)
from app.services.recovery_service import TaskRecoveryService
from app.tools.calculator import CalculatorTool
from app.tools.http_get import validate_target_url, ApprovedHttpGetTool

# Isolated in-memory SQLite database using StaticPool for shared memory across threads/sessions
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


fastapi_app.dependency_overrides[get_db] = override_get_db
client = TestClient(fastapi_app)


@pytest.fixture(autouse=True)
def setup_test_db():
    fastapi_app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=TEST_ENGINE)
    db = TestingSessionLocal()
    # Seed standard users
    admin_user = User(
        id="user_admin",
        username="admin_user",
        email="admin@mesh.test",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    operator_user = User(
        id="user_operator",
        username="operator_user",
        email="operator@mesh.test",
        hashed_password=hash_password("OperatorPass123!"),
        role=UserRole.OPERATOR.value,
        is_active=True,
    )
    viewer_user = User(
        id="user_viewer",
        username="viewer_user",
        email="viewer@mesh.test",
        hashed_password=hash_password("ViewerPass123!"),
        role=UserRole.VIEWER.value,
        is_active=True,
    )
    other_tenant = User(
        id="user_other_tenant",
        username="other_tenant",
        email="other@mesh.test",
        hashed_password=hash_password("OtherPass123!"),
        role=UserRole.OPERATOR.value,
        is_active=True,
    )
    db.add_all([admin_user, operator_user, viewer_user, other_tenant])
    db.commit()
    yield
    db.close()
    Base.metadata.drop_all(bind=TEST_ENGINE)


class TestPhase6SecuritySuite:
    """
    Phase 6 Comprehensive Security, Auth, RBAC, Tenant Isolation, and Sweeper Verification.
    """

    # --- 1. Authentication & Cryptography Tests ---

    def test_jwt_signature_and_expiration_enforcement(self):
        token = create_access_token({"sub": "user_operator", "role": "operator"}, expires_delta=timedelta(seconds=2))
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user_operator"
        assert payload["role"] == "operator"

        # Test expiration
        time.sleep(2.1)
        expired_payload = decode_access_token(token)
        assert expired_payload is None, "Expired JWT token must be rejected"

    def test_jwt_tampered_signature_and_alg_none_rejection(self):
        token = create_access_token({"sub": "user_operator", "role": "operator"})
        parts = token.split(".")
        # Tamper payload
        tampered_token = f"{parts[0]}.eyJhZG1pbiI6dHJ1ZX0.{parts[2]}"
        assert decode_access_token(tampered_token) is None, "Tampered JWT payload must be rejected"

        # Tamper algorithm to 'none'
        import base64
        import json
        header_none = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
        token_none = f"{header_none}.{parts[1]}."
        assert decode_access_token(token_none) is None, "alg:none token must be rejected"

    def test_production_auth_gate_blocks_x_user_id_bypass(self):
        # When REQUIRE_AUTH is True, X-User-ID alone must NOT grant access
        from app.config import get_settings
        settings = get_settings()
        original_require_auth = getattr(settings, "REQUIRE_AUTH", False)
        try:
            settings.REQUIRE_AUTH = True
            resp = client.get("/api/v1/auth/me", headers={"X-User-ID": "admin_user"})
            assert resp.status_code == 401, "Production gate must reject X-User-ID header without token"
        finally:
            settings.REQUIRE_AUTH = original_require_auth

    # --- 2. Role-Based Access Control (RBAC) Tests ---

    def test_viewer_role_cannot_approve_tasks(self):
        db = TestingSessionLocal()
        task_waiting = Task(
            id="task_waiting_approval_1",
            user_id="user_operator",
            goal="Deploy production update",
            status=TaskStatus.WAITING_APPROVAL,
        )
        db.add(task_waiting)
        db.commit()
        db.close()

        token = create_access_token({"sub": "user_viewer", "role": "viewer"})
        resp = client.post(
            "/api/v1/tasks/task_waiting_approval_1/approve",
            json={"approved": True, "feedback": "Approved"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, "Viewer role must be barred from approving actions"

    def test_viewer_role_cannot_mutate_workflows_or_agents(self):
        token = create_access_token({"sub": "user_viewer", "role": "viewer"})
        # Attempt to create agent
        resp_agent = client.post(
            "/api/v1/agents",
            json={
                "name": "Malicious Agent",
                "role": "executor",
                "system_prompt": "You are a specialized agent executing user instructions.",
                "permitted_tools": ["calculator"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_agent.status_code == 403, "Viewer role cannot create agents"

        # Attempt to create workflow
        resp_wf = client.post(
            "/api/v1/workflows",
            json={
                "name": "Viewer Pipeline",
                "definition": {
                    "nodes": [{"id": "n1", "type": "start", "label": "Start"}],
                    "edges": [],
                },
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_wf.status_code == 403, "Viewer role cannot create workflows"

    # --- 3. Multi-Tenant Data Isolation Tests ---

    def test_cross_user_tenant_isolation_tasks_and_runs(self):
        db = TestingSessionLocal()
        # Seed Task and WorkflowRun for operator 1
        task_a = Task(
            id="task_owned_by_op1",
            user_id="user_operator",
            goal="Private Financial Summary",
            status=TaskStatus.RUNNING,
            current_stage="executor",
        )
        wf_a = Workflow(
            id="wf_owned_by_op1",
            user_id="user_operator",
            name="Private Financial Pipeline",
            definition={"nodes": [], "edges": []},
        )
        run_a = WorkflowRun(
            id="run_owned_by_op1",
            workflow_id="wf_owned_by_op1",
            user_id="user_operator",
            version=1,
            status="RUNNING",
        )
        db.add_all([task_a, wf_a, run_a])
        db.commit()
        db.close()

        # Other tenant attempts to read task A
        other_token = create_access_token({"sub": "user_other_tenant", "role": "operator"})
        resp = client.get(
            "/api/v1/tasks/task_owned_by_op1",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 403, "Other tenant must receive 403 Forbidden for another's task"

        # Other tenant attempts to step workflow run A
        resp_step = client.post(
            "/api/v1/workflows/runs/run_owned_by_op1/step?node_id=step_1",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp_step.status_code == 403, "Other tenant must receive 403 Forbidden stepping another's run"

    def test_cross_user_tenant_isolation_audit_logs(self):
        db = TestingSessionLocal()
        task_a = Task(
            id="task_tenant_alpha",
            user_id="user_operator",
            goal="Alpha Goal",
            status=TaskStatus.COMPLETED,
        )
        audit_entry = AuditLog(
            id="audit_alpha_1",
            task_id="task_tenant_alpha",
            agent_name="executor",
            action_type="TOOL_EXECUTION",
            risk_level="MEDIUM",
            payload={"secret_value": "confidential_financial_data"},
        )
        db.add_all([task_a, audit_entry])
        db.commit()
        db.close()

        # Other tenant requests audit logs
        other_token = create_access_token({"sub": "user_other_tenant", "role": "operator"})
        resp = client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0, "Non-admin tenant must not see another tenant's audit logs"

        # Owner operator requests audit logs
        owner_token = create_access_token({"sub": "user_operator", "role": "operator"})
        resp_owner = client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp_owner.status_code == 200
        assert resp_owner.json()["total"] == 1, "Owner must view their own audit logs"

    # --- 4. Recovery Sweeper & Concurrency Tests ---

    def test_stuck_task_recovery_sweeper_transitions_only_stale_tasks(self):
        db = TestingSessionLocal()
        old_time = datetime.now(timezone.utc) - timedelta(minutes=45)
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)

        stale_task = Task(
            id="stale_task_1",
            user_id="user_operator",
            goal="Stale mission",
            status=TaskStatus.RUNNING,
            updated_at=old_time,
        )
        active_task = Task(
            id="active_task_1",
            user_id="user_operator",
            goal="Active mission",
            status=TaskStatus.RUNNING,
            updated_at=recent_time,
        )
        waiting_approval_task = Task(
            id="waiting_task_1",
            user_id="user_operator",
            goal="Waiting approval mission",
            status=TaskStatus.WAITING_APPROVAL,
            updated_at=old_time,
        )
        completed_task = Task(
            id="completed_task_1",
            user_id="user_operator",
            goal="Completed mission",
            status=TaskStatus.COMPLETED,
            updated_at=old_time,
        )
        db.add_all([stale_task, active_task, waiting_approval_task, completed_task])
        db.commit()

        recovered = TaskRecoveryService.sweep_stuck_tasks(db, timeout_seconds=1800)
        assert recovered == 1, "Only the stale running task must be swept"

        db.refresh(stale_task)
        db.refresh(active_task)
        db.refresh(waiting_approval_task)
        db.refresh(completed_task)

        assert stale_task.status == TaskStatus.FAILED
        assert "no worker heartbeat recorded" in stale_task.error_message
        assert active_task.status == TaskStatus.RUNNING, "Recently active task must NOT be swept"
        assert waiting_approval_task.status == TaskStatus.WAITING_APPROVAL, "HITL approval task must NEVER be swept"
        assert completed_task.status == TaskStatus.COMPLETED, "Completed task must NOT be altered"
        db.close()

    # --- 5. Tool Safety, AST & SSRF Security Tests ---

    def test_ast_calculator_blocks_malicious_eval(self):
        calc = CalculatorTool()
        res_safe = calc.run("40 + 2")
        assert res_safe.success is True
        assert res_safe.output["result"] == 42.0

        res_malicious = calc.run("__import__('os').system('echo pwned')")
        assert res_malicious.success is False
        assert "Calculation failed" in res_malicious.error

        res_eval = calc.run("eval('2 + 2')")
        assert res_eval.success is False
        assert "Calculation failed" in res_eval.error

    def test_ssrf_validator_blocks_metadata_and_loopback(self):
        with pytest.raises(PermissionError):
            validate_target_url("http://127.0.0.1:8000/admin")

        with pytest.raises(PermissionError):
            validate_target_url("http://169.254.169.254/latest/meta-data")

        with pytest.raises(PermissionError):
            validate_target_url("http://metadata.google.internal/computeMetadata/v1")

    # --- 6. End-to-End Mission Scenario (Stage 9) ---

    def test_e2e_mission_lifecycle_with_approval_rejection_and_isolation(self):
        from unittest.mock import patch
        from app.api.tasks import run_agent_task_background

        # 1. Authenticate as authorized operator
        token = create_access_token({"sub": "user_operator", "role": "operator"})
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 2. Create mission with sensitive deletion requiring HITL approval
        create_resp = client.post(
            "/api/v1/tasks",
            json={"goal": "Delete sensitive logs in system"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        task_data = create_resp.json()
        task_id = task_data["id"]
        assert task_id is not None

        # 3. Execute background multi-agent graph (will reach high-risk interrupt and pause)
        with patch("app.api.tasks.SessionLocal", TestingSessionLocal):
            run_agent_task_background(task_id, "Delete sensitive logs in system")

        # 4. Verify task is paused at approval interrupt
        db = TestingSessionLocal()
        task = db.query(Task).filter(Task.id == task_id).first()
        assert task.status == TaskStatus.WAITING_APPROVAL
        db.close()

        # 5. Verify pending approval exists in API
        pending_resp = client.get("/api/v1/approvals/pending", headers=auth_headers)
        assert pending_resp.status_code == 200
        pending_data = pending_resp.json()
        pending_items = pending_data.get("approvals", [])
        matching = [p for p in pending_items if p["task_id"] == task_id]
        assert len(matching) == 1

        # 6. Reject the action and verify execution halts safely
        reject_resp = client.post(
            f"/api/v1/tasks/{task_id}/approve",
            json={"approved": False, "feedback": "Operation denied by security policy"},
            headers=auth_headers,
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["decision"] == "REJECTED"

        # 7. Verify cross-user isolation: other tenant cannot read this mission
        other_token = create_access_token({"sub": "user_other_tenant", "role": "operator"})
        other_resp = client.get(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert other_resp.status_code == 403, "Other tenant must be blocked from inspecting operator's mission"
