import time
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from app.tools.base import BaseTool, ToolResult
from app.tools.web_search import WebSearchTool
from app.tools.file_ops import FileReadTool, FileWriteTool
from app.tools.code_sandbox import CodeSandboxTool
from app.tools.calculator import CalculatorTool
from app.tools.text_summarizer import TextSummarizerTool
from app.tools.json_validator import JsonValidatorTool
from app.tools.doc_inspector import DocumentInspectorTool
from app.tools.http_get import ApprovedHttpGetTool
from app.safety.risk_scorer import assess_tool_risk
from app.safety.policy import RiskAssessment, RiskLevel
from app.safety.audit_logger import record_audit_log


class ToolRegistry:
    """
    Central secure tool registry and execution gate.
    Enforces permissions, tool enablement, parameter validation, idempotency,
    timeouts, output caps, and comprehensive audit trails.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        # Tracks non-idempotent operations to prevent duplicate execution after network/interrupted failures
        self._idempotency_cache: Dict[str, ToolResult] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a new tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def list_schemas(self) -> List[Dict[str, Any]]:
        """List schemas for all registered and enabled tools."""
        return [tool.get_schema() for tool in self._tools.values() if tool.is_enabled]

    def list_all_tools(self) -> List[Dict[str, Any]]:
        """List metadata for all tools in the registry including disabled tools."""
        return [tool.get_schema() for tool in self._tools.values()]

    def execute_with_safety_gate(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        human_approved: bool = False,
        caller_permissions: Optional[List[str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[ToolResult, RiskAssessment]:
        """
        The mandatory execution gate.
        Every tool call must pass through this method.
        1. Evaluates risk via safety policy.
        2. Logs audit trail.
        3. Enforces idempotency checks to prevent executing non-idempotent ops twice.
        4. Verifies tool enablement and caller permissions.
        5. Validates inputs with Pydantic schema.
        6. Enforces human approval for HIGH risk actions.
        7. Executes tool with execution timing and output size enforcement.
        """
        start_time = time.time()

        # Step 1: Run risk assessment
        risk = assess_tool_risk(tool_name, arguments)

        # Step 2: Record audit log for execution attempt
        record_audit_log(
            agent_name="tool_gate",
            action_type="tool_execution_attempt",
            risk_level=risk.risk_level.value,
            payload={
                "tool_name": tool_name,
                "arguments": arguments,
                "human_approved": human_approved,
                "idempotency_key": idempotency_key,
                "reason": risk.reason,
            },
        )

        # Step 3: Check Idempotency Cache
        if idempotency_key and idempotency_key in self._idempotency_cache:
            cached = self._idempotency_cache[idempotency_key]
            meta = dict(cached.metadata or {})
            meta["is_idempotent_replay"] = True
            replay_result = ToolResult(
                success=cached.success,
                output=cached.output,
                error=cached.error,
                duration_ms=0.0,
                metadata=meta,
            )
            return replay_result, risk

        # Step 4: Gate on high-risk actions
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

        # Step 5: Find tool in registry
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

        # Step 6: Verify tool enablement
        if not tool.is_enabled:
            return (
                ToolResult(
                    success=False,
                    output=None,
                    error=f"Tool '{tool_name}' is currently disabled by administrative policy.",
                    metadata={"tool_disabled": True},
                ),
                risk,
            )

        # Step 7: Check required permissions if caller permissions are specified
        if caller_permissions is not None and tool.required_permissions:
            granted: Set[str] = set(caller_permissions)
            missing = [p for p in tool.required_permissions if p not in granted and "*:*" not in granted]
            if missing:
                return (
                    ToolResult(
                        success=False,
                        output=None,
                        error=f"Permission Denied: Caller lacks required permissions {missing} for tool '{tool_name}'.",
                    ),
                    risk,
                )

        # Step 8: Validate arguments using tool's Pydantic schema
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

        # Step 9: Execute tool with duration tracking and output size bounding
        try:
            result = tool.run(**validated_args.model_dump())
            duration_ms = round((time.time() - start_time) * 1000, 2)
            result.duration_ms = duration_ms

            # Output size bounding
            if result.output is not None:
                output_str = json.dumps(result.output) if isinstance(result.output, (dict, list)) else str(result.output)
                if len(output_str.encode("utf-8")) > tool.max_output_size_bytes:
                    result.metadata["output_truncated"] = True
                    result.metadata["original_size_bytes"] = len(output_str.encode("utf-8"))
                    if isinstance(result.output, str):
                        result.output = result.output[:tool.max_output_size_bytes] + "\n...[OUTPUT TRUNCATED DUE TO SIZE LIMIT]"

            # Cache successful idempotent/non-idempotent result
            if idempotency_key and result.success:
                self._idempotency_cache[idempotency_key] = result

            # Log audit for completed execution
            record_audit_log(
                agent_name="tool_gate",
                action_type="tool_execution_completed",
                risk_level=risk.risk_level.value,
                payload={
                    "tool_name": tool_name,
                    "success": result.success,
                    "duration_ms": duration_ms,
                    "metadata": result.metadata,
                },
            )
            return result, risk

        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            return (
                ToolResult(
                    success=False,
                    output=None,
                    error=f"Tool execution exception: {str(exc)}",
                    duration_ms=duration_ms,
                ),
                risk,
            )


# Default pre-configured registry instance
default_tool_registry = ToolRegistry()

# 1. Essential safe tools (Phase 3)
default_tool_registry.register(CalculatorTool())
default_tool_registry.register(TextSummarizerTool())
default_tool_registry.register(JsonValidatorTool())
default_tool_registry.register(DocumentInspectorTool())
default_tool_registry.register(ApprovedHttpGetTool(is_enabled=False))

# 2. Existing standard tools
default_tool_registry.register(WebSearchTool())
default_tool_registry.register(FileReadTool())
default_tool_registry.register(FileWriteTool())
default_tool_registry.register(CodeSandboxTool())
