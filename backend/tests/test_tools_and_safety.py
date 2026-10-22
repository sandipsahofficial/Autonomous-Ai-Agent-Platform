import os
import unittest
from app.tools.registry import default_tool_registry
from app.tools.web_search import WebSearchTool
from app.tools.file_ops import FileReadTool, FileWriteTool, WORKSPACE_ROOT
from app.safety.policy import RiskLevel
from app.safety.risk_scorer import assess_tool_risk


class TestToolsAndSafety(unittest.TestCase):
    def setUp(self):
        # Clean workspace test directory
        self.test_filename = "test_note.txt"
        self.test_path = os.path.join(WORKSPACE_ROOT, self.test_filename)
        if os.path.exists(self.test_path):
            os.remove(self.test_path)

    def tearDown(self):
        if os.path.exists(self.test_path):
            os.remove(self.test_path)

    def test_web_search_tool(self):
        search_tool = WebSearchTool()
        result = search_tool.run(query="Python programming language", max_results=2)
        self.assertTrue(result.success)
        self.assertIsInstance(result.output, list)
        self.assertGreater(len(result.output), 0)
        first_item = result.output[0]
        self.assertIn("title", first_item)
        self.assertIn("snippet", first_item)

    def test_file_write_and_read(self):
        write_tool = FileWriteTool()
        read_tool = FileReadTool()

        test_content = "Hello, Autonomous AI Agent Platform!"
        write_result = write_tool.run(file_path=self.test_filename, content=test_content)
        self.assertTrue(write_result.success)

        read_result = read_tool.run(file_path=self.test_filename)
        self.assertTrue(read_result.success)
        self.assertEqual(read_result.output, test_content)

    def test_path_traversal_blocked(self):
        read_tool = FileReadTool()
        # Attempt to read outside workspace
        result = read_tool.run(file_path="../../.env")
        self.assertFalse(result.success)
        self.assertIn("Security Violation", result.error)

    def test_risk_scoring_levels(self):
        # 1. LOW: read-only
        r1 = assess_tool_risk("web_search", {"query": "python"})
        self.assertEqual(r1.risk_level, RiskLevel.LOW)
        self.assertFalse(r1.requires_human_approval)

        r2 = assess_tool_risk("file_read", {"file_path": "notes.txt"})
        self.assertEqual(r2.risk_level, RiskLevel.LOW)
        self.assertFalse(r2.requires_human_approval)

        # 2. MEDIUM: writing files in workspace
        r3 = assess_tool_risk("file_write", {"file_path": "script.py", "content": "print(1)"})
        self.assertEqual(r3.risk_level, RiskLevel.MEDIUM)
        self.assertFalse(r3.requires_human_approval)

        # 3. HIGH: deletion, shell, protected files, denied commands
        r4 = assess_tool_risk("file_delete", {"file_path": "script.py"})
        self.assertEqual(r4.risk_level, RiskLevel.HIGH)
        self.assertTrue(r4.requires_human_approval)

        r5 = assess_tool_risk("file_read", {"file_path": "my_secrets/.env"})
        self.assertEqual(r5.risk_level, RiskLevel.HIGH)
        self.assertTrue(r5.requires_human_approval)

        r6 = assess_tool_risk("shell_command", {"command": "rm -rf /data"})
        self.assertEqual(r6.risk_level, RiskLevel.HIGH)
        self.assertTrue(r6.requires_human_approval)

    def test_safety_gate_enforcement(self):
        # Gated execution: unapproved high-risk action must be blocked
        res, risk = default_tool_registry.execute_with_safety_gate(
            tool_name="file_delete",
            arguments={"file_path": "critical_data.txt"},
            human_approved=False,
        )
        self.assertFalse(res.success)
        self.assertIn("Approval Required", res.error)
        self.assertTrue(risk.requires_human_approval)

        # Gated execution: auto-allowed low-risk action executes immediately
        res2, risk2 = default_tool_registry.execute_with_safety_gate(
            tool_name="web_search",
            arguments={"query": "python tutorial", "max_results": 1},
            human_approved=False,
        )
        self.assertTrue(res2.success)
        self.assertEqual(risk2.risk_level, RiskLevel.LOW)


if __name__ == "__main__":
    unittest.main()
