import pytest
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
from app.config import Settings
from app.llm.ollama_llm import OllamaLLMProvider
from app.llm.base import LLMProviderError


@pytest.fixture(scope="module")
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Seed test users
    db = TestingSessionLocal()
    admin = User(
        id="user_admin_p7",
        username="admin_p7",
        email="admin_p7@mesh.test",
        hashed_password=hash_password("adminpass123"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    operator_a = User(
        id="user_op_a_p7",
        username="operator_a_p7",
        email="op_a_p7@mesh.test",
        hashed_password=hash_password("operatora123"),
        role=UserRole.OPERATOR.value,
        is_active=True,
    )
    operator_b = User(
        id="user_op_b_p7",
        username="operator_b_p7",
        email="op_b_p7@mesh.test",
        hashed_password=hash_password("operatorb123"),
        role=UserRole.OPERATOR.value,
        is_active=True,
    )
    viewer_c = User(
        id="user_viewer_c_p7",
        username="viewer_c_p7",
        email="viewer_c_p7@mesh.test",
        hashed_password=hash_password("viewerc123"),
        role=UserRole.VIEWER.value,
        is_active=True,
    )
    db.add_all([admin, operator_a, operator_b, viewer_c])
    db.commit()

    yield TestingSessionLocal, engine

    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    TestingSessionLocal, _ = test_db

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestPhase7ProductionConfigSecurity:
    """Stage 4 & Stage 2: Configuration fail-fast validation."""

    def test_production_readiness_rejects_debug(self):
        s = Settings(
            APP_ENV="production",
            APP_DEBUG=True,
            JWT_SECRET_KEY="a" * 32,
            REQUIRE_AUTH=True,
            ALLOWED_ORIGINS="http://localhost:5173",
            DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/db",
        )
        with pytest.raises(ValueError, match="APP_DEBUG must be False in production"):
            s.validate_production_readiness()

    def test_production_readiness_rejects_default_jwt_secret(self):
        s = Settings(
            APP_ENV="production",
            APP_DEBUG=False,
            JWT_SECRET_KEY="mesh_insecure_development_secret_change_in_production",
            REQUIRE_AUTH=True,
            ALLOWED_ORIGINS="http://localhost:5173",
            DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/db",
        )
        with pytest.raises(ValueError, match="JWT_SECRET_KEY must be configured"):
            s.validate_production_readiness()

    def test_production_readiness_rejects_missing_require_auth(self):
        s = Settings(
            APP_ENV="production",
            APP_DEBUG=False,
            JWT_SECRET_KEY="super_secure_production_secret_32_chars",
            REQUIRE_AUTH=False,
            ALLOWED_ORIGINS="http://localhost:5173",
            DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/db",
        )
        with pytest.raises(ValueError, match="REQUIRE_AUTH must be True in production"):
            s.validate_production_readiness()

    def test_production_readiness_rejects_sqlite_database(self):
        s = Settings(
            APP_ENV="production",
            APP_DEBUG=False,
            JWT_SECRET_KEY="super_secure_production_secret_32_chars",
            REQUIRE_AUTH=True,
            ALLOWED_ORIGINS="http://localhost:5173",
            DATABASE_URL="sqlite:///./prod.db",
        )
        with pytest.raises(ValueError, match="SQLite database is strictly forbidden in production"):
            s.validate_production_readiness()

    def test_production_readiness_rejects_wildcard_cors(self):
        s = Settings(
            APP_ENV="production",
            APP_DEBUG=False,
            JWT_SECRET_KEY="super_secure_production_secret_32_chars",
            REQUIRE_AUTH=True,
            ALLOWED_ORIGINS="*",
            DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/db",
        )
        with pytest.raises(ValueError, match="Wildcard '\\*' CORS origin is strictly forbidden in production"):
            s.validate_production_readiness()


class TestPhase7ApiKeySecurityAndRevocation:
    """Stage 2: API-key expiration, revocation, and deletion."""

    def test_api_key_expiration_enforced(self, client, test_db):
        TestingSessionLocal, _ = test_db
        db = TestingSessionLocal()
        raw_key = "mesh_sk_expired_test_key_12345"
        key_hash = hash_api_key(raw_key)

        # Create expired API key (expired 1 hour ago)
        expired_key = ApiKey(
            id="key_expired_p7",
            user_id="user_op_a_p7",
            key_hash=key_hash,
            name="Expired Key",
            is_active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.add(expired_key)
        db.commit()
        db.close()

        # Request with expired API key should be rejected with 401
        resp = client.get("/api/v1/auth/me", headers={"X-API-Key": raw_key})
        assert resp.status_code == 401
        assert "API key has expired" in resp.json()["detail"]

    def test_api_key_revocation_lifecycle(self, client, test_db):
        TestingSessionLocal, _ = test_db
        db = TestingSessionLocal()
        raw_key = "mesh_sk_revocable_key_99999"
        key_hash = hash_api_key(raw_key)

        active_key = ApiKey(
            id="key_to_revoke_p7",
            user_id="user_op_a_p7",
            key_hash=key_hash,
            name="Revocable Key",
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(active_key)
        db.commit()
        db.close()

        # 1. Key works before revocation
        token_a = create_access_token({"sub": "user_op_a_p7", "role": "operator"})
        headers_a = {"Authorization": f"Bearer {token_a}"}

        resp = client.get("/api/v1/auth/me", headers={"X-API-Key": raw_key})
        assert resp.status_code == 200

        # 2. Operator A revokes their key
        rev_resp = client.post("/api/v1/auth/api-keys/key_to_revoke_p7/revoke", headers=headers_a)
        assert rev_resp.status_code == 200
        assert rev_resp.json()["is_active"] is False

        # 3. Key is now rejected with 401
        after_resp = client.get("/api/v1/auth/me", headers={"X-API-Key": raw_key})
        assert after_resp.status_code == 401
        assert "Invalid or deactivated API key" in after_resp.json()["detail"]

        # 4. Operator A permanently deletes the key
        del_resp = client.delete("/api/v1/auth/api-keys/key_to_revoke_p7", headers=headers_a)
        assert del_resp.status_code == 204

    def test_cannot_revoke_other_tenant_api_key(self, client, test_db):
        TestingSessionLocal, _ = test_db
        db = TestingSessionLocal()
        raw_key = "mesh_sk_tenant_a_key_88888"
        k = ApiKey(
            id="key_tenant_a_p7",
            user_id="user_op_a_p7",
            key_hash=hash_api_key(raw_key),
            name="Tenant A Key",
            is_active=True,
        )
        db.add(k)
        db.commit()
        db.close()

        # Operator B attempts to revoke Operator A's key -> 403 Forbidden
        token_b = create_access_token({"sub": "user_op_b_p7", "role": "operator"})
        resp = client.post(
            "/api/v1/auth/api-keys/key_tenant_a_p7/revoke",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 403
        assert "Forbidden" in resp.json()["detail"]


class TestPhase7RoleAndMutationGates:
    """Stage 2: Viewer role restricted from mutating tools & templates."""

    def test_viewer_cannot_execute_tools_directly(self, client):
        token_viewer = create_access_token({"sub": "user_viewer_c_p7", "role": "viewer"})
        resp = client.post(
            "/api/v1/tools/execute",
            headers={"Authorization": f"Bearer {token_viewer}"},
            json={"tool_name": "calculator", "arguments": {"expression": "2+2"}},
        )
        assert resp.status_code == 403
        assert "Forbidden" in resp.json()["detail"]

    def test_operator_can_execute_tools(self, client):
        token_op = create_access_token({"sub": "user_op_a_p7", "role": "operator"})
        resp = client.post(
            "/api/v1/tools/execute",
            headers={"Authorization": f"Bearer {token_op}"},
            json={"tool_name": "calculator", "arguments": {"expression": "2+2"}},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_viewer_cannot_import_templates(self, client):
        token_viewer = create_access_token({"sub": "user_viewer_c_p7", "role": "viewer"})
        resp = client.post(
            "/api/v1/templates/import",
            headers={"Authorization": f"Bearer {token_viewer}"},
            json={"template_json": '{"name": "test", "template_type": "workflow", "definition": {}}'},
        )
        assert resp.status_code == 403
        assert "Forbidden" in resp.json()["detail"]


class TestPhase7CrossTenantIsolation:
    """Stage 3: Cross-tenant schedule, metric, and workflow isolation."""

    def test_cannot_schedule_other_tenant_workflow(self, client, test_db):
        TestingSessionLocal, _ = test_db
        db = TestingSessionLocal()

        # Create workflow owned by Operator A
        wf_a = Workflow(
            id="wf_owned_by_a_p7",
            user_id="user_op_a_p7",
            workspace_id="ws_a",
            name="Confidential A Workflow",
            version=1,
            is_enabled=True,
            definition={"nodes": [], "edges": []},
        )
        db.add(wf_a)
        db.commit()
        db.close()

        # Operator B attempts to schedule Operator A's workflow
        token_b = create_access_token({"sub": "user_op_b_p7", "role": "operator"})
        resp = client.post(
            "/api/v1/schedules",
            headers={"Authorization": f"Bearer {token_b}"},
            json={
                "name": "Unauthorized B Schedule",
                "goal": "Trigger A workflow",
                "schedule_type": "recurring",
                "cron_expression": "0 12 * * *",
                "workflow_id": "wf_owned_by_a_p7",
            },
        )
        assert resp.status_code == 403
        assert "Forbidden" in resp.json()["detail"]

    def test_fleet_metrics_tenant_scoped(self, client, test_db):
        TestingSessionLocal, _ = test_db
        db = TestingSessionLocal()

        # Add tasks for Operator A and Operator B
        task_a = Task(
            id="task_a_metric_p7",
            goal="Goal A",
            user_id="user_op_a_p7",
            status=TaskStatus.COMPLETED,
            token_usage=1200,
            estimated_cost_usd=0.05,
        )
        task_b = Task(
            id="task_b_metric_p7",
            goal="Goal B",
            user_id="user_op_b_p7",
            status=TaskStatus.COMPLETED,
            token_usage=2500,
            estimated_cost_usd=0.10,
        )
        db.add_all([task_a, task_b])
        db.commit()
        db.close()

        # Operator A queries fleet metrics -> should only see task A (1 task, 1200 tokens)
        token_a = create_access_token({"sub": "user_op_a_p7", "role": "operator"})
        resp_a = client.get("/api/v1/metrics/fleet", headers={"Authorization": f"Bearer {token_a}"})
        assert resp_a.status_code == 200
        data_a = resp_a.json()
        assert data_a["total_tasks"] == 1
        assert data_a["total_tokens"] == 1200

        # Operator B queries fleet metrics -> should only see task B (1 task, 2500 tokens)
        token_b = create_access_token({"sub": "user_op_b_p7", "role": "operator"})
        resp_b = client.get("/api/v1/metrics/fleet", headers={"Authorization": f"Bearer {token_b}"})
        assert resp_b.status_code == 200
        data_b = resp_b.json()
        assert data_b["total_tasks"] == 1
        assert data_b["total_tokens"] == 2500

    def test_agent_metrics_tenant_isolation(self, client, test_db):
        TestingSessionLocal, _ = test_db
        db = TestingSessionLocal()

        # Create subtask under Operator A task
        st_a = Subtask(
            id="subtask_a_p7",
            task_id="task_a_metric_p7",
            order_index=0,
            title="A Subtask",
            description="Subtask for A",
            assigned_agent="planner_agent_p7",
            status=SubtaskStatus.COMPLETED,
        )
        # Create agent for Operator B with same slug
        ag_b = CustomAgent(
            id="agent_b_p7",
            user_id="user_op_b_p7",
            workspace_id="ws_b",
            name="Planner Agent",
            slug="planner_agent_p7",
            role="planner",
            system_prompt="Test prompt",
            model_provider="mock",
            model_name="test",
        )
        db.add_all([st_a, ag_b])
        db.commit()
        db.close()

        # Operator B requests metrics for their agent -> should NOT count Operator A's subtask!
        token_b = create_access_token({"sub": "user_op_b_p7", "role": "operator"})
        resp = client.get("/api/v1/agents/agent_b_p7/metrics", headers={"Authorization": f"Bearer {token_b}"})
        assert resp.status_code == 200
        assert resp.json()["total_runs"] == 0  # 0 runs for Operator B!


class TestPhase7OllamaInferenceGuarantees:
    """Stage 5: Real Ollama error handling and no mock fallback."""

    def test_unreachable_ollama_raises_llm_provider_error(self):
        provider = OllamaLLMProvider(
            base_url="http://127.0.0.1:9998",
            model_name="llama3",
            timeout=1.5,
        )
        with pytest.raises(LLMProviderError) as exc_info:
            provider.generate("Test prompt")
        # Ensure it failed cleanly with provider error and did not return mock data
        assert "Ollama request timed out" in str(exc_info.value) or "communication failure" in str(exc_info.value)
