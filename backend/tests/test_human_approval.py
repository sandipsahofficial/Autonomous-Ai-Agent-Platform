import unittest
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from app.agents.graph import build_multi_agent_graph
from app.agents.state import AgentState


class TestHumanApproval(unittest.TestCase):
    def test_interrupt_and_resume_approval(self):
        # 1. Build graph with dedicated MemorySaver checkpointer
        checkpointer = MemorySaver()
        graph = build_multi_agent_graph(checkpointer=checkpointer)

        thread_id = "test-thread-approval-1"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state: AgentState = {
            "task_id": thread_id,
            "goal": "Delete temporary system cache",
            "current_step": 0,
            "max_steps": 10,
            "max_rework_attempts": 2,
            "token_usage": 0,
            "estimated_cost_usd": 0.0,
            "messages": [],
            "subtasks": [
                {
                    "order_index": 0,
                    "title": "Clean temporary cache",
                    "description": "Delete old files",
                    "assigned_agent": "coder",
                }
            ],
            "current_subtask_index": 0,
            "is_completed": False,
        }

        # 2. Invoke graph - it MUST interrupt before executing high-risk file_delete
        graph.invoke(initial_state, config=config)

        # 3. Verify workflow is paused waiting for approval
        snapshot = graph.get_state(config)
        self.assertTrue(len(snapshot.next) > 0, "Graph should be paused at interrupt")

        # In LangGraph 0.2+, the interrupt payload is accessible in snapshot.tasks[0].interrupts[0].value
        interrupt_payload = snapshot.tasks[0].interrupts[0].value
        self.assertEqual(interrupt_payload["tool_name"], "file_delete")
        self.assertEqual(interrupt_payload["risk_level"], "HIGH")

        # 4. Resume workflow by submitting human approval
        resume_command = Command(resume={"approved": True, "feedback": "Approved by administrator"})
        resumed_state = graph.invoke(resume_command, config=config)

        # 5. Verify graph resumed and completed
        post_snapshot = graph.get_state(config)
        self.assertEqual(len(post_snapshot.next), 0, "Graph should complete after approval")
        self.assertTrue(resumed_state.get("is_completed"))

    def test_interrupt_and_resume_rejection(self):
        checkpointer = MemorySaver()
        graph = build_multi_agent_graph(checkpointer=checkpointer)

        thread_id = "test-thread-rejection-1"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state: AgentState = {
            "task_id": thread_id,
            "goal": "Access sensitive environment configuration",
            "current_step": 0,
            "max_steps": 10,
            "max_rework_attempts": 2,
            "token_usage": 0,
            "estimated_cost_usd": 0.0,
            "messages": [],
            "subtasks": [
                {
                    "order_index": 0,
                    "title": "Read secret configuration",
                    "description": "Read .env secret keys",
                    "assigned_agent": "researcher",
                }
            ],
            "current_subtask_index": 0,
            "is_completed": False,
        }

        # 1. Invoke graph - pauses on sensitive .env access
        graph.invoke(initial_state, config=config)
        snapshot = graph.get_state(config)
        self.assertTrue(len(snapshot.next) > 0)

        # 2. Operator REJECTS the dangerous action
        resume_command = Command(
            resume={"approved": False, "feedback": "Security policy prohibits reading .env files"}
        )
        resumed_state = graph.invoke(resume_command, config=config)

        # 3. Verify security rejection was recorded and dangerous tool was aborted
        messages = resumed_state.get("messages", [])
        has_rejection = any("Security Rejection" in str(m.get("error", "")) for m in messages)
        self.assertTrue(has_rejection)


if __name__ == "__main__":
    unittest.main()
