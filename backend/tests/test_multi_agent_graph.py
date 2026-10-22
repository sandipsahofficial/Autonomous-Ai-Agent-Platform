import unittest
from app.agents.graph import build_multi_agent_graph
from app.agents.state import AgentState


class TestMultiAgentGraph(unittest.TestCase):
    def test_multi_agent_full_pipeline(self):
        graph = build_multi_agent_graph()

        thread_id = "multi-task-1"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state: AgentState = {
            "task_id": thread_id,
            "goal": "Build an iterative Fibonacci solver in Python with unit tests",
            "current_step": 0,
            "max_steps": 15,
            "max_rework_attempts": 3,
            "token_usage": 0,
            "estimated_cost_usd": 0.0,
            "messages": [],
            "subtasks": [],
            "current_subtask_index": 0,
            "is_completed": False,
        }

        final_state = graph.invoke(initial_state, config=config)

        # 1. State must be marked completed
        self.assertTrue(final_state.get("is_completed"))
        self.assertIsNotNone(final_state.get("final_output"))

        # 2. Both subtasks must have been planned and processed
        subtasks = final_state.get("subtasks", [])
        self.assertGreaterEqual(len(subtasks), 2)
        self.assertEqual(final_state.get("current_subtask_index"), len(subtasks))

        # 3. Tokens and cost must have accumulated across agents
        self.assertGreater(final_state.get("token_usage", 0), 200)
        self.assertGreater(final_state.get("estimated_cost_usd", 0.0), 0.0)

        # 4. Message timeline must show Planner, Researcher, Coder, and Reviewer participation
        roles = [m.get("role") for m in final_state.get("messages", [])]
        self.assertIn("planner", roles)
        self.assertIn("researcher", roles)
        self.assertIn("coder", roles)
        self.assertIn("reviewer", roles)

    def test_rework_limit_caps_infinite_loops(self):
        graph = build_multi_agent_graph()

        thread_id = "multi-task-rework"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state: AgentState = {
            "task_id": thread_id,
            "goal": "Test rework bounds",
            "current_step": 0,
            "max_steps": 10,
            "max_rework_attempts": 1,
            "token_usage": 0,
            "estimated_cost_usd": 0.0,
            "messages": [],
            "subtasks": [],
            "current_subtask_index": 0,
            "is_completed": False,
        }

        final_state = graph.invoke(initial_state, config=config)
        self.assertTrue(final_state.get("is_completed"))
        self.assertEqual(final_state.get("rework_count"), 0)


if __name__ == "__main__":
    unittest.main()
