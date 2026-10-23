import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.task import Task, Subtask, ExecutionEvent, TaskStatus, SubtaskStatus
from app.services.trace_service import record_execution_event

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


class TestMetricsAndTraces(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=test_engine)
        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)

    def test_fleet_metrics_empty_db(self):
        resp = self.client.get("/api/v1/metrics/fleet")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_tasks"], 0)
        self.assertEqual(data["active_tasks"], 0)
        self.assertEqual(data["completed_tasks"], 0)
        self.assertEqual(data["failed_tasks"], 0)
        self.assertEqual(data["pending_approvals"], 0)
        self.assertEqual(data["completion_rate"], 0.0)
        self.assertEqual(data["average_cost_usd"], 0.0)
        self.assertEqual(data["total_cost_usd"], 0.0)
        self.assertEqual(data["total_tokens"], 0)

    def test_fleet_metrics_calculated(self):
        db = TestingSessionLocal()
        # Task 1: COMPLETED
        t1 = Task(
            goal="Task 1",
            status=TaskStatus.COMPLETED,
            token_usage=1000,
            estimated_cost_usd=0.04,
        )
        # Task 2: FAILED
        t2 = Task(
            goal="Task 2",
            status=TaskStatus.FAILED,
            token_usage=500,
            estimated_cost_usd=0.02,
        )
        # Task 3: WAITING_APPROVAL
        t3 = Task(
            goal="Task 3",
            status=TaskStatus.WAITING_APPROVAL,
            token_usage=300,
            estimated_cost_usd=0.01,
        )
        db.add_all([t1, t2, t3])
        db.commit()
        db.close()

        resp = self.client.get("/api/v1/metrics/fleet")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_tasks"], 3)
        self.assertEqual(data["active_tasks"], 1)  # WAITING_APPROVAL is active
        self.assertEqual(data["completed_tasks"], 1)
        self.assertEqual(data["failed_tasks"], 1)
        self.assertEqual(data["pending_approvals"], 1)
        # 1 completed out of 2 finalized = 50.0%
        self.assertEqual(data["completion_rate"], 50.0)
        self.assertEqual(data["total_tokens"], 1800)
        # (0.04 + 0.02 + 0.01) / 3 = 0.0233
        self.assertAlmostEqual(data["average_cost_usd"], 0.0233, places=3)

    def test_agent_metrics_endpoint(self):
        db = TestingSessionLocal()
        # Add a subtask for researcher and coder
        t = Task(goal="Fleet Test", status=TaskStatus.RUNNING)
        db.add(t)
        db.commit()
        s1 = Subtask(
            task_id=t.id,
            order_index=0,
            title="Research",
            description="Doc lookup",
            assigned_agent="researcher",
            status=SubtaskStatus.COMPLETED,
        )
        s2 = Subtask(
            task_id=t.id,
            order_index=1,
            title="Coding",
            description="Code generation",
            assigned_agent="coder",
            status=SubtaskStatus.IN_PROGRESS,
        )
        db.add_all([s1, s2])
        db.commit()
        db.close()

        resp = self.client.get("/api/v1/metrics/agents")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_agents"], 4)
        agents = {a["assigned_agent"]: a for a in data["agents"]}
        self.assertIn("researcher", agents)
        self.assertIn("coder", agents)
        self.assertIn("planner", agents)
        self.assertIn("reviewer", agents)

        self.assertEqual(agents["researcher"]["runs"], 1)
        self.assertEqual(agents["researcher"]["success_rate"], 100.0)
        self.assertEqual(agents["coder"]["runs"], 1)
        self.assertEqual(agents["coder"]["status"], "Active")

    def test_task_traces_lifecycle(self):
        db = TestingSessionLocal()
        t = Task(goal="Trace life cycle test", status=TaskStatus.RUNNING)
        db.add(t)
        db.commit()
        db.refresh(t)
        task_id = t.id

        # Add execution events
        e1 = record_execution_event(
            task_id=task_id,
            event_type="TASK_CREATED",
            message="Task initialized",
            agent_name="system",
            step_index=0,
            db=db,
        )
        e2 = record_execution_event(
            task_id=task_id,
            event_type="TOOL_INVOKED",
            message="Invoked execute_python",
            agent_name="tool_gate",
            step_index=1,
            details={"tool": "execute_python", "risk": "LOW"},
            db=db,
        )
        db.close()

        resp = self.client.get(f"/api/v1/tasks/{task_id}/traces")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["task_id"], task_id)
        self.assertEqual(data["total_events"], 2)
        events = data["events"]
        self.assertEqual(events[0]["event_type"], "TASK_CREATED")
        self.assertEqual(events[1]["event_type"], "TOOL_INVOKED")
        self.assertEqual(events[1]["details"]["tool"], "execute_python")


if __name__ == "__main__":
    unittest.main()
