import time
import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.config import Settings
from app.models.user import User, ApiKey, UserRole
from app.models.task import Task, TaskStatus
from app.models.document import Document
from app.models.workflow import Workflow
from app.services.recovery_service import TaskRecoveryService
from app.services.document_service import DocumentService
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    hash_api_key,
    generate_raw_api_key,
)

# In-memory database for isolated, reproducible test runs
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestPhase5Suite(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=test_engine)
        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)

    # =========================================================================
    # MODULE 1: AUTHENTICATION, PASSWORD HASHING & RBAC
    # =========================================================================
    def test_user_registration_and_password_hashing(self):
        """User passwords must be securely hashed with PBKDF2; never stored in plaintext."""
        payload = {
            "username": "alice_secops",
            "email": "alice@mesh.internal",
            "password": "SuperSecretPassword123!",
            "role": "operator",
        }
        res = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["username"], "alice_secops")

        # Verify password in DB is hashed
        user_in_db = self.db.query(User).filter(User.username == "alice_secops").first()
        self.assertIsNotNone(user_in_db)
        self.assertTrue(user_in_db.hashed_password.startswith("pbkdf2_sha256$"))
        self.assertNotIn("SuperSecretPassword123!", user_in_db.hashed_password)

        # Verify password verification works
        self.assertTrue(verify_password("SuperSecretPassword123!", user_in_db.hashed_password))
        self.assertFalse(verify_password("WrongPassword!", user_in_db.hashed_password))

    def test_jwt_access_token_creation_and_expiration(self):
        """JWT tokens must be verifiable, sign with HS256, and reject expired tokens."""
        token = create_access_token({"sub": "user_123", "role": "admin"})
        decoded = decode_access_token(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["sub"], "user_123")
        self.assertEqual(decoded["role"], "admin")

        # Expired token rejection
        expired_token = create_access_token({"sub": "user_expired"}, expires_delta=timedelta(seconds=-10))
        self.assertIsNone(decode_access_token(expired_token))

        # Tampered token rejection
        tampered_token = token[:-4] + "fake"
        self.assertIsNone(decode_access_token(tampered_token))

    def test_api_key_generation_and_hashing(self):
        """API Keys must be cryptographically hashed for database storage; raw key returned once."""
        user = User(
            id="user_bot",
            username="bot_agent",
            email="bot@mesh.internal",
            hashed_password=hash_password("BotSecret!"),
            role="operator",
        )
        self.db.add(user)
        self.db.commit()

        # Login to get JWT
        login_res = self.client.post("/api/v1/auth/login", json={"username": "bot_agent", "password": "BotSecret!"})
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()["access_token"]

        # Create API key
        key_res = self.client.post(
            "/api/v1/auth/api-keys",
            json={"name": "CI Deployment Key", "expires_in_days": 15},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(key_res.status_code, 201)
        key_data = key_res.json()
        raw_key = key_data["raw_api_key"]
        self.assertTrue(raw_key.startswith("mesh_sk_"))

        # Verify key is stored as digest in DB
        db_key = self.db.query(ApiKey).filter(ApiKey.id == key_data["id"]).first()
        self.assertEqual(db_key.key_hash, hash_api_key(raw_key))
        self.assertNotIn(raw_key, db_key.key_hash)

        # Authenticate using X-API-Key
        me_res = self.client.get("/api/v1/auth/me", headers={"X-API-Key": raw_key})
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["username"], "bot_agent")

    # =========================================================================
    # MODULE 1 & 7: TENANT & RESOURCE OWNERSHIP ISOLATION
    # =========================================================================
    def test_cross_user_tenant_isolation_tasks(self):
        """User B must be strictly forbidden (403) from reading or mutating User A's missions."""
        user_a = User(id="user_a", username="user_a", email="a@mesh.internal", hashed_password="h", role="operator")
        user_b = User(id="user_b", username="user_b", email="b@mesh.internal", hashed_password="h", role="operator")
        self.db.add_all([user_a, user_b])

        task_a = Task(id="task_a_secret", user_id="user_a", goal="Deploy proprietary quantum model", status=TaskStatus.RUNNING)
        self.db.add(task_a)
        self.db.commit()

        # 1. User A can view their own task
        res_a = self.client.get(f"/api/v1/tasks/{task_a.id}", headers={"X-User-ID": "user_a"})
        self.assertEqual(res_a.status_code, 200)

        # 2. User B cannot view User A's task -> 403 Forbidden
        res_b = self.client.get(f"/api/v1/tasks/{task_a.id}", headers={"X-User-ID": "user_b"})
        self.assertEqual(res_b.status_code, 403)
        self.assertIn("access denied", res_b.json()["detail"].lower())

        # 3. User B cannot cancel User A's task -> 403 Forbidden
        cancel_b = self.client.post(f"/api/v1/tasks/{task_a.id}/cancel", headers={"X-User-ID": "user_b"})
        self.assertEqual(cancel_b.status_code, 403)

    def test_cross_user_tenant_isolation_documents(self):
        """Knowledge document searches must strictly scope to the authenticated user's workspace."""
        # User A ingests private documents
        doc_a, _ = DocumentService.upload_document(
            db=self.db,
            user_id="user_a",
            workspace_id="ws_a",
            filename="user_a_private_financials.txt",
            raw_bytes=b"Q3 Revenue target is $10M with EBITDA margin of 35%. Restricted.",
            mime_type="text/plain",
        )
        self.assertIsNotNone(doc_a)

        # 1. User A search finds citation
        res_a = DocumentService.search_knowledge_base(self.db, user_id="user_a", query="revenue target", limit=3)
        self.assertGreater(len(res_a.citations), 0)

        # 2. User B search must return ZERO results from User A's documents
        res_b = DocumentService.search_knowledge_base(self.db, user_id="user_b", query="revenue target", limit=3)
        self.assertEqual(len(res_b.citations), 0)

    # =========================================================================
    # MODULE 1 & 9: RATE LIMITING & SECURITY HEADERS
    # =========================================================================
    def test_security_headers_present(self):
        """All HTTP responses must carry standard production security headers."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(res.headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertIn("X-Correlation-ID", res.headers)

    def test_rate_limiter_blocks_burst_abuse(self):
        """Rapid bursts on sensitive endpoints must trigger HTTP 429 Too Many Requests."""
        # Login endpoint has limit = 15
        exceeded = False
        for _ in range(25):
            res = self.client.post("/api/v1/auth/login", json={"username": "fake", "password": "bad"})
            if res.status_code == 429:
                exceeded = True
                self.assertIn("Retry-After", res.headers)
                break
        self.assertTrue(exceeded, "Rate limiter did not block excessive login attempts.")

    # =========================================================================
    # MODULE 5: RELIABLE BACKGROUND EXECUTION & STUCK JOB SWEEPER
    # =========================================================================
    def test_stuck_job_recovery_sweeper(self):
        """Stalled running tasks past the heartbeat timeout must be automatically marked FAILED."""
        old_time = datetime.now(timezone.utc) - timedelta(minutes=45)
        stuck_task = Task(
            id="stuck_mission_1",
            user_id="sandip_sah",
            goal="Hanging mission after node termination",
            status=TaskStatus.RUNNING,
            current_step=4,
        )
        self.db.add(stuck_task)
        self.db.commit()

        # Artificially set updated_at in past
        self.db.query(Task).filter(Task.id == "stuck_mission_1").update({"updated_at": old_time})
        self.db.commit()

        # Run sweeper with 30-min threshold (1800s)
        swept = TaskRecoveryService.sweep_stuck_tasks(self.db, timeout_seconds=1800)
        self.assertEqual(swept, 1)

        refreshed = self.db.query(Task).filter(Task.id == "stuck_mission_1").first()
        self.assertEqual(refreshed.status, TaskStatus.FAILED)
        self.assertIn("timed out", refreshed.error_message.lower())

    def test_task_cancellation(self):
        """Active tasks can be cancelled gracefully by the owner."""
        task = Task(id="cancel_mission_1", user_id="sandip_sah", goal="Mission to abort", status=TaskStatus.RUNNING)
        self.db.add(task)
        self.db.commit()

        ok, msg = TaskRecoveryService.cancel_task(self.db, "cancel_mission_1", "sandip_sah")
        self.assertTrue(ok)
        refreshed = self.db.query(Task).filter(Task.id == "cancel_mission_1").first()
        self.assertEqual(refreshed.status, TaskStatus.CANCELLED)

    # =========================================================================
    # MODULE 2: PRODUCTION CONFIGURATION VALIDATION
    # =========================================================================
    def test_production_readiness_configuration_validation(self):
        """Production configuration must fail-fast if debug is active or default secrets are used."""
        insecure_prod = Settings(
            APP_ENV="production",
            APP_DEBUG=True,  # Insecure!
            JWT_SECRET_KEY="mesh_insecure_development_secret_change_in_production",
        )
        with self.assertRaises(ValueError) as ctx:
            insecure_prod.validate_production_readiness()
        self.assertIn("APP_DEBUG", str(ctx.exception))

        insecure_secret = Settings(
            APP_ENV="production",
            APP_DEBUG=False,
            JWT_SECRET_KEY="mesh_insecure_development_secret_change_in_production",  # Insecure default!
        )
        with self.assertRaises(ValueError) as ctx2:
            insecure_secret.validate_production_readiness()
        self.assertIn("JWT_SECRET_KEY", str(ctx2.exception))
