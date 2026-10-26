import pytest
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole, ApiKey
from app.models.task import Task, Subtask, TaskStatus, SubtaskStatus
from app.models.workflow import Workflow
from app.models.agent import CustomAgent
from app.auth.security import hash_password, hash_api_key, create_access_token
from app.config import get_settings
from app.services.recovery_service import TaskRecoveryService
from app.agents.graph import build_multi_agent_graph


@pytest.fixture(scope="module")
def p8_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    admin = User(
        id="user_admin_p8",
        username="admin_p8",
        email="admin_p8@mesh.test",
        hashed_password=hash_password("adminpass123"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    op_a = User(
        id="user_op_a_p8",
        username="operator_a_p8",
        email="op_a_p8@mesh.test",
        hashed_password=hash_password("operatora123"),
        role=UserRole.OPERATOR.value,
        is_active=True,
    )
    op_b = User(
        id="user_op_b_p8",
        username="operator_b_p8",
        email="op_b_p8@mesh.test",
        hashed_password=hash_password("operatorb123"),
        role=UserRole.OPERATOR.value,
        is_active=True,
    )
    viewer_c = User(
        id="user_viewer_c_p8",
        username="viewer_c_p8",
        email="viewer_c_p8@mesh.test",
        hashed_password=hash_password("viewerc123"),
        role=UserRole.VIEWER.value,
        is_active=True,
    )
    db.add_all([admin, op_a, op_b, viewer_c])
    db.commit()

    # Active API key for op_a
    raw_key_active = "mesh_sec_op_a_active_key_12345"
    key_active = ApiKey(
        id="key_active_p8",
        user_id=op_a.id,
        key_hash=hash_api_key(raw_key_active),
        name="Active Key",
        is_active=True,
    )
    # Revoked API key for op_a
    raw_key_revoked = "mesh_sec_op_a_revoked_key_12345"
    key_revoked = ApiKey(
        id="key_revoked_p8",
        user_id=op_a.id,
        key_hash=hash_api_key(raw_key_revoked),
        name="Revoked Key",
        is_active=False,
    )
    # Expired API key for op_a
    raw_key_expired = "mesh_sec_op_a_expired_key_12345"
    key_expired = ApiKey(
        id="key_expired_p8",
        user_id=op_a.id,
        key_hash=hash_api_key(raw_key_expired),
        name="Expired Key",
        is_active=True,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    db.add_all([key_active, key_revoked, key_expired])
    db.commit()

    yield {
        "db": db,
        "session_factory": TestingSessionLocal,
        "admin": admin,
        "op_a": op_a,
        "op_b": op_b,
        "viewer_c": viewer_c,
        "raw_key_active": raw_key_active,
        "raw_key_revoked": raw_key_revoked,
        "raw_key_expired": raw_key_expired,
    }
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def p8_client(p8_db):
    def override_get_db():
        session = p8_db["session_factory"]()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ==============================================================================
# STAGE 4: AUTHENTICATION & TENANT ISOLATION TESTS
# ==============================================================================

def test_jwt_tampered_signature_rejected(p8_client, p8_db):
    token = create_access_token({"sub": p8_db["op_a"].id, "role": "operator"})
    # Tamper with signature part
    tampered_token = token[:-5] + "XXXXX"
    resp = p8_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401
    assert "Invalid or expired access token" in resp.json()["detail"]


def test_jwt_expired_token_rejected(p8_client, p8_db):
    expired_token = create_access_token(
        {"sub": p8_db["op_a"].id, "role": "operator"},
        expires_delta=timedelta(seconds=-10),
    )
    resp = p8_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401


def test_jwt_malformed_token_rejected(p8_client):
    resp = p8_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid-token"})
    assert resp.status_code == 401


def test_api_key_inactive_rejected(p8_client, p8_db):
    resp = p8_client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": p8_db["raw_key_revoked"]},
    )
    assert resp.status_code == 401
    assert "Invalid or deactivated" in resp.json()["detail"]


def test_api_key_expired_rejected(p8_client, p8_db):
    resp = p8_client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": p8_db["raw_key_expired"]},
    )
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_api_key_active_authenticated(p8_client, p8_db):
    resp = p8_client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": p8_db["raw_key_active"]},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "operator_a_p8"


def test_viewer_role_cannot_create_task(p8_client, p8_db):
    token = create_access_token({"sub": p8_db["viewer_c"].id, "role": "viewer"})
    resp = p8_client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"goal": "Viewer task creation test"},
    )
    assert resp.status_code == 403


def test_viewer_role_cannot_create_workflow(p8_client, p8_db):
    token = create_access_token({"sub": p8_db["viewer_c"].id, "role": "viewer"})
    resp = p8_client.post(
        "/api/v1/workflows",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Viewer Workflow",
            "definition": {
                "nodes": [
                    {"id": "node-1", "type": "start", "label": "Start", "x": 0, "y": 0, "config": {}},
                    {"id": "node-2", "type": "end", "label": "End", "x": 100, "y": 0, "config": {}},
                ],
                "edges": [
                    {"id": "edge-1", "source": "node-1", "target": "node-2"},
                ],
            },
        },
    )
    assert resp.status_code == 403


def test_viewer_role_cannot_create_agent(p8_client, p8_db):
    token = create_access_token({"sub": p8_db["viewer_c"].id, "role": "viewer"})
    resp = p8_client.post(
        "/api/v1/agents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Viewer Agent",
            "role": "executor",
            "system_prompt": "You are an authorized test executor agent.",
            "permitted_tools": ["calculator"],
        },
    )
    assert resp.status_code == 403


def test_cross_tenant_task_access_denied(p8_client, p8_db):
    # Create task belonging to User A
    db = p8_db["db"]
    task_a = Task(
        id="task_p8_tenant_a",
        user_id=p8_db["op_a"].id,
        goal="Secret mission for Tenant A",
        status=TaskStatus.COMPLETED,
    )
    db.add(task_a)
    db.commit()

    # User B attempts to access User A's task
    token_b = create_access_token({"sub": p8_db["op_b"].id, "role": "operator"})
    resp = p8_client.get(f"/api/v1/tasks/{task_a.id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]

    # User B attempts to delete User A's task
    del_resp = p8_client.delete(f"/api/v1/tasks/{task_a.id}", headers={"Authorization": f"Bearer {token_b}"})
    assert del_resp.status_code == 403

    # Admin CAN access User A's task
    token_admin = create_access_token({"sub": p8_db["admin"].id, "role": "admin"})
    admin_resp = p8_client.get(f"/api/v1/tasks/{task_a.id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert admin_resp.status_code == 200
    assert admin_resp.json()["goal"] == "Secret mission for Tenant A"


def test_cross_tenant_audit_logs_denied(p8_client, p8_db):
    # User B attempts to query audit logs for User A's task
    token_b = create_access_token({"sub": p8_db["op_b"].id, "role": "operator"})
    resp = p8_client.get(
        "/api/v1/audit-logs?task_id=task_p8_tenant_a",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 200
    # Tenant isolation filters to zero logs for tasks not owned by user
    assert resp.json()["total"] == 0


def test_prod_mode_rejects_x_user_id_dev_header(p8_client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "REQUIRE_AUTH", True)
    resp = p8_client.get(
        "/api/v1/auth/me",
        headers={"X-User-ID": "bypass_attempt_user"},
    )
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


# ==============================================================================
# STAGE 6: APPROVAL, CANCELLATION, SWEEPER & LIMIT TESTS
# ==============================================================================

def test_task_cancellation_lifecycle(p8_client, p8_db):
    db = p8_db["db"]
    c_task = Task(
        id="task_p8_to_cancel",
        user_id=p8_db["op_a"].id,
        goal="Task to test cancellation",
        status=TaskStatus.RUNNING,
    )
    db.add(c_task)
    db.commit()

    token_a = create_access_token({"sub": p8_db["op_a"].id, "role": "operator"})
    resp = p8_client.post(
        f"/api/v1/tasks/{c_task.id}/cancel",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"

    # Verify task in DB is CANCELLED
    db.refresh(c_task)
    assert c_task.status == TaskStatus.CANCELLED

    # Cancelling again returns 400
    resp2 = p8_client.post(
        f"/api/v1/tasks/{c_task.id}/cancel",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp2.status_code == 400
    assert "terminal state" in resp2.json()["detail"]


def test_viewer_cannot_approve_task(p8_client, p8_db):
    db = p8_db["db"]
    wait_task = Task(
        id="task_p8_wait_app",
        user_id=p8_db["viewer_c"].id,
        goal="Task paused at approval",
        status=TaskStatus.WAITING_APPROVAL,
    )
    db.add(wait_task)
    db.commit()

    token_viewer = create_access_token({"sub": p8_db["viewer_c"].id, "role": "viewer"})
    resp = p8_client.post(
        f"/api/v1/tasks/{wait_task.id}/approve",
        headers={"Authorization": f"Bearer {token_viewer}"},
        json={"approved": True, "feedback": "Viewer trying to approve"},
    )
    assert resp.status_code == 403
    assert "viewer" in resp.json()["detail"].lower()


def test_stale_task_recovery_sweeper(p8_db):
    db = p8_db["db"]
    # Task stuck in RUNNING for 2 hours (past 1800s threshold)
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=7200)
    stale_task = Task(
        id="task_p8_stale_runner",
        user_id=p8_db["op_a"].id,
        goal="Stale worker task",
        status=TaskStatus.RUNNING,
        updated_at=stale_time,
    )
    db.add(stale_task)
    db.commit()

    swept = TaskRecoveryService.sweep_stuck_tasks(db, timeout_seconds=1800)
    assert swept >= 1

    db.refresh(stale_task)
    assert stale_task.status == TaskStatus.FAILED
    assert "timed out" in stale_task.error_message


def test_active_task_not_swept(p8_db):
    db = p8_db["db"]
    # Task running with recent heartbeat (30 seconds ago)
    recent_time = datetime.now(timezone.utc) - timedelta(seconds=30)
    active_task = Task(
        id="task_p8_active_runner",
        user_id=p8_db["op_a"].id,
        goal="Active healthy worker task",
        status=TaskStatus.RUNNING,
        updated_at=recent_time,
    )
    db.add(active_task)
    db.commit()

    swept = TaskRecoveryService.sweep_stuck_tasks(db, timeout_seconds=1800)
    db.refresh(active_task)
    assert active_task.status == TaskStatus.RUNNING
