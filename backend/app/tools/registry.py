from typing import Dict, List, Any, Optional, Tuple
from app.tools.base import BaseTool, ToolResult
from app.tools.web_search import WebSearchTool
from app.tools.file_ops import FileReadTool, FileWriteTool
from app.tools.code_sandbox import CodeSandboxTool
from app.safety.risk_scorer import assess_tool_risk
from app.safety.policy import RiskAssessment, RiskLevel
from app.safety.audit_logger import record_audit_log


class ToolRegistry:
    """
    Central registry and execution gate for all tools.
    Integrates risk scoring and audit logging before every tool execution.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a new tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def list_schemas(self) -> List[Dict[str, Any]]:
        """List OpenAPI-style schemas for all registered tools."""
        return [tool.get_schema() for tool in self._tools.values()]

    def execute_with_safety_gate(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        human_approved: bool = False,
    ) -> Tuple[ToolResult, RiskAssessment]:
        """
        The mandatory execution gate.
        Every tool call must pass through this method.
        1. Evaluates risk via safety policy.
        2. Logs audit trail.
        3. Blocks execution and requests approval if HIGH risk and not yet approved.
        4. Executes tool only if safety checks pass.
        """
        # Step 1: Run risk assessment
        risk = assess_tool_risk(tool_name, arguments)

        # Step 2: Record audit log for attempt
        record_audit_log(
            agent_name="tool_gate",
            action_type="tool_execution_attempt",
            risk_level=risk.risk_level.value,
            payload={
                "tool_name": tool_name,
                "arguments": arguments,
                "human_approved": human_approved,
                "reason": risk.reason,
            },
        )

        # Step 3: Gate on high-risk actions
        if risk.requires_human_approval and not human_approved:
            return (
                ToolResult(
                    success=False,
                    output=None,
                    error=f"Approval Required: {risk.reason}",
                    metadata={
                        "risk_level": risk.risk_level.value,
                        "requires_human_approval": True,
                        "reason": risk.reason,
                    },
                ),
                risk,
            )

        # Step 4: Find tool
        tool = self.get(tool_name)
        if not tool:
            return (
                ToolResult(
                    success=False,
                    output=None,
                    error=f"Tool '{tool_name}' not found in registry.",
                ),
                risk,
            )

        # Step 5: Validate inputs with Pydantic schema
        try:
            validated_args = tool.args_schema(**arguments)
        except Exception as exc:
            return (
                ToolResult(
                    success=False,
                    output=None,
                    error=f"Invalid arguments for tool '{tool_name}': {str(exc)}",
                ),
                risk,
            )

        # Step 6: Execute tool
        try:
            result = tool.run(**validated_args.model_dump())

            # Log audit for successful or failed execution
            record_audit_log(
                agent_name="tool_gate",
                action_type="tool_execution_completed",
                risk_level=risk.risk_level.value,
                payload={
                    "tool_name": tool_name,
                    "success": result.success,
                    "metadata": result.metadata,
                },
            )
            return result, risk
        except Exception as exc:
            return (
                ToolResult(
                    success=False,
                    output=None,
                    error=f"Tool execution exception: {str(exc)}",
                ),
                risk,
            )


# Default pre-configured registry instance
default_tool_registry = ToolRegistry()
default_tool_registry.register(WebSearchTool())
default_tool_registry.register(FileReadTool())
default_tool_registry.register(FileWriteTool())
default_tool_registry.register(CodeSandboxTool())
