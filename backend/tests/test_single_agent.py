import unittest
from app.llm.mock_llm import MockLLMProvider
from app.agents.single_agent import build_single_agent_graph
from app.agents.state import AgentState


class TestSingleAgent(unittest.TestCase):
    def test_mock_llm_tracking(self):
        llm = MockLLMProvider()
        response = llm.generate("Explain Python generators and yield statement")
        self.assertGreater(response.usage.total_tokens, 0)
        self.assertGreaterEqual(response.usage.cost_usd, 0.0)
        self.assertIsNotNone(response.content)

    def test_single_agent_basic_run(self):
        graph = build_single_agent_graph()
        initial_state: AgentState = {
            "task_id": "test-task-1",
            "goal": "Write a concise explanation of asynchronous programming",
            "current_step": 0,
            "max_steps": 5,
            "token_usage": 0,
            "estimated_cost_usd": 0.0,
            "messages": [],
            "is_completed": False,
        }

        final_state = graph.invoke(initial_state)
        self.assertTrue(final_state.get("is_completed"))
        self.assertIsNotNone(final_state.get("final_output"))
        self.assertGreater(final_state.get("token_usage", 0), 0)
        self.assertEqual(final_state.get("current_step"), 1)

    def test_single_agent_tool_loop(self):
        # Goal containing "search" exercises the agent -> tool -> agent loop
        graph = build_single_agent_graph()
        initial_state: AgentState = {
            "task_id": "test-task-2",
            "goal": "Search the web for Python 3.11 release notes",
            "current_step": 0,
            "max_steps": 5,
            "token_usage": 0,
            "estimated_cost_usd": 0.0,
            "messages": [],
            "is_completed": False,
        }

        final_state = graph.invoke(initial_state)
        self.assertTrue(final_state.get("is_completed"))
        # Should have taken 2 reasoning steps (agent -> tool -> agent)
        self.assertEqual(final_state.get("current_step"), 2)
        # Check that tool output was captured in history
        messages = final_state.get("messages", [])
        has_tool_output = any("tool_output" in m for m in messages)
        self.assertTrue(has_tool_output)

    def test_step_limit_enforcement(self):
        graph = build_single_agent_graph()
        # Set max_steps to 0 so the very first step exceeds the limit
        initial_state: AgentState = {
            "task_id": "test-task-limit",
            "goal": "Infinite task test",
            "current_step": 0,
            "max_steps": 0,
            "token_usage": 0,
            "estimated_cost_usd": 0.0,
            "messages": [],
            "is_completed": False,
        }

        final_state = graph.invoke(initial_state)
        self.assertTrue(final_state.get("is_completed"))
        self.assertIn("Safety Limit Exceeded", final_state.get("error_message", ""))


if __name__ == "__main__":
    unittest.main()
