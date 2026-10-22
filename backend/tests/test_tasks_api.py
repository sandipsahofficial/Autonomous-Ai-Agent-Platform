import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Set up in-memory SQLite engine for fast, isolated tests
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


# Override application dependency
app.dependency_overrides[get_db] = override_get_db


class TestTasksAPI(unittest.TestCase):
    def setUp(self):
        """Create fresh database tables before each test."""
        Base.metadata.create_all(bind=test_engine)
        self.client = TestClient(app)

    def tearDown(self):
        """Drop all tables after each test."""
        Base.metadata.drop_all(bind=test_engine)

    def test_create_and_get_task(self):
        # 1. Create a new task
        create_payload = {"goal": "Write a Python script to calculate Fibonacci numbers"}
        response = self.client.post("/api/v1/tasks", json=create_payload)
        self.assertEqual(response.status_code, 201)
        created_data = response.json()
        task_id = created_data["id"]
        self.assertEqual(created_data["goal"], create_payload["goal"])
        self.assertEqual(created_data["status"], "PENDING")
        self.assertEqual(created_data["current_step"], 0)

        # 2. Retrieve the task by ID
        get_response = self.client.get(f"/api/v1/tasks/{task_id}")
        self.assertEqual(get_response.status_code, 200)
        fetched_data = get_response.json()
        self.assertEqual(fetched_data["id"], task_id)
        self.assertEqual(fetched_data["subtasks"], [])

    def test_add_subtasks_to_task(self):
        # 1. Create parent task
        create_response = self.client.post("/api/v1/tasks", json={"goal": "Build Fibonacci"})
        task_id = create_response.json()["id"]

        # 2. Add first subtask
        subtask_1 = {
            "order_index": 0,
            "title": "Research efficient Fibonacci implementations",
            "description": "Find iterative vs dynamic programming complexity",
            "assigned_agent": "researcher",
        }
        sub_resp = self.client.post(f"/api/v1/tasks/{task_id}/subtasks", json=subtask_1)
        self.assertEqual(sub_resp.status_code, 201)
        self.assertEqual(sub_resp.json()["assigned_agent"], "researcher")

        # 3. Add second subtask
        subtask_2 = {
            "order_index": 1,
            "title": "Implement iterative solution",
            "description": "Write Python function fibonacci(n)",
            "assigned_agent": "coder",
        }
        self.client.post(f"/api/v1/tasks/{task_id}/subtasks", json=subtask_2)

        # 4. Fetch task and verify both subtasks are present in order
        get_response = self.client.get(f"/api/v1/tasks/{task_id}")
        self.assertEqual(get_response.status_code, 200)
        task_data = get_response.json()
        self.assertEqual(len(task_data["subtasks"]), 2)
        self.assertEqual(task_data["subtasks"][0]["order_index"], 0)
        self.assertEqual(task_data["subtasks"][1]["order_index"], 1)

    def test_list_tasks(self):
        # Create two tasks
        self.client.post("/api/v1/tasks", json={"goal": "Task 1"})
        self.client.post("/api/v1/tasks", json={"goal": "Task 2"})

        response = self.client.get("/api/v1/tasks")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["tasks"]), 2)

    def test_delete_task(self):
        # Create and then delete
        create_response = self.client.post("/api/v1/tasks", json={"goal": "To be deleted"})
        task_id = create_response.json()["id"]

        del_resp = self.client.delete(f"/api/v1/tasks/{task_id}")
        self.assertEqual(del_resp.status_code, 204)

        # Verify 404
        get_resp = self.client.get(f"/api/v1/tasks/{task_id}")
        self.assertEqual(get_resp.status_code, 404)

    def test_not_found_handling(self):
        resp = self.client.get("/api/v1/tasks/non-existent-id")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
