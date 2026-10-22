import enum
from typing import List, Set
from pydantic import BaseModel, Field


class RiskLevel(str, enum.Enum):
    """
    Standard risk levels for agent actions and tool calls.
    """
    LOW = "LOW"        # Read-only tools, sandboxed execution with no network -> Auto-allowed
    MEDIUM = "MEDIUM"  # Writing files inside workspace -> Auto-allowed with audit log
    HIGH = "HIGH"      # Deletion, shell execution, external network, spending -> Human approval required


class RiskAssessment(BaseModel):
    """
    Structured outcome of evaluating an action against the safety policy.
    """
    tool_name: str
    risk_level: RiskLevel
    requires_human_approval: bool
    reason: str


# Disallowed command substrings and patterns (denylist)
DENIED_COMMAND_PATTERNS: Set[str] = {
    "rm -rf",
    "mkfs",
    ":(){ :|:& };:",  # Fork bomb
    "dd if=",
    "chmod -r 777",
    "sudo",
    "shutdown",
    "reboot",
    "wget",
    "curl",
}

# Sensitive file targets that should never be accessed or overwritten
PROTECTED_FILE_NAMES: Set[str] = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "passwd",
    "shadow",
    ".git",
}
