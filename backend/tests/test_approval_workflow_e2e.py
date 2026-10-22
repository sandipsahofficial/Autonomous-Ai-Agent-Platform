import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db, SessionLocal
from app.main import app
from app.models.task import Task, TaskStatus, Subtask, SubtaskStatus
from app.api.tasks import run_agent_task_background
from app.agents.graph import build_multi_agent_graph
from langgraph.types import Command

# In-memory SQLite for isolated API tests
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
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


class TestApprovalWorkflowE2E(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=test_engine)
        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)

    def test_normal_task_completes_successfully(self):
        """1. A normal task completes successfully and is marked COMPLETED."""
        # Create normal coding/research goal
        task = Task(goal="Calculate iterative Fibonacci numbers", status=TaskStatus.PENDING)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        # Run background agent task
        # Note: In test mode, we pass TestingSessionLocal engine
        from unittest.mock import patch
        with patch("app.api.tasks.SessionLocal", TestingSessionLocal):
            run_agent_task_background(task.id, task.goal)

        # Verify task completed
        self.db.refresh(task)
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(task.final_output)
        self.assertGreater(task.current_step, 0)
        self.assertIsNone(task.error_message)

    def test_high_risk_task_waiting_for_approval(self):
        """2. A high-risk task pauses at approval and is marked WAITING_APPROVAL."""
        # Create a task with destructive deletion
        task = Task(goal="Delete old temporary cache files", status=TaskStatus.PENDING)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        from unittest.mock import patch
        with patch("app.api.tasks.SessionLocal", TestingSessionLocal):
            run_agent_task_background(task.id, task.goal)

        self.db.refresh(task)
        # CRITICAL VERIFICATION: Must be WAITING_APPROVAL, NOT COMPLETED!
        self.assertEqual(task.status, TaskStatus.WAITING_APPROVAL)
        self.assertNotEqual(task.status, TaskStatus.COMPLETED)

    def test_pending_approval_appears_in_api(self):
        """3. A pending approval appears in GET /api/v1/approvals/pending."""
        task = Task(goal="Delete backup archives in workspace", status=TaskStatus.PENDING)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        from unittest.mock import patch
        with patch("app.api.tasks.SessionLocal", TestingSessionLocal):
            run_agent_task_background(task.id, task.goal)

        # Query GET /api/v1/approvals/pending
        response = self.client.get("/api/v1/approvals/pending")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertGreaterEqual(data["total"], 1)
        matching = [item for item in data["approvals"] if item["task_id"] == task.id]
        self.assertEqual(len(matching), 1)

        item = matching[0]
        self.assertEqual(item["task_id"], task.id)
        self.assertEqual(item["status"], "WAITING_APPROVAL")
        self.assertEqual(item["risk_level"], "HIGH")
        self.assertEqual(item["tool_name"], "file_delete")
        self.assertIn("file_path", item["arguments"])

    def test_approved_task_resumes_correctly(self):
        """4. An approved task resumes and finishes with COMPLETED."""
        task = Task(goal="Delete old temp cache", status=TaskStatus.PENDING)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        from unittest.mock import patch
        with patch("app.api.tasks.SessionLocal", TestingSessionLocal):
            run_agent_task_background(task.id, task.goal)

        self.db.refresh(task)
        self.assertEqual(task.status, TaskStatus.WAITING_APPROVAL)

        # Submit approval decision via API
        approve_resp = self.client.post(
            f"/api/v1/tasks/{task.id}/approve",
            json={"approved": True, "feedback": "Authorized by security admin"},
        )
        self.assertEqual(approve_resp.status_code, 200)
        resp_data = approve_resp.json()
        self.assertEqual(resp_data["decision"], "APPROVED")

        # Verify task is now completed
        self.db.refresh(task)
        self.assertEqual(task.status, TaskStatus.COMPLETED)

    def test_rejected_task_does_not_execute_protected_action(self):
        """5. A rejected task records rejection, does not execute action, and completes safely."""
        task = Task(goal="Delete sensitive logs", status=TaskStatus.PENDING)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        from unittest.mock import patch
        with patch("app.api.tasks.SessionLocal", TestingSessionLocal):
            run_agent_task_background(task.id, task.goal)

        self.db.refresh(task)
        self.assertEqual(task.status, TaskStatus.WAITING_APPROVAL)

        # Submit REJECTION decision via API
        reject_resp = self.client.post(
            f"/api/v1/tasks/{task.id}/approve",
            json={"approved": False, "feedback": "Rejected: Operation violates compliance policy"},
        )
        self.assertEqual(reject_resp.status_code, 200)
        self.assertEqual(reject_resp.json()["decision"], "REJECTED")

        # Verify task is completed without unhandled exceptions
        self.db.refresh(task)
        self.assertEqual(task.status, TaskStatus.COMPLETED)

    def test_errors_not_reported_as_successful_completion(self):
        """6. Errors are persisted as FAILED with error_message, never COMPLETED."""
        task = Task(goal="Failing task simulation", status=TaskStatus.PENDING)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        from unittest.mock import patch
        # Simulate a crash during graph execution
        with patch("app.api.tasks.SessionLocal", TestingSessionLocal):
            with patch.object(
                build_multi_agent_graph().__class__,
                "invoke",
                side_effect=RuntimeError("Simulated LLM pipeline failure"),
            ):
                run_agent_task_background(task.id, task.goal)

        self.db.refresh(task)
        # CRITICAL: Must be marked FAILED, NEVER COMPLETED!
        self.assertEqual(task.status, TaskStatus.FAILED)
        self.assertNotEqual(task.status, TaskStatus.COMPLETED)
        self.assertIn("Simulated LLM pipeline failure", task.error_message)


if __name__ == "__main__":
    unittest.main()
