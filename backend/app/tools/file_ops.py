import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult

# Safe workspace sandbox root directory
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.getcwd(), "workspace"))
os.makedirs(WORKSPACE_ROOT, exist_ok=True)


def _resolve_safe_path(requested_path: str) -> Optional[str]:
    """
    Resolve requested path and verify it stays inside the WORKSPACE_ROOT.
    Prevents path traversal attacks (e.g., ../../.env).
    """
    # If path is relative, resolve from WORKSPACE_ROOT
    if not os.path.isabs(requested_path):
        target = os.path.abspath(os.path.join(WORKSPACE_ROOT, requested_path))
    else:
        target = os.path.abspath(requested_path)

    # Verify target path is strictly within WORKSPACE_ROOT
    try:
        common = os.path.commonpath([WORKSPACE_ROOT, target])
        if common == WORKSPACE_ROOT:
            return target
    except ValueError:
        return None

    return None


class FileReadInput(BaseModel):
    file_path: str = Field(..., description="Path to file within the workspace to read")


class FileReadTool(BaseTool):
    """
    Safely reads content from a file inside the designated workspace.
    """
    name = "file_read"
    description = "Reads text contents from a file located within the workspace."
    args_schema = FileReadInput

    def run(self, file_path: str) -> ToolResult:
        safe_path = _resolve_safe_path(file_path)
        if not safe_path:
            return ToolResult(
                success=False,
                output=None,
                error=f"Security Violation: Access denied to path outside workspace: '{file_path}'",
            )

        if not os.path.exists(safe_path):
            return ToolResult(
                success=False,
                output=None,
                error=f"File not found: '{file_path}'",
            )

        if not os.path.isfile(safe_path):
            return ToolResult(
                success=False,
                output=None,
                error=f"Path is not a regular file: '{file_path}'",
            )

        try:
            with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return ToolResult(
                success=True,
                output=content,
                metadata={"file_path": file_path, "bytes": len(content.encode("utf-8"))},
            )
        except Exception as exc:
            return ToolResult(success=False, output=None, error=f"Read error: {str(exc)}")


class FileWriteInput(BaseModel):
    file_path: str = Field(..., description="Path to file within the workspace to write")
    content: str = Field(..., description="Text content to write to the file")


class FileWriteTool(BaseTool):
    """
    Safely writes content to a file inside the designated workspace.
    """
    name = "file_write"
    description = "Writes text content to a file located within the workspace."
    args_schema = FileWriteInput

    def run(self, file_path: str, content: str) -> ToolResult:
        safe_path = _resolve_safe_path(file_path)
        if not safe_path:
            return ToolResult(
                success=False,
                output=None,
                error=f"Security Violation: Cannot write to path outside workspace: '{file_path}'",
            )

        try:
            # Ensure parent directories exist
            os.makedirs(os.path.dirname(safe_path), exist_ok=True)
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(
                success=True,
                output=f"Successfully wrote {len(content.encode('utf-8'))} bytes to '{file_path}'",
                metadata={"file_path": file_path, "bytes_written": len(content.encode("utf-8"))},
            )
        except Exception as exc:
            return ToolResult(success=False, output=None, error=f"Write error: {str(exc)}")
