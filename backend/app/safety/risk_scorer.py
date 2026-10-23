from typing import Any, Dict
from app.safety.policy import (
    RiskLevel,
    RiskAssessment,
    DENIED_COMMAND_PATTERNS,
    PROTECTED_FILE_NAMES,
)


def assess_tool_risk(tool_name: str, arguments: Dict[str, Any]) -> RiskAssessment:
    """
    Evaluates a proposed tool call and assigns an immutable risk rating.
    Gating criteria:
      - LOW: Read-only operations, isolated sandbox code execution.
      - MEDIUM: Creating/modifying files inside workspace.
      - HIGH: File deletion, shell commands, unknown tools, sensitive files.
    """
    args_str = str(arguments).lower()

    # 1. Immediate High Risk: Check for sensitive file targets
    for protected in PROTECTED_FILE_NAMES:
        if protected in args_str:
            return RiskAssessment(
                tool_name=tool_name,
                risk_level=RiskLevel.HIGH,
                requires_human_approval=True,
                reason=f"Action references sensitive target: '{protected}'",
            )

    # 2. Immediate High Risk: Check for dangerous command patterns
    for denied_pattern in DENIED_COMMAND_PATTERNS:
        if denied_pattern in args_str:
            return RiskAssessment(
                tool_name=tool_name,
                risk_level=RiskLevel.HIGH,
                requires_human_approval=True,
                reason=f"Command contains prohibited pattern: '{denied_pattern}'",
            )

    # 3. Tool-specific classification
    if tool_name == "web_search":
        return RiskAssessment(
            tool_name=tool_name,
            risk_level=RiskLevel.LOW,
            requires_human_approval=False,
            reason="Web search is read-only information gathering.",
        )

    elif tool_name == "file_read":
        return RiskAssessment(
            tool_name=tool_name,
            risk_level=RiskLevel.LOW,
            requires_human_approval=False,
            reason="File read within workspace is read-only.",
        )

    elif tool_name == "execute_code_sandbox":
        # Sandboxed code execution with no network is LOW risk
        return RiskAssessment(
            tool_name=tool_name,
            risk_level=RiskLevel.LOW,
            requires_human_approval=False,
            reason="Execution runs in an isolated container with no network access.",
        )

    elif tool_name == "file_write":
        return RiskAssessment(
            tool_name=tool_name,
            risk_level=RiskLevel.MEDIUM,
            requires_human_approval=False,
            reason="File write modifies the workspace environment; auto-allowed with audit log.",
        )

    elif tool_name in ("calculator", "text_summarizer", "json_validator", "doc_inspector"):
        return RiskAssessment(
            tool_name=tool_name,
            risk_level=RiskLevel.LOW,
            requires_human_approval=False,
            reason=f"Tool '{tool_name}' performs safe, read-only or in-memory operations.",
        )

    elif tool_name == "http_get":
        return RiskAssessment(
            tool_name=tool_name,
            risk_level=RiskLevel.HIGH,
            requires_human_approval=True,
            reason="External HTTP requests require human approval and SSRF verification.",
        )

    elif tool_name in ("file_delete", "shell_command", "send_payment"):
        return RiskAssessment(
            tool_name=tool_name,
            risk_level=RiskLevel.HIGH,
            requires_human_approval=True,
            reason=f"Tool '{tool_name}' performs destructive or privileged system actions.",
        )

    # 4. Unknown tools default to HIGH risk (Fail-Safe Default)
    return RiskAssessment(
        tool_name=tool_name,
        risk_level=RiskLevel.HIGH,
        requires_human_approval=True,
        reason=f"Unrecognized tool '{tool_name}'; defaults to high risk for safety.",
    )
