import pytest
import os
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole, ApiKey
from app.models.task import Task, TaskStatus
from app.models.workflow import Workflow
from app.models.memory import AgentMemory
from app.models.document import Document
from app.auth.security import hash_password, hash_api_key, create_access_token
from app.config import get_settings
from app.tools.file_ops import FileReadTool, FileWriteTool, WORKSPACE_ROOT
from app.tools.http_get import validate_target_url, is_prohibited_ip


@pytest.fixture(scope="module")
def p9_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    admin = User(
        id="user_admin_p9",
        username="admin_p9",
        email="admin_p9@mesh.test",
        hashed_password=hash_password("adminpass123"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    op_a = User(
        id="user_op_a_p9",
        username="operator_a_p9",
        email="op_a_p9@mesh.test",
        hashed_password=hash_password("operatora123"),
        role=UserRole.OPERATOR.value,
        is_active=True,
    )
    op_b = User(
        id="user_op_b_p9",
        username="operator_b_p9",
        email="op_b_p9@mesh.test",
        hashed_password=hash_password("operatorb123"),
        role=UserRole.OPERATOR.value,
        is_active=True,
    )
    viewer_c = User(
        id="user_viewer_c_p9",
        username="viewer_c_p9",
        email="viewer_c_p9@mesh.test",
        hashed_password=hash_password("viewerc123"),
        role=UserRole.VIEWER.value,
        is_active=True,
    )
    db.add_all([admin, op_a, op_b, viewer_c])
    db.commit()

    # Active, revoked, and expired API keys for op_a
    raw_key_active = "mesh_sec_p9_active_12345"
    key_active = ApiKey(
        id="key_active_p9",
        user_id=op_a.id,
        key_hash=hash_api_key(raw_key_active),
        name="Active Key",
        is_active=True,
    )
    raw_key_revoked = "mesh_sec_p9_revoked_12345"
    key_revoked = ApiKey(
        id="key_revoked_p9",
        user_id=op_a.id,
        key_hash=hash_api_key(raw_key_revoked),
        name="Revoked Key",
        is_active=False,
    )
    raw_key_expired = "mesh_sec_p9_expired_12345"
    key_expired = ApiKey(
        id="key_expired_p9",
        user_id=op_a.id,
        key_hash=hash_api_key(raw_key_expired),
        name="Expired Key",
        is_active=True,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
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
def p9_client(p9_db):
    def override_get_db():
        session = p9_db["session_factory"]()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ==============================================================================
# 1. JWT & API KEY AUDIT
# ==============================================================================

def test_jwt_signature_and_expiration(p9_client, p9_db):
    # Expired token
    expired = create_access_token({"sub": p9_db["op_a"].id, "role": "operator"}, expires_delta=timedelta(seconds=-5))
    resp = p9_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401

    # Tampered signature
    valid = create_access_token({"sub": p9_db["op_a"].id, "role": "operator"})
    tampered = valid[:-4] + "FAIL"
    resp2 = p9_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert resp2.status_code == 401


def test_api_key_expiration_and_revocation(p9_client, p9_db):
    # Revoked key
    resp = p9_client.get("/api/v1/auth/me", headers={"X-API-Key": p9_db["raw_key_revoked"]})
    assert resp.status_code == 401
    assert "Invalid or deactivated" in resp.json()["detail"]

    # Expired key
    resp2 = p9_client.get("/api/v1/auth/me", headers={"X-API-Key": p9_db["raw_key_expired"]})
    assert resp2.status_code == 401
    assert "expired" in resp2.json()["detail"].lower()


# ==============================================================================
# 2. ROLE RESTRICTIONS ON EVERY MUTATION ENDPOINT
# ==============================================================================

def test_viewer_role_restrictions_across_all_mutations(p9_client, p9_db):
    token = create_access_token({"sub": p9_db["viewer_c"].id, "role": "viewer"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Tasks
    r1 = p9_client.post("/api/v1/tasks", headers=headers, json={"goal": "Viewer task test"})
    assert r1.status_code == 403

    # 2. Workflows
    r2 = p9_client.post(
        "/api/v1/workflows",
        headers=headers,
        json={
            "name": "Viewer Workflow",
            "definition": {
                "nodes": [
                    {"id": "n1", "type": "start", "label": "Start", "x": 0, "y": 0, "config": {}},
                    {"id": "n2", "type": "end", "label": "End", "x": 100, "y": 0, "config": {}},
                ],
                "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
            },
        },
    )
    assert r2.status_code == 403

    # 3. Agents
    r3 = p9_client.post(
        "/api/v1/agents",
        headers=headers,
        json={
            "name": "Viewer Agent",
            "role": "executor",
            "system_prompt": "Authorized test assistant agent.",
            "permitted_tools": [],
        },
    )
    assert r3.status_code == 403

    # 4. Documents
    r4 = p9_client.post(
        "/api/v1/documents/text",
        headers=headers,
        json={"filename": "doc.txt", "content": "Sample content"},
    )
    assert r4.status_code == 403

    # 5. Memories
    r5 = p9_client.post(
        "/api/v1/memories",
        headers=headers,
        json={"key": "mem_1", "content": "Knowledge content"},
    )
    assert r5.status_code == 403

    # 6. Schedules
    r6 = p9_client.post(
        "/api/v1/schedules",
        headers=headers,
        json={"name": "Nightly Schedule", "goal": "Run nightly maintenance", "cron_expression": "0 0 * * *"},
    )
    assert r6.status_code == 403

    # 7. Direct Tool Execution
    r7 = p9_client.post(
        "/api/v1/tools/execute",
        headers=headers,
        json={"tool_name": "calculator", "arguments": {"expression": "2+2"}},
    )
    assert r7.status_code == 403


# ==============================================================================
# 3. TENANT ISOLATION ACROSS PROTECTED RESOURCES
# ==============================================================================

def test_tenant_isolation_tasks_workflows_and_schedules(p9_client, p9_db):
    db = p9_db["db"]

    # Resource belonging to Operator A
    task_a = Task(id="task_p9_tenant_a", user_id=p9_db["op_a"].id, goal="Op A secret task", status=TaskStatus.COMPLETED)
    wf_a = Workflow(
        id="wf_p9_tenant_a",
        user_id=p9_db["op_a"].id,
        name="Op A Workflow",
        description="Private workflow",
        is_enabled=True,
    )
    mem_a = AgentMemory(
        id="mem_p9_tenant_a",
        user_id=p9_db["op_a"].id,
        key="secret_strategy_a",
        content="Proprietary method A",
        memory_type="workspace",
    )
    db.add_all([task_a, wf_a, mem_a])
    db.commit()

    token_b = create_access_token({"sub": p9_db["op_b"].id, "role": "operator"})
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Op B cannot access Op A's task
    resp_task = p9_client.get(f"/api/v1/tasks/{task_a.id}", headers=headers_b)
    assert resp_task.status_code == 403

    # Op B cannot delete Op A's task
    del_task = p9_client.delete(f"/api/v1/tasks/{task_a.id}", headers=headers_b)
    assert del_task.status_code == 403

    # Op B cannot schedule Op A's workflow
    resp_sched = p9_client.post(
        "/api/v1/schedules",
        headers=headers_b,
        json={
            "name": "Unauthorized Schedule",
            "goal": "Schedule another tenant's workflow",
            "cron_expression": "0 0 * * *",
            "workflow_id": wf_a.id,
        },
    )
    assert resp_sched.status_code == 403
    assert "another tenant" in resp_sched.json()["detail"].lower()

    # Op B cannot delete Op A's memory
    del_mem = p9_client.delete(f"/api/v1/memories/{mem_a.id}", headers=headers_b)
    assert del_mem.status_code in (403, 404)


# ==============================================================================
# 4. PATH TRAVERSAL & SSRF PROTECTIONS
# ==============================================================================

def test_path_traversal_defenses():
    read_tool = FileReadTool()
    write_tool = FileWriteTool()

    # Traversal via parent directory
    r1 = read_tool.run(file_path="../../etc/passwd")
    assert not r1.success
    assert "Security Violation" in r1.error

    r2 = write_tool.run(file_path="../unauthorized.txt", content="payload")
    assert not r2.success
    assert "Security Violation" in r2.error


def test_ssrf_prohibited_ips_and_hostnames():
    # Loopback IP
    assert is_prohibited_ip("127.0.0.1") is True
    # Private IP
    assert is_prohibited_ip("192.168.1.10") is True
    assert is_prohibited_ip("10.0.0.1") is True
    # Link local / metadata
    assert is_prohibited_ip("169.254.169.254") is True

    # Validate target URL throws on blocked hostname / protocol
    with pytest.raises((ValueError, PermissionError)):
        validate_target_url("http://169.254.169.254/latest/meta-data/")

    with pytest.raises((ValueError, PermissionError)):
        validate_target_url("http://localhost:8000/api/v1/admin")

    with pytest.raises((ValueError, PermissionError)):
        validate_target_url("ftp://example.com/file")


# ==============================================================================
# 5. ERROR SANITIZATION & STRICT PRODUCTION AUTH
# ==============================================================================

def test_production_auth_strict_enforcement(p9_client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "REQUIRE_AUTH", True)

    # Request without auth
    resp = p9_client.get("/api/v1/tasks")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]

    # Request with bypass header alone
    resp_bypass = p9_client.get("/api/v1/tasks", headers={"X-User-ID": "bypass_user"})
    assert resp_bypass.status_code == 401
